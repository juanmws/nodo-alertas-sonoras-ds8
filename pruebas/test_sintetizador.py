"""
pruebas/test_sintetizador.py
Melodias, duraciones y archivos WAV de las alertas. (LABORATORIO: archivo nuevo)
"""

import os
import shutil
import tempfile
import unittest
import wave
from array import array
from unittest import mock

import config
from alertas import sintetizador


class TestMelodias(unittest.TestCase):

    def test_la_secuencia_repite_la_melodia(self):
        for nombre, patron in config.SONIDOS.items():
            with self.subTest(alerta=nombre):
                secuencia = sintetizador.notas(nombre)
                frecuencias = [f for f, _d, _p in secuencia]
                melodia = [f for f, _d in patron["notas"]]
                self.assertEqual(frecuencias, melodia * patron["repeticiones"])

    def test_la_ultima_nota_no_lleva_silencio(self):
        for nombre in config.SONIDOS:
            with self.subTest(alerta=nombre):
                *_resto, (_f, _d, pausa) = sintetizador.notas(nombre)
                self.assertIsNone(pausa)

    def test_duracion_cuadra_con_la_tabla(self):
        for nombre, p in config.SONIDOS.items():
            with self.subTest(alerta=nombre):
                notas = len(p["notas"])
                reps = p["repeticiones"]
                esperado = (reps * sum(d for _f, d in p["notas"])
                            + reps * (notas - 1) * p["pausa_ms"]
                            + (reps - 1) * p["pausa_rep_ms"])
                self.assertEqual(sintetizador.duracion_ms(nombre), esperado)


class TestArchivos(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.parche = mock.patch.object(config, "CARPETA_SONIDOS", self.carpeta)
        self.parche.start()

    def tearDown(self):
        self.parche.stop()
        shutil.rmtree(self.carpeta)

    def test_el_wav_tiene_el_formato_de_config(self):
        ruta = sintetizador.generar("red_conectada")
        with wave.open(ruta, "rb") as w:
            self.assertEqual(w.getnchannels(), config.CANALES)
            self.assertEqual(w.getsampwidth(), config.BYTES_POR_MUESTRA)
            self.assertEqual(w.getframerate(), config.TASA_MUESTREO)
            segundos = w.getnframes() / w.getframerate()
        # Cada nota y cada silencio se redondea a muestras enteras: a lo
        # sumo se pierde una muestra por tramo.
        secuencia = sintetizador.notas("red_conectada")
        tramos = len(secuencia) + len([p for *_x, p in secuencia if p is not None])
        tolerancia = tramos / config.TASA_MUESTREO
        self.assertAlmostEqual(segundos, sintetizador.duracion("red_conectada"),
                               delta=tolerancia)

    def test_el_volumen_no_satura(self):
        ruta = sintetizador.generar("cpu_alta")          # timbre brillante
        with wave.open(ruta, "rb") as w:
            muestras = array(sintetizador.TIPO_MUESTRA, w.readframes(w.getnframes()))
        tope = config.VOLUMEN * config.MAXIMO_MUESTRA
        self.assertLessEqual(max(abs(m) for m in muestras), tope)
        self.assertGreater(max(muestras), 0)            # si hay sonido

    def test_empieza_y_termina_en_silencio(self):
        ruta = sintetizador.generar("ram_alta")
        with wave.open(ruta, "rb") as w:
            muestras = array(sintetizador.TIPO_MUESTRA, w.readframes(w.getnframes()))
        self.assertEqual(muestras[0], 0)          # sin "clic" al empezar
        self.assertEqual(muestras.pop(), 0)       # ni al terminar

    def test_no_regenera_si_ya_existe(self):
        sintetizador.archivo("cpu_alta")
        with mock.patch.object(sintetizador, "generar") as generar:
            sintetizador.archivo("cpu_alta")
        generar.assert_not_called()

    def test_cambiar_la_melodia_cambia_el_archivo(self):
        antes = sintetizador.ruta("cpu_alta")
        otra = dict(config.SONIDOS["cpu_alta"], repeticiones=1)
        with mock.patch.dict(config.SONIDOS, {"cpu_alta": otra}):
            self.assertNotEqual(sintetizador.ruta("cpu_alta"), antes)

    def test_preparar_genera_todas(self):
        rutas = sintetizador.preparar()
        self.assertEqual(set(rutas), set(config.SONIDOS))
        for ruta in rutas.values():
            self.assertTrue(os.path.exists(ruta))


if __name__ == "__main__":
    unittest.main()
