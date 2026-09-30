"""
Paquete alertas
---------------
LABORATORIO: paquete nuevo del Laboratorio N.°1.

Agrega una reaccion sonora a los eventos del nodo sin tocar los sensores
ni los detectores. Se engancha al despachador como un OYENTE: cada vez
que se atiende un evento, el despachador llama a al_evento() y, si ese
evento tiene sonido en config.SONIDOS, la alerta entra en la cola.

    sintetizador.py  convierte cada melodia de config.SONIDOS en un WAV
    salidas.py       lo hace sonar en segundo plano segun el sistema
    reproductor.py   cola (deque) y marcas de tiempo: decide cuando suena

Desde afuera solo se usan las funciones de este archivo.
"""

from collections import deque

import config
from . import salidas, sintetizador
from .reproductor import Reproductor

_reproductor = None
_prueba = deque()            # alertas pendientes de la demostracion


def iniciar(silencio=None):
    """Genera los WAV, elige la salida de audio y crea el reproductor."""
    global _reproductor
    sintetizador.preparar()
    _reproductor = Reproductor(salidas.crear(), silencio=silencio)
    return _reproductor


def al_evento(nombre, registro):
    """Oyente del despachador: se ejecuta con cada evento atendido."""
    if _reproductor is not None:
        _reproductor.encolar(nombre)


def actualizar():
    """Una vuelta del reproductor. Se llama en cada vuelta del ciclo."""
    if _reproductor is None:
        return None
    if _prueba and not _reproductor.ocupado():
        _reproductor.encolar(_prueba.popleft(), forzar=True)
    return _reproductor.actualizar()


def probar_todas():
    """Encola, una tras otra, todas las alertas distintas (demostracion)."""
    _prueba.clear()
    _prueba.extend(config.ORDEN_PRUEBA)


def alternar_silencio():
    return _reproductor.alternar_silencio() if _reproductor else None


def ocupado():
    return bool(_prueba) or (_reproductor is not None
                             and _reproductor.ocupado())


def detener():
    _prueba.clear()
    if _reproductor is not None:
        _reproductor.detener()


def estado():
    """Todo lo que el dashboard necesita para dibujar el panel de alertas."""
    if _reproductor is None:
        return None
    actual = _reproductor.actual
    return {
        "salida": _reproductor.nombre_salida(),
        "silencio": _reproductor.silencio,
        "actual": actual,
        "nombre": config.NOMBRES_ALERTA.get(actual, actual),
        "descripcion": (config.SONIDOS[actual]["descripcion"]
                        if actual else None),
        "restante": _reproductor.restante(),
        "cola": [config.NOMBRES_ALERTA.get(n, n) for n in
                 _reproductor.pendientes() + list(_prueba)],
        "historial": list(_reproductor.historial),
        "error": _reproductor.error,
    }
