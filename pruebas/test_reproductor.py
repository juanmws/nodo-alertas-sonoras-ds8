"""
pruebas/test_reproductor.py
Cola, marcas de tiempo y reglas del reproductor de alertas.
(LABORATORIO: archivo nuevo)
"""

import math
import shutil
import time
import unittest
from unittest import mock

import config
from alertas import sintetizador
from alertas.reproductor import Reproductor
from alertas.salidas import SalidaComando
from pruebas.apoyo import RelojFalso, SalidaFalsa

PAUSA = config.PAUSA_ENTRE_ALERTAS_MS / config.MS_POR_SEGUNDO


def nuevo(silencio=False, salida=None):
    """Reproductor con reloj falso; la 'ruta' de cada WAV es su nombre."""
    reloj = RelojFalso(time.monotonic())
    salida = salida or SalidaFalsa()
    r = Reproductor(salida, archivo=lambda nombre: nombre,
                    duracion=sintetizador.duracion, reloj=reloj,
                    silencio=silencio)
    return r, reloj, salida


class TestTurnos(unittest.TestCase):

    def test_sin_alertas_no_hace_nada(self):
        r, reloj, salida = nuevo()
        self.assertIsNone(r.actualizar())
        self.assertEqual(salida.rutas, [])

    def test_la_primera_alerta_suena_en_la_siguiente_vuelta(self):
        r, reloj, salida = nuevo()
        self.assertTrue(r.encolar("cpu_alta"))
        self.assertEqual(r.actualizar(), "cpu_alta")
        self.assertEqual(salida.rutas, ["cpu_alta"])
        self.assertEqual(r.actual, "cpu_alta")

    def test_no_empieza_otra_mientras_suena_la_actual(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        r.encolar("ram_alta")
        r.actualizar()
        fin = reloj.t + sintetizador.duracion("cpu_alta")
        reloj.t = math.nextafter(fin, reloj.t)     # un instante antes del fin
        self.assertIsNone(r.actualizar())
        self.assertEqual(salida.rutas, ["cpu_alta"])
        self.assertEqual(r.pendientes(), ["ram_alta"])

    def test_respeta_la_pausa_entre_alertas(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        r.encolar("ram_alta")
        r.actualizar()
        reloj.avanzar(sintetizador.duracion("cpu_alta"))
        self.assertIsNone(r.actualizar())          # termino, pero hay pausa
        self.assertIsNone(r.actual)
        reloj.avanzar(PAUSA)
        self.assertEqual(r.actualizar(), "ram_alta")
        self.assertEqual(salida.rutas, ["cpu_alta", "ram_alta"])

    def test_restante_baja_con_el_tiempo(self):
        r, reloj, salida = nuevo()
        r.encolar("ram_alta")
        r.actualizar()
        total = sintetizador.duracion("ram_alta")
        self.assertAlmostEqual(r.restante(), total)
        reloj.avanzar(config.PERIODO_CONEXION)
        self.assertAlmostEqual(r.restante(), total - config.PERIODO_CONEXION)


class TestNoBloquea(unittest.TestCase):

    def test_actualizar_devuelve_enseguida_aunque_la_alerta_siga_sonando(self):
        r, reloj, salida = nuevo()
        r.encolar("red_desconectada")
        r.encolar("cpu_alta")
        for _vuelta in config.SONIDOS:              # varias vueltas seguidas
            inicio = time.perf_counter()
            r.actualizar()
            ms = (time.perf_counter() - inicio) * config.MS_POR_SEGUNDO
            self.assertLess(ms, config.MAX_MS_ACTUALIZAR)
        self.assertEqual(salida.rutas, ["red_desconectada"])

    @unittest.skipUnless(shutil.which("sleep"), "requiere el comando sleep")
    def test_la_salida_no_espera_al_proceso_que_suena(self):
        # 'sleep' hace de reproductor que tarda lo mismo que la melodia.
        salida = SalidaComando("sleep", "prueba")
        duracion = sintetizador.duracion("red_desconectada")
        inicio = time.perf_counter()
        salida.reproducir(str(duracion))
        transcurrido = time.perf_counter() - inicio
        salida.detener()
        # Lanzar el sonido tarda menos que una vuelta del dashboard, y
        # muchisimo menos que la melodia.
        self.assertLess(transcurrido * config.MS_POR_SEGUNDO,
                        config.REFRESCO_MS)
        self.assertLess(transcurrido, duracion)


class TestReglasDeLaCola(unittest.TestCase):

    def test_evento_sin_sonido_se_ignora(self):
        r, reloj, salida = nuevo()
        self.assertFalse(r.encolar("proceso_nuevo"))
        self.assertEqual(r.pendientes(), [])

    def test_no_duplica_una_alerta_que_ya_espera(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        reloj.avanzar(config.ENFRIAMIENTO_S)
        self.assertFalse(r.encolar("cpu_alta"))
        self.assertEqual(r.pendientes(), ["cpu_alta"])

    def test_enfriamiento(self):
        r, reloj, salida = nuevo()
        inicio = reloj.t
        self.assertTrue(r.encolar("cpu_alta"))
        r.actualizar()
        limite = inicio + config.ENFRIAMIENTO_S
        reloj.t = math.nextafter(limite, inicio)   # un instante antes
        self.assertFalse(r.encolar("cpu_alta"))
        reloj.t = limite
        self.assertTrue(r.encolar("cpu_alta"))

    def test_forzar_ignora_el_enfriamiento(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        r.actualizar()
        self.assertTrue(r.encolar("cpu_alta", forzar=True))

    def test_urgente_pasa_al_frente(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        r.encolar("ram_alta")
        r.encolar("red_desconectada")
        self.assertEqual(r.pendientes(),
                         ["red_desconectada", "cpu_alta", "ram_alta"])

    def test_cola_llena_rechaza_lo_normal_y_acepta_lo_urgente(self):
        llenas = ["cpu_alta", "ram_alta", "red_pico"]
        with mock.patch.object(config, "MAX_COLA_ALERTAS", len(llenas)):
            r, reloj, salida = nuevo()
        for nombre in llenas:
            self.assertTrue(r.encolar(nombre))
        self.assertFalse(r.encolar("red_sigue_desconectada"))
        self.assertTrue(r.encolar("red_desconectada"))
        # la urgente entra al frente y sale la ultima de la cola
        self.assertEqual(r.pendientes(),
                         ["red_desconectada", "cpu_alta", "ram_alta"])

    def test_red_conectada_cancela_avisos_de_caida_pendientes(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        r.actualizar()
        r.encolar("red_desconectada")
        r.encolar("red_sigue_desconectada")
        r.encolar("red_conectada")
        self.assertEqual(r.pendientes(), ["red_conectada"])

    def test_interrumpe_la_alerta_cancelada_que_esta_sonando(self):
        r, reloj, salida = nuevo()
        r.encolar("red_desconectada")
        r.actualizar()
        r.encolar("red_conectada")
        self.assertEqual(salida.detenciones, [True])
        self.assertEqual(r.actualizar(), "red_conectada")

    def test_no_interrumpe_si_la_cancelada_ya_termino(self):
        r, reloj, salida = nuevo()
        r.encolar("cpu_alta")
        r.actualizar()
        reloj.avanzar(sintetizador.duracion("cpu_alta"))
        r.encolar("cpu_normal")
        self.assertEqual(salida.detenciones, [])


class TestModoSilencioso(unittest.TestCase):

    def test_no_suena_pero_la_cola_avanza(self):
        r, reloj, salida = nuevo(silencio=True)
        r.encolar("cpu_alta")
        self.assertEqual(r.actualizar(), "cpu_alta")
        self.assertEqual(salida.rutas, [])
        self.assertTrue(r.historial[0]["silencio"])

    def test_alternar_corta_el_sonido(self):
        r, reloj, salida = nuevo()
        r.encolar("ram_alta")
        r.actualizar()
        self.assertTrue(r.alternar_silencio())
        self.assertEqual(salida.detenciones, [True])
        self.assertFalse(r.alternar_silencio())

    def test_una_salida_rota_no_detiene_el_reproductor(self):
        r, reloj, salida = nuevo(salida=SalidaFalsa(falla=OSError("sin audio")))
        r.encolar("cpu_alta")
        self.assertEqual(r.actualizar(), "cpu_alta")
        self.assertEqual(r.error, "sin audio")


if __name__ == "__main__":
    unittest.main()
