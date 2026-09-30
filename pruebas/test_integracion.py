"""
pruebas/test_integracion.py
El despachador avisa a los oyentes, las alertas reaccionan a los eventos
y el nucleo completo no se frena mientras suena una alerta.
(LABORATORIO: archivo nuevo)
"""

import time
import unittest
from unittest import mock

import config
import alertas
import eventos
import nucleo
import almacenamiento as registro
from alertas import sintetizador
from eventos import despachador


class TestOyentes(unittest.TestCase):

    def setUp(self):
        self.recibidos = []
        eventos.suscribir(self.oyente)

    def tearDown(self):
        despachador._oyentes.remove(self.oyente)

    def oyente(self, nombre, registro):
        self.recibidos.append((nombre, registro["nivel"]))

    def test_el_despachador_avisa_a_los_oyentes(self):
        eventos.atender("cpu_alta", {"valor": config.CPU_ALTO,
                                     "umbral": config.CPU_ALTO})
        self.assertIn(("cpu_alta", "ALERTA"), self.recibidos)

    def test_suscribir_dos_veces_no_duplica(self):
        eventos.suscribir(self.oyente)
        eventos.atender("red_desconectada", {"segundos": config.PERIODO_CONEXION})
        self.assertEqual(self.recibidos, [("red_desconectada", "ALERTA")])

    def test_un_oyente_roto_no_rompe_el_despacho(self):
        def roto(nombre, registro):
            raise ValueError("oyente defectuoso")
        eventos.suscribir(roto)
        try:
            registro = eventos.atender("red_conectada",
                                       {"segundos": config.PERIODO_CONEXION})
        finally:
            despachador._oyentes.remove(roto)
        self.assertEqual(registro["nivel"], "INFO")
        self.assertIn(("red_conectada", "INFO"), self.recibidos)

    def test_los_eventos_de_red_tienen_manejador(self):
        for nombre in ("red_desconectada", "red_conectada",
                       "red_sigue_desconectada"):
            with self.subTest(evento=nombre):
                self.assertIn(nombre, eventos.eventos_conocidos())


class TestAlertasReaccionan(unittest.TestCase):

    def setUp(self):
        alertas.iniciar(silencio=True)
        eventos.suscribir(alertas.al_evento)

    def tearDown(self):
        alertas.detener()

    def test_un_evento_con_sonido_entra_en_la_cola(self):
        eventos.atender("ram_alta", {"valor": config.RAM_ALTA,
                                     "umbral": config.RAM_ALTA})
        self.assertEqual(alertas.actualizar(), "ram_alta")
        self.assertEqual(alertas.estado()["nombre"], "Memoria alta")

    def test_un_evento_sin_sonido_no(self):
        eventos.atender("proceso_nuevo", {"nombre": "prueba"})
        self.assertIsNone(alertas.actualizar())

    def test_la_prueba_toca_todas_en_orden(self):
        alertas.probar_todas()
        self.assertEqual(alertas.actualizar(), config.ORDEN_PRUEBA[0])
        self.assertTrue(alertas.ocupado())


class TestNucleoNoSeFrena(unittest.TestCase):

    def test_ninguna_vuelta_dura_lo_que_una_melodia(self):
        with mock.patch.object(config, "MODO_SILENCIOSO", True):
            nucleo.iniciar()
        alertas.probar_todas()
        mas_corta = min(sintetizador.duracion(n) for n in config.SONIDOS)
        duraciones = []
        inicio = time.monotonic()
        while time.monotonic() - inicio < mas_corta:
            antes = time.perf_counter()
            nucleo.ciclo()
            duraciones.append(time.perf_counter() - antes)
        alertas.detener()
        self.assertTrue(duraciones)
        # Hubo muchas vueltas mientras sonaba la primera alerta y ninguna
        # se acerco a la duracion de una melodia.
        self.assertGreater(len(duraciones), len(config.SONIDOS))
        self.assertLess(max(duraciones), mas_corta)


if __name__ == "__main__":
    unittest.main()


class TestBitacoraDelDashboard(unittest.TestCase):
    """Regresion: con la bitacora llena (deque con maxlen) la lista del
    dashboard dejaba de mostrar eventos nuevos."""

    def setUp(self):
        try:
            import tkinter as tk
            from dashboard import ventana
            self.raiz = tk.Tk()
        except Exception as error:          # sin tkinter o sin pantalla
            self.skipTest(f"tkinter no disponible: {error}")
        self.raiz.withdraw()
        self.tk, self.ventana = tk, ventana
        ventana._lista_eventos = tk.Listbox(self.raiz)
        ventana._ultimo_evento = None
        registro.limpiar_eventos()

    def tearDown(self):
        self.raiz.destroy()
        registro.limpiar_eventos()

    def test_sigue_mostrando_eventos_con_la_bitacora_llena(self):
        for i in range(config.MAX_EVENTOS_LOG + 1):
            registro.registrar_evento("INFO", "prueba", f"evento {i}")
        self.ventana._actualizar_eventos()
        registro.registrar_evento("INFO", "prueba", "llega con la bitacora llena")
        self.ventana._actualizar_eventos()
        lista = self.ventana._lista_eventos
        self.assertIn("llega con la bitacora llena", lista.get(self.tk.END))
        self.assertEqual(lista.size(), config.MAX_EVENTOS_LOG)
