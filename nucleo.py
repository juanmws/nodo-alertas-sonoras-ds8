"""
nucleo.py
Motor de monitoreo. Aqui esta el bucle orientado a eventos.

Diseno clave: el ciclo NO usa time.sleep() para esperar. Cada metrica
guarda su propia marca de tiempo y se lee cuando le toca. Asi un solo
ciclo atiende tareas con periodos distintos sin bloquearse, que es el
patron recomendado de la Unidad 2.

La funcion ciclo() no bloquea: se puede llamar cada 200 ms desde un
dashboard grafico o desde un bucle de consola. Ella decide sola que
hay que leer en ese instante.
"""

import time

import config
import sensores
import eventos
import almacenamiento as registro
import alertas                                   # LABORATORIO
from sensores import conexion as sensor_red      # LABORATORIO

# Que metricas se leen rapido y cuales despacio. Consultar los procesos
# es caro; consultar la CPU no lo es.
GRUPO_RAPIDO = ["cpu", "memoria", "red"]
GRUPO_LENTO = ["disco", "procesos", "bateria"]

# Marcas de tiempo: la ultima vez que se ejecuto cada tarea.
_marcas = {"rapido": 0.0, "lento": 0.0, "reporte": 0.0}

# Ultima lectura conocida de cada metrica, para que el dashboard siempre
# tenga algo que mostrar aunque en este instante no toque leer.
_ultimas = {}

_activos = []

# LABORATORIO: inicio
_detector_red = eventos.DetectorConexion()
_red = {"conectado": None, "detalle": "sin lecturas", "desde": None}
# LABORATORIO: fin


def iniciar():
    """Detecta que sensores existen en este equipo y prepara el ciclo."""
    global _activos
    _activos = sensores.disponibles()
    ahora = time.time()
    for clave in _marcas:
        _marcas[clave] = ahora

    # Lectura de calentamiento: se descarta. La CPU siempre devuelve 0.0
    # la primera vez y la red necesita dos contadores para calcular una
    # velocidad. Sin este paso, la primera vuelta generaria eventos falsos.
    for clave in _activos:
        _ultimas[clave] = sensores.leer(clave)

    # LABORATORIO: inicio
    # Las alertas se suscriben al despachador antes del primer evento.
    alertas.iniciar()
    eventos.suscribir(alertas.al_evento)
    _revisar_conexion(ahora)
    _marcas["conexion"] = ahora
    # LABORATORIO: fin

    ausentes = [c for c in sensores.LECTORES if c not in _activos]
    for clave in ausentes:
        eventos.atender("sensor_ausente", {"metrica": clave})

    registro.registrar_evento(
        "INFO", "sistema",
        f"Nodo {config.NODO} iniciado | sensores activos: "
        f"{', '.join(_activos)}")
    return _activos


def _leer_grupo(claves):
    """Lee un grupo de metricas y despacha los eventos que provoquen."""
    nuevos = []
    for clave in claves:
        if clave not in _activos:
            continue
        lectura = sensores.leer(clave)
        _ultimas[clave] = lectura

        if lectura is not None:
            registro.agregar(clave, lectura["valor"])

        for nombre, dato in eventos.detectar(clave, lectura):
            nuevos.append(eventos.atender(nombre, dato))
    return nuevos


# LABORATORIO: inicio
def _revisar_conexion(ahora):
    """Lee el sensor de conexion y despacha lo que detecte su detector."""
    lectura = sensor_red.leer()
    conectado = None if lectura is None else lectura["conectado"]
    nuevos = []
    for nombre, dato in _detector_red.revisar(conectado, ahora):
        nuevos.append(eventos.atender(nombre, dato))
    if lectura is not None:
        _red["detalle"] = lectura["detalle"]
    if _red["conectado"] != _detector_red.conectado:
        _red["desde"] = ahora
    _red["conectado"] = _detector_red.conectado
    return nuevos


def red():
    """Estado confirmado de la conexion, para el dashboard."""
    return dict(_red)
# LABORATORIO: fin


def ciclo():
    """Una vuelta del bucle de monitoreo. No bloquea.

    Devuelve un diccionario con las ultimas lecturas y con los eventos
    generados en esta vuelta.
    """
    ahora = time.time()
    nuevos = []

    if ahora - _marcas["rapido"] >= config.PERIODO_RAPIDO:
        nuevos += _leer_grupo(GRUPO_RAPIDO)
        _marcas["rapido"] = ahora

    # LABORATORIO: inicio
    if ahora - _marcas["conexion"] >= config.PERIODO_CONEXION:
        nuevos += _revisar_conexion(ahora)
        _marcas["conexion"] = ahora
    # LABORATORIO: fin

    if ahora - _marcas["lento"] >= config.PERIODO_LENTO:
        nuevos += _leer_grupo(GRUPO_LENTO)
        _marcas["lento"] = ahora

    # Evento por tiempo: no lo dispara ningun sensor, lo dispara el reloj.
    if ahora - _marcas["reporte"] >= config.PERIODO_REPORTE:
        nuevos.append(generar_reporte())
        _marcas["reporte"] = ahora

    # LABORATORIO: el reproductor avanza una vuelta. No espera: si hay una
    # alerta sonando, devuelve enseguida y el ciclo sigue.
    alertas.actualizar()

    return {"lecturas": dict(_ultimas), "eventos": nuevos}


def generar_reporte():
    """Resume el periodo, lo guarda en la bitacora y vacia el historial."""
    datos = registro.resumen()
    registro.guardar_bitacora(datos)
    registro.limpiar_periodo()
    return eventos.atender("reporte", {"metricas": len(datos["metricas"])})


def lecturas():
    """Ultimas lecturas conocidas, sin forzar una nueva medicion."""
    return dict(_ultimas)


def activos():
    return list(_activos)


if __name__ == "__main__":
    # Prueba del propio modulo: diez vueltas mostrando lo que ocurre.
    iniciar()
    for _ in range(10):
        resultado = ciclo()
        for e in resultado["eventos"]:
            print(f"{e['hora']} [{e['nivel']}] {e['mensaje']}")
        time.sleep(0.5)
