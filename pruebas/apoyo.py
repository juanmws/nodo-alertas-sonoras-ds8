"""
pruebas/apoyo.py
Objetos falsos compartidos por las pruebas. (LABORATORIO: archivo nuevo)
"""


class RelojFalso:
    """Reloj que solo avanza cuando la prueba lo pide."""

    def __init__(self, inicio):
        self.t = inicio

    def __call__(self):
        return self.t

    def avanzar(self, segundos):
        self.t += segundos


class SalidaFalsa:
    """Salida de audio que anota lo que le piden en lugar de sonar."""

    NOMBRE = "salida falsa"

    def __init__(self, falla=None):
        self.rutas = []
        self.detenciones = []
        self._falla = falla

    def reproducir(self, ruta):
        if self._falla is not None:
            raise self._falla
        self.rutas.append(ruta)

    def detener(self):
        self.detenciones.append(True)
