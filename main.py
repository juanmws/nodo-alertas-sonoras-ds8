"""
main.py
Punto de entrada del nodo de telemetria.

Fijese en lo que NO hay en este archivo: ni un umbral, ni un periodo,
ni una llamada a psutil, ni un if encadenado decidiendo que hacer con
cada evento. Todo eso vive en su modulo. main.py solo elige la
presentacion y arranca.

Uso:
    python main.py              dashboard grafico (tkinter)
    python main.py --consola    dashboard de texto
    python main.py --revisar    comprueba el entorno y sale
    python main.py --silencio   cualquiera de los anteriores, sin sonido  (LABORATORIO)
    python main.py --probar-alertas   toca todas las alertas y sale       (LABORATORIO)
"""

import sys
import time            # LABORATORIO

import config          # LABORATORIO


def revisar_entorno():
    """Comprueba que todo lo necesario este instalado."""
    print("Revision del entorno")
    print("-" * 40)

    try:
        import psutil
        print(f"  psutil          OK  (version {psutil.__version__})")
    except ImportError:
        print("  psutil          FALTA -> pip install psutil")
        return False

    try:
        import tkinter
        print(f"  tkinter         OK  (Tk {tkinter.TkVersion})")
    except ImportError:
        print("  tkinter         FALTA -> use: python main.py --consola")

    import sensores
    activos = sensores.disponibles()
    print("-" * 40)
    for clave, modulo in sensores.LECTORES.items():
        estado = "disponible" if clave in activos else "NO disponible"
        print(f"  {modulo.ETIQUETA:<14} {estado}")
    # LABORATORIO: inicio
    from sensores import conexion
    from alertas import salidas
    red = conexion.leer()
    print(f"  {'Conexion':<14} {red['detalle'] if red else 'NO disponible'}")
    print(f"  {'Audio':<14} {salidas.crear().NOMBRE}")
    # LABORATORIO: fin
    print("-" * 40)
    print("La bateria aparece como NO disponible en computadoras de")
    print("escritorio. No es un error: es un sensor ausente y el")
    print("programa lo maneja como tal.")
    return True


# LABORATORIO: inicio
def probar_alertas():
    """Toca una alerta de cada tipo con el mismo reproductor no bloqueante.

    Anota la hora de cada vuelta del bucle. Si el sonido bloqueara, entre
    dos vueltas habria un hueco tan largo como la melodia; como no
    bloquea, el hueco maximo queda cerca de REFRESCO_MS.
    """
    import itertools
    import alertas
    reproductor = alertas.iniciar()
    modo = "  (MODO SILENCIOSO)" if reproductor.silencio else ""
    print(f"Salida de audio: {reproductor.nombre_salida()}{modo}")
    print(config.SEPARADOR)
    alertas.probar_todas()
    marcas = []
    anterior = None
    inicio = time.monotonic()
    while alertas.ocupado():
        marcas.append(time.monotonic())
        alertas.actualizar()
        estado = alertas.estado()
        if estado["actual"] and estado["actual"] != anterior:
            transcurrido = time.monotonic() - inicio
            print(f"{transcurrido:6.2f} s  vuelta {len(marcas):>4}  "
                  f"{estado['nombre']:<18} {estado['descripcion']}")
        anterior = estado["actual"]
        time.sleep(config.REFRESCO_MS / config.MS_POR_SEGUNDO)
    huecos = [b - a for a, b in itertools.pairwise(marcas)]
    print(config.SEPARADOR)
    print(f"{len(marcas)} vueltas del ciclo en {time.monotonic() - inicio:.1f} s")
    print(f"Hueco maximo entre dos vueltas: "
          f"{max(huecos) * config.MS_POR_SEGUNDO:.0f} ms "
          f"(periodo configurado: {config.REFRESCO_MS} ms)")
# LABORATORIO: fin


def main():
    if "--silencio" in sys.argv:            # LABORATORIO
        config.MODO_SILENCIOSO = True       # LABORATORIO

    if "--probar-alertas" in sys.argv:      # LABORATORIO
        probar_alertas()                    # LABORATORIO
        return                              # LABORATORIO

    if "--revisar" in sys.argv:
        revisar_entorno()
        return

    if "--consola" in sys.argv:
        from dashboard import consola
        consola.iniciar()
        return

    try:
        from dashboard import ventana
    except ImportError:
        print("tkinter no esta disponible en este equipo.")
        print("Se inicia el dashboard de consola.")
        from dashboard import consola
        consola.iniciar()
        return

    ventana.iniciar()


if __name__ == "__main__":
    main()
