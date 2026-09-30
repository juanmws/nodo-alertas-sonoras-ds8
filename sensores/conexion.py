"""
sensores/conexion.py
Indica si el equipo tiene conexion de red.

LABORATORIO: modulo nuevo.

red.py mide cuantos KB/s pasan por la red, pero un equipo desconectado
marca casi 0 KB/s igual que uno conectado y en reposo. Este sensor
responde otra pregunta: existe alguna interfaz real, activa y con una
direccion IPv4 valida?

No se hace ping ni se abre una conexion hacia Internet: sin red, eso
puede tardar varios segundos en fallar y congelaria el ciclo. Consultar
las interfaces del sistema es inmediato.

A proposito NO se registra en sensores.LECTORES: asi no pasa por los
detectores originales, que quedan intactos. Lo consulta nucleo.py.
"""

import socket

import psutil

import config

ETIQUETA = "Conexion"


def _ignorada(nombre):
    """Interfaces virtuales (VPN, maquinas virtuales, Docker, WSL...)."""
    return nombre.lower().startswith(config.INTERFACES_IGNORADAS)


def _ip_valida(direccion):
    """Descarta 127.x (el propio equipo) y 169.254.x (sin servidor DHCP)."""
    return not direccion.startswith(config.PREFIJOS_IP_SIN_RED)


def interfaces_activas(estados=None, direcciones=None):
    """Lista de (interfaz, ipv4) que dan conexion real.

    Los parametros permiten probar la funcion con datos inventados; en el
    programa se dejan en None y se consultan a psutil.
    """
    estados = psutil.net_if_stats() if estados is None else estados
    direcciones = psutil.net_if_addrs() if direcciones is None else direcciones
    activas = []
    for nombre, estado in estados.items():
        if not estado.isup or _ignorada(nombre):
            continue
        for d in direcciones.get(nombre, ()):
            if d.family == socket.AF_INET and _ip_valida(d.address):
                activas.append((nombre, d.address))
                break
    return activas


def disponible():
    try:
        psutil.net_if_stats()
        return True
    except Exception:
        return False


def leer():
    """Diccionario con 'conectado', 'interfaces' y 'detalle', o None."""
    try:
        activas = interfaces_activas()
    except Exception:
        return None
    detalle = ", ".join(f"{nombre} {ip}" for nombre, ip in activas)
    return {
        "conectado": bool(activas),
        "interfaces": activas,
        "detalle": detalle or "ninguna interfaz con direccion IP",
    }
