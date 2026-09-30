"""
pruebas/test_reglas.py
Reglas del enunciado que se pueden comprobar leyendo el propio codigo.
(LABORATORIO: archivo nuevo)

  - Cada tipo de problema tiene un sonido distinto.
  - Sonidos, tiempos y umbrales solo en config.py: fuera de el no hay
    numeros literales en el codigo nuevo ni en las lineas marcadas.
  - Los sensores y los detectores originales no se modificaron.
"""

import ast
import glob
import io
import os
import tokenize
import unittest

import config
from eventos.manejadores import MANEJADORES

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARCA = "# LABORATORIO"

ARCHIVOS_NUEVOS = (["alertas/__init__.py", "alertas/sintetizador.py",
                    "alertas/salidas.py", "alertas/reproductor.py",
                    "sensores/conexion.py", "eventos/conexion.py"]
                   + sorted(os.path.relpath(p, RAIZ) for p in
                            glob.glob(os.path.join(RAIZ, "pruebas", "*.py"))))

ARCHIVOS_MODIFICADOS = ["main.py", "nucleo.py", "generador.py",
                        "eventos/__init__.py", "eventos/despachador.py",
                        "eventos/manejadores.py", "dashboard/consola.py",
                        "dashboard/ventana.py"]

ORIGINALES_INTACTOS = ["eventos/detectores.py", "sensores/__init__.py",
                       "sensores/cpu.py", "sensores/memoria.py",
                       "sensores/disco.py", "sensores/red.py",
                       "sensores/procesos.py", "sensores/bateria.py"]

# 0 y 1 no son parametros: son el inicio de un indice o de un conteo y
# ninguna regla de "numeros magicos" los considera como tales.
NEUTROS = {0, 1}

# Eventos que el enunciado pide que suenen distinto.
PROBLEMAS = ("cpu_alta", "ram_alta", "red_pico", "red_desconectada",
             "red_sigue_desconectada", "red_conectada")


def leer(relativa):
    with open(os.path.join(RAIZ, relativa), encoding="utf-8") as f:
        return f.read()


def numeros(texto, lineas=None):
    """(linea, numero) de cada literal numerico no neutro del texto."""
    hallados = []
    for tok in tokenize.generate_tokens(io.StringIO(texto).readline):
        if tok.type != tokenize.NUMBER:
            continue
        linea = tok.start[0]
        if lineas is not None and linea not in lineas:
            continue
        if ast.literal_eval(tok.string) not in NEUTROS:
            hallados.append((linea, tok.string))
    return hallados


def lineas_marcadas(texto):
    """Lineas con '# LABORATORIO' al final y las de cada bloque
    '# LABORATORIO: inicio' ... '# LABORATORIO: fin'."""
    marcadas = set()
    dentro = False
    for n, linea in enumerate(texto.splitlines(), start=1):
        limpia = linea.strip()
        if limpia.startswith(MARCA + ": inicio"):
            dentro = True
        if dentro or (MARCA in linea and not limpia.startswith("#")):
            marcadas.add(n)
        if limpia.startswith(MARCA + ": fin"):
            dentro = False
    return marcadas


class TestTablaDeSonidos(unittest.TestCase):

    def test_todos_los_problemas_tienen_sonido(self):
        for nombre in PROBLEMAS:
            with self.subTest(evento=nombre):
                self.assertIn(nombre, config.SONIDOS)

    def test_cada_problema_suena_distinto(self):
        melodias = {config.SONIDOS[n]["notas"] for n in PROBLEMAS}
        self.assertEqual(len(melodias), len(PROBLEMAS))

    def test_cada_sonido_corresponde_a_un_evento_real(self):
        for nombre in config.SONIDOS:
            with self.subTest(evento=nombre):
                self.assertIn(nombre, MANEJADORES)
                self.assertIn(nombre, config.NOMBRES_ALERTA)

    def test_cada_sonido_esta_completo(self):
        claves = {"notas", "pausa_ms", "repeticiones", "pausa_rep_ms",
                  "timbre", "urgente", "cancela", "descripcion"}
        for nombre, patron in config.SONIDOS.items():
            with self.subTest(evento=nombre):
                self.assertEqual(set(patron), claves)
                self.assertIn(patron["timbre"], config.TIMBRES)
                for otra in patron["cancela"]:
                    self.assertIn(otra, config.SONIDOS)

    def test_la_demostracion_usa_alertas_existentes(self):
        for nombre in config.ORDEN_PRUEBA:
            self.assertIn(nombre, config.SONIDOS)


class TestSinNumerosLiterales(unittest.TestCase):

    def test_archivos_nuevos(self):
        for ruta in ARCHIVOS_NUEVOS:
            with self.subTest(archivo=ruta):
                self.assertEqual(numeros(leer(ruta)), [])

    def test_lineas_marcadas_en_archivos_modificados(self):
        for ruta in ARCHIVOS_MODIFICADOS:
            with self.subTest(archivo=ruta):
                texto = leer(ruta)
                marcadas = lineas_marcadas(texto)
                self.assertTrue(marcadas, "el archivo no tiene marcas")
                self.assertEqual(numeros(texto, marcadas), [])


class TestOriginalesIntactos(unittest.TestCase):

    def test_sensores_y_detectores_sin_marcas(self):
        for ruta in ORIGINALES_INTACTOS:
            with self.subTest(archivo=ruta):
                self.assertNotIn("LABORATORIO", leer(ruta))


if __name__ == "__main__":
    unittest.main()
