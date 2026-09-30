"""
alertas/sintetizador.py
Convierte cada melodia de config.SONIDOS en un archivo WAV.

LABORATORIO: modulo nuevo.

Por que archivos y no winsound.Beep(): Beep() no devuelve el control hasta
que la nota termina, asi que una alerta de dos segundos congelaria el
dashboard dos segundos. Un archivo WAV, en cambio, se manda a sonar en
segundo plano (SND_ASYNC en Windows, afplay en macOS) y el programa sigue
en el acto.

Los archivos se generan una sola vez, al arrancar el nodo. El nombre de
cada uno lleva una huella de su melodia: si se cambia config.py, el
archivo se vuelve a generar solo.
"""

import hashlib
import math
import os
import sys
import wave
from array import array

import config

# Entero con signo de 16 bits. El formato WAV lo exige en little endian.
TIPO_MUESTRA = "h"


def _muestras(ms):
    """Cantidad de muestras que ocupan `ms` milisegundos."""
    return int(config.TASA_MUESTREO * ms / config.MS_POR_SEGUNDO)


def notas(nombre):
    """Secuencia completa de la alerta: lista de (frecuencia, ms, pausa_ms).

    La ultima nota lleva pausa None: el silencio entre dos alertas lo pone
    el reproductor, no el archivo.
    """
    patron = config.SONIDOS[nombre]
    secuencia = []
    for _vuelta in range(patron["repeticiones"]):
        vuelta = [(f, d, patron["pausa_ms"]) for f, d in patron["notas"]]
        frecuencia, duracion, _pausa = vuelta.pop()
        vuelta.append((frecuencia, duracion, patron["pausa_rep_ms"]))
        secuencia.extend(vuelta)
    frecuencia, duracion, _pausa = secuencia.pop()
    secuencia.append((frecuencia, duracion, None))
    return secuencia


def duracion_ms(nombre):
    """Lo que dura la alerta completa, en milisegundos."""
    secuencia = notas(nombre)
    sonido = sum(d for _f, d, _p in secuencia)
    silencio = sum(p for _f, _d, p in secuencia if p is not None)
    return sonido + silencio


def duracion(nombre):
    """Lo que dura la alerta completa, en segundos."""
    return duracion_ms(nombre) / config.MS_POR_SEGUNDO


def _tono(frecuencia, ms, armonicos):
    """Muestras de una nota: suma de senoidales con subida y bajada suave."""
    total = _muestras(ms)
    rampa = _muestras(config.RAMPA_MS)
    peso_total = sum(peso for _a, peso in armonicos)
    escala = config.VOLUMEN * config.MAXIMO_MUESTRA / peso_total
    paso = math.tau * frecuencia / config.TASA_MUESTREO
    muestras = array(TIPO_MUESTRA)
    for i in range(total):
        onda = sum(peso * math.sin(paso * armonico * i)
                   for armonico, peso in armonicos)
        # Envolvente: crece en la rampa inicial y decrece en la final,
        # de modo que la primera y la ultima muestra valen exactamente 0.
        envolvente = min(i, total - 1 - i, rampa) / rampa
        muestras.append(int(onda * envolvente * escala))
    return muestras


def _silencio(ms):
    return array(TIPO_MUESTRA, bytes(_muestras(ms) * config.BYTES_POR_MUESTRA))


def _huella(nombre):
    """Identifica la melodia y los parametros con que se sintetizo."""
    patron = config.SONIDOS[nombre]
    datos = repr((notas(nombre), config.TIMBRES[patron["timbre"]],
                  config.TASA_MUESTREO, config.VOLUMEN, config.RAMPA_MS))
    return hashlib.md5(datos.encode("utf-8")).hexdigest()


def ruta(nombre):
    return os.path.join(config.CARPETA_SONIDOS,
                        f"{nombre}_{_huella(nombre)}.wav")


def generar(nombre):
    """Escribe el WAV de una alerta y devuelve su ruta."""
    armonicos = config.TIMBRES[config.SONIDOS[nombre]["timbre"]]
    muestras = array(TIPO_MUESTRA)
    for frecuencia, ms, pausa in notas(nombre):
        muestras.extend(_tono(frecuencia, ms, armonicos))
        if pausa is not None:
            muestras.extend(_silencio(pausa))
    if sys.byteorder == "big":
        muestras.byteswap()

    destino = ruta(nombre)
    os.makedirs(config.CARPETA_SONIDOS, exist_ok=True)
    temporal = destino + ".tmp"
    with wave.open(temporal, "wb") as archivo:
        archivo.setnchannels(config.CANALES)
        archivo.setsampwidth(config.BYTES_POR_MUESTRA)
        archivo.setframerate(config.TASA_MUESTREO)
        archivo.writeframes(muestras.tobytes())
    # Se renombra al final para que nadie reproduzca un archivo a medias.
    os.replace(temporal, destino)
    return destino


def archivo(nombre):
    """Ruta del WAV de la alerta. Lo genera solo si aun no existe."""
    destino = ruta(nombre)
    if not os.path.exists(destino):
        generar(nombre)
    return destino


def preparar():
    """Genera por adelantado todos los WAV, antes de que arranque el ciclo."""
    return {nombre: archivo(nombre) for nombre in config.SONIDOS}
