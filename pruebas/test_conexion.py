"""
pruebas/test_conexion.py
Detector de conexion (flanco, antirrebote y recordatorio) y sensor de
conexion con interfaces de red inventadas. (LABORATORIO: archivo nuevo)
"""

import socket
import time
import unittest
from collections import namedtuple
from unittest import mock

import config
from eventos.conexion import DetectorConexion
from sensores import conexion

PASO = config.PERIODO_CONEXION
CONFIRMAR = config.CONFIRMAR_CAMBIO_RED


class Linea:
    """Alimenta al detector con lecturas separadas por PASO segundos."""

    def __init__(self):
        self.detector = DetectorConexion()
        self.t = time.time()
        self.datos = {}                  # ultimo dato de cada evento

    def leer(self, *lecturas):
        """Devuelve los nombres de los eventos que provocan las lecturas."""
        nombres = []
        for conectado in lecturas:
            self.t += PASO
            for nombre, dato in self.detector.revisar(conectado, self.t):
                nombres.append(nombre)
                self.datos[nombre] = dato
        return nombres

    def esperar(self, segundos, conectado):
        """Avanza el reloj sin lecturas y luego hace una."""
        self.t += segundos - PASO
        return self.leer(conectado)


class TestFlanco(unittest.TestCase):

    def test_arranque_con_red_no_avisa(self):
        self.assertEqual(Linea().leer(True), [])

    def test_arranque_sin_red_avisa(self):
        self.assertEqual(Linea().leer(False), ["red_desconectada"])

    def test_corte_confirmado_avisa_una_sola_vez(self):
        linea = Linea()
        linea.leer(True)
        eventos = linea.leer(*[False] * CONFIRMAR)
        self.assertEqual(eventos, ["red_desconectada"])
        self.assertEqual(linea.leer(False), [])
        self.assertFalse(linea.detector.conectado)

    def test_un_parpadeo_no_es_un_corte(self):
        linea = Linea()
        linea.leer(True)
        self.assertEqual(linea.leer(False, True, False, True), [])
        self.assertTrue(linea.detector.conectado)

    def test_recuperacion_informa_cuanto_duro_el_corte(self):
        linea = Linea()
        linea.leer(True)
        linea.leer(*[False] * CONFIRMAR)
        inicio_corte = linea.t - (CONFIRMAR - 1) * PASO   # primera lectura sin red
        inicio_vuelta = linea.t + PASO                    # primera lectura con red
        self.assertEqual(linea.leer(*[True] * CONFIRMAR), ["red_conectada"])
        esperado = round(inicio_vuelta - inicio_corte, config.DECIMALES_TIEMPO)
        self.assertEqual(linea.datos["red_conectada"]["segundos"], esperado)
        self.assertTrue(linea.detector.conectado)

    def test_sensor_sin_respuesta_no_cambia_nada(self):
        linea = Linea()
        linea.leer(True)
        self.assertEqual(linea.leer(*[None] * CONFIRMAR), [])
        self.assertTrue(linea.detector.conectado)


class TestRecordatorio(unittest.TestCase):

    def cortada(self):
        linea = Linea()
        linea.leer(True)
        linea.leer(*[False] * CONFIRMAR)
        return linea

    def test_no_recuerda_antes_de_tiempo(self):
        linea = self.cortada()
        self.assertEqual(
            linea.esperar(config.RECORDATORIO_RED_S - PASO, False), [])

    def test_recuerda_cada_periodo_mientras_siga_caida(self):
        linea = self.cortada()
        self.assertEqual(linea.esperar(config.RECORDATORIO_RED_S, False),
                         ["red_sigue_desconectada"])
        self.assertEqual(linea.leer(False), [])
        self.assertEqual(linea.esperar(config.RECORDATORIO_RED_S, False),
                         ["red_sigue_desconectada"])

    def test_el_recordatorio_cuenta_desde_el_inicio_del_corte(self):
        linea = self.cortada()
        (_nombre, dato), = linea.detector.revisar(
            False, linea.t + config.RECORDATORIO_RED_S)
        self.assertGreaterEqual(dato["segundos"], config.RECORDATORIO_RED_S)

    def test_con_red_nunca_hay_recordatorio(self):
        linea = Linea()
        linea.leer(True)
        self.assertEqual(linea.esperar(config.RECORDATORIO_RED_S, True), [])

    def test_despues_de_recuperar_no_hay_recordatorios(self):
        linea = self.cortada()
        linea.leer(*[True] * CONFIRMAR)
        self.assertEqual(linea.esperar(config.RECORDATORIO_RED_S, True), [])


# ---------------------------------------------------------------------------
# Sensor: interfaces inventadas con la misma forma que devuelve psutil.
# ---------------------------------------------------------------------------
Estado = namedtuple("Estado", "isup")
Direccion = namedtuple("Direccion", "family address")


def ipv4(ip):
    return [Direccion(socket.AF_INET, ip)]


class TestSensorConexion(unittest.TestCase):

    def activas(self, **interfaces):
        """interfaces: nombre=(activa, [direcciones])"""
        estados = {n: Estado(a) for n, (a, _d) in interfaces.items()}
        direcciones = {n: d for n, (_a, d) in interfaces.items()}
        return conexion.interfaces_activas(estados, direcciones)

    def test_solo_loopback_no_es_conexion(self):
        self.assertEqual(self.activas(lo0=(True, ipv4("127.0.0.1"))), [])

    def test_ip_automatica_sin_dhcp_no_es_conexion(self):
        self.assertEqual(self.activas(en0=(True, ipv4("169.254.10.20"))), [])

    def test_wifi_con_ip_es_conexion(self):
        self.assertEqual(self.activas(en0=(True, ipv4("192.168.1.20"))),
                         [("en0", "192.168.1.20")])

    def test_interfaz_apagada_no_cuenta(self):
        self.assertEqual(self.activas(en0=(False, ipv4("192.168.1.20"))), [])

    def test_vpn_y_maquinas_virtuales_no_cuentan(self):
        self.assertEqual(self.activas(
            utun4=(True, ipv4("10.8.0.2")),
            vboxnet0=(True, ipv4("192.168.56.1")),
            **{"vEthernet (WSL)": (True, ipv4("172.20.0.1"))}), [])

    def test_ethernet_de_windows_si_cuenta(self):
        nombre = "Local Area Connection"
        self.assertEqual(self.activas(**{nombre: (True, ipv4("10.0.0.5"))}),
                         [(nombre, "10.0.0.5")])

    def test_solo_ipv6_no_cuenta(self):
        v6 = [Direccion(socket.AF_INET6, "fe80::1")]
        self.assertEqual(self.activas(en0=(True, v6)), [])

    def test_leer_arma_el_diccionario(self):
        with mock.patch.object(conexion.psutil, "net_if_stats",
                               return_value={"en0": Estado(True)}), \
             mock.patch.object(conexion.psutil, "net_if_addrs",
                               return_value={"en0": ipv4("192.168.1.20")}):
            lectura = conexion.leer()
        self.assertTrue(lectura["conectado"])
        self.assertEqual(lectura["detalle"], "en0 192.168.1.20")

    def test_leer_sin_red(self):
        with mock.patch.object(conexion.psutil, "net_if_stats",
                               return_value={"en0": Estado(False)}), \
             mock.patch.object(conexion.psutil, "net_if_addrs",
                               return_value={}):
            self.assertFalse(conexion.leer()["conectado"])

    def test_leer_con_error_devuelve_none(self):
        with mock.patch.object(conexion.psutil, "net_if_stats",
                               side_effect=OSError):
            self.assertIsNone(conexion.leer())


if __name__ == "__main__":
    unittest.main()
