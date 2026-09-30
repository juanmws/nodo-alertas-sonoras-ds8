"""
eventos/despachador.py
Conecta cada evento con su manejador.

Este archivo tiene una sola funcion y no va a crecer nunca, por mas
eventos que se agreguen: en lugar de una cadena de if/elif, busca la
funcion en un diccionario. Ese es exactamente el mecanismo con el que
trabajan por dentro las bibliotecas de eventos y los clientes MQTT.
"""

import almacenamiento as registro
from .manejadores import MANEJADORES

# LABORATORIO: inicio
# Oyentes: funciones que quieren enterarse de TODOS los eventos, ademas
# de su manejador. Asi se agrega una reaccion nueva (las alertas sonoras)
# sin tocar los detectores ni los manejadores existentes.
_oyentes = []


def suscribir(funcion):
    """Registra una funcion oyente(nombre, registro)."""
    if funcion not in _oyentes:
        _oyentes.append(funcion)


def _avisar(nombre, registro_evento):
    for oyente in list(_oyentes):
        try:
            oyente(nombre, registro_evento)
        except Exception as error:
            # Un oyente defectuoso tampoco debe tumbar el bucle.
            registro.registrar_evento(
                "FALLA", nombre, f"Error en un oyente: {error}")
# LABORATORIO: fin


def atender(nombre, dato):
    """Ejecuta el manejador del evento y lo anota en la bitacora.

    Devuelve el registro creado, o None si el evento no tiene manejador.
    Se usa .get() para no provocar un KeyError con un evento desconocido.
    """
    manejador = MANEJADORES.get(nombre)
    if manejador is None:
        return registro.registrar_evento(
            "FALLA", nombre, f"Evento sin manejador registrado: {nombre}")

    try:
        nivel, mensaje = manejador(dato)
    except Exception as error:
        # Un manejador defectuoso no debe tumbar el bucle de monitoreo.
        return registro.registrar_evento(
            "FALLA", nombre, f"Error en el manejador: {error}")

    registro_evento = registro.registrar_evento(nivel, nombre, mensaje)  # LABORATORIO
    _avisar(nombre, registro_evento)                                     # LABORATORIO
    return registro_evento                                               # LABORATORIO


def eventos_conocidos():
    """Nombres de todos los eventos que el sistema sabe atender."""
    return sorted(MANEJADORES.keys())
