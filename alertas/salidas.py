"""
alertas/salidas.py
Donde suena el sonido. Hay una salida por sistema operativo y todas
cumplen la misma interfaz, igual que los sensores:

    NOMBRE             texto que se muestra en el dashboard
    reproducir(ruta)   empieza a sonar el WAV y DEVUELVE ENSEGUIDA
    detener()          corta lo que este sonando

LABORATORIO: modulo nuevo.

Ninguna salida espera a que el sonido termine. Cuanto dura cada alerta lo
sabe el reproductor por las marcas de tiempo, no la salida.
"""

import shutil
import subprocess
import sys


class SalidaWindows:
    """winsound.PlaySound con SND_ASYNC: suena en segundo plano."""

    NOMBRE = "winsound (Windows)"

    def __init__(self):
        import winsound
        self._winsound = winsound
        self._banderas = (winsound.SND_FILENAME | winsound.SND_ASYNC
                          | winsound.SND_NODEFAULT)

    def reproducir(self, ruta):
        self._winsound.PlaySound(ruta, self._banderas)

    def detener(self):
        # Con None, PlaySound corta el sonido que este en curso.
        self._winsound.PlaySound(None, self._winsound.SND_ASYNC)


class SalidaComando:
    """Lanza un reproductor del sistema (afplay, paplay, aplay) como un
    proceso aparte. Popen no espera a que el proceso termine."""

    def __init__(self, programa, nombre):
        self._programa = programa
        self.NOMBRE = nombre
        self._proceso = None

    def reproducir(self, ruta):
        self.detener()
        self._proceso = subprocess.Popen(
            [self._programa, ruta],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def detener(self):
        if self._proceso is not None and self._proceso.poll() is None:
            self._proceso.terminate()
            self._proceso.wait()     # el proceso muere en el acto con terminate


class SalidaCampana:
    """Ultimo recurso: el caracter BEL. No distingue melodias, pero avisa."""

    NOMBRE = "campana del sistema"

    def reproducir(self, ruta):
        sys.stdout.write("\a")
        sys.stdout.flush()

    def detener(self):
        pass


def crear():
    """Elige la mejor salida disponible en este equipo."""
    if sys.platform.startswith("win"):
        try:
            return SalidaWindows()
        except ImportError:
            return SalidaCampana()
    if sys.platform == "darwin" and shutil.which("afplay"):
        return SalidaComando("afplay", "afplay (macOS)")
    for programa in ("paplay", "aplay"):
        if shutil.which(programa):
            return SalidaComando(programa, f"{programa} (Linux)")
    return SalidaCampana()
