"""
dashboard/consola.py
Version de texto del dashboard, por si tkinter no esta disponible o si
se prefiere trabajar sin interfaz grafica.

Usa el mismo nucleo y los mismos sensores que la ventana: lo unico que
cambia es como se presenta la informacion. Esa es la ventaja de haber
separado el motor de la presentacion.
"""

import os
import time

import config
import nucleo
import sensores
import alertas                # LABORATORIO
import almacenamiento as registro

ANCHO = 46


def _barra(porcentaje, ancho=28):
    """Barra de progreso hecha con caracteres."""
    llenos = int(max(0.0, min(100.0, porcentaje)) / 100.0 * ancho)
    return "[" + "#" * llenos + "-" * (ancho - llenos) + "]"


def _limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def _pintar(lecturas):
    _limpiar_pantalla()
    print("=" * 74)
    print(f" NODO {config.NODO} | {config.UBICACION} | "
          f"{time.strftime('%H:%M:%S')}")
    print(f" {config.ESTUDIANTE} | {config.CEDULA} | Grupo {config.GRUPO} | "
          f"{config.ASIGNATURA}")
    print("=" * 74)

    for clave in sensores.LECTORES:
        etiqueta = sensores.etiqueta(clave)
        lectura = lecturas.get(clave)
        if lectura is None:
            print(f" {etiqueta:<14} {'no disponible':<40}")
            continue
        print(f" {etiqueta:<14} {_barra(lectura['porcentaje'])} "
              f"{lectura['valor']:>7g} {lectura['unidad']}")
        print(f" {'':<14} {lectura['detalle']}")

    # LABORATORIO: inicio
    red = nucleo.red()
    estado_red = {True: "CONECTADA", False: "SIN RED", None: "sin lecturas"}
    print(f" {'Conexion':<14} {estado_red[red['conectado']]:<11} {red['detalle']}")
    sonido = alertas.estado()
    if sonido:
        modo = "silencio" if sonido["silencio"] else sonido["salida"]
        ahora = (f"sonando {sonido['nombre']}" if sonido["actual"]
                 else "en espera")
        print(f" {'Alertas':<14} {ahora:<28} cola {len(sonido['cola'])} | {modo}")
    # LABORATORIO: fin
    print("-" * 74)
    print(" Ultimos eventos:")
    for e in registro.eventos()[-8:]:
        print(f"   {e['hora']}  [{e['nivel']:<6}] {e['mensaje'][:52]}")
    print("-" * 74)
    print(" Ctrl+C para terminar")


def iniciar():
    """Bucle de monitoreo en modo texto. No bloquea entre lecturas."""
    nucleo.iniciar()
    ultimo_pintado = 0.0
    try:
        while True:
            resultado = nucleo.ciclo()
            ahora = time.time()
            if ahora - ultimo_pintado >= 1.0:
                _pintar(resultado["lecturas"])
                ultimo_pintado = ahora
            time.sleep(config.REFRESCO_MS / 1000.0)
    except KeyboardInterrupt:
        print("\n Monitoreo detenido por el usuario.")
        nucleo.generar_reporte()
        print(f" Reporte final guardado en {config.ARCHIVO_BITACORA}")
