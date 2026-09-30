"""
sensores/bateria.py
Estado de la bateria.

Este es el unico sensor que puede NO existir: en una computadora de
escritorio psutil.sensors_battery() devuelve None. Ese caso no es un
error del programa, es un sensor ausente, y el sistema debe seguir
funcionando sin el.

El campo power_plugged es una senal digital: conectado o desconectado.
Su cambio es el evento de flanco mas facil de provocar en el laboratorio,
basta con jalar el cable del cargador.
"""

import psutil

ETIQUETA = "Bateria"
UNIDAD = "%"


def _estado():
    try:
        return psutil.sensors_battery()
    except Exception:
        return None


def disponible():
    """False en equipos de escritorio o sin soporte del sistema."""
    return _estado() is not None


def leer():
    b = _estado()
    if b is None:
        return None

    if b.power_plugged:
        detalle = "conectado a la corriente"
    elif b.secsleft in (psutil.POWER_TIME_UNLIMITED,
                        psutil.POWER_TIME_UNKNOWN):
        detalle = "en bateria | autonomia desconocida"
    else:
        horas, resto = divmod(int(b.secsleft), 3600)
        detalle = f"en bateria | quedan {horas}h {resto // 60:02d}m"

    return {
        "valor": round(b.percent, 1),
        "unidad": UNIDAD,
        "porcentaje": b.percent,
        "detalle": detalle,
        "extra": {"conectado": bool(b.power_plugged)},
    }
