"""
config.py
Parametros de configuracion del nodo de telemetria.

Todo lo que puede cambiar entre una instalacion y otra vive aqui.
Ningun otro archivo del proyecto debe contener un numero literal.

Unidad 2 - Programacion en Python para sistemas IoT
Facultad de Ingenieria de Sistemas Computacionales - UTP
"""

import os

# --------------------------------------------------------------------------
# Identificacion del nodo
# --------------------------------------------------------------------------
NODO = "macbook-juanwilson"
UBICACION = "FISC - Universidad Tecnologica de Panama"

# Datos del estudiante que se muestran en el panel de control.
ESTUDIANTE = "Juan Wilson"
CEDULA = "8-1016-1882"
GRUPO = "1GS134"
ASIGNATURA = "Desarrollo de Software VIII"

# --------------------------------------------------------------------------
# Periodos de muestreo, en segundos.
# Cada metrica tiene el suyo: leer los procesos es caro, leer la CPU no.
# --------------------------------------------------------------------------
PERIODO_RAPIDO = 1.0      # cpu, memoria, red
PERIODO_LENTO = 5.0       # disco, procesos, bateria
PERIODO_REPORTE = 30.0    # resumen periodico hacia la bitacora

REFRESCO_MS = 200         # cada cuanto refresca el dashboard (milisegundos)

# --------------------------------------------------------------------------
# Umbrales. Dos valores por metrica: uno para entrar en alarma y otro,
# mas bajo, para salir de ella. Esa diferencia es la HISTERESIS y evita
# que una lectura oscilando en el limite genere decenas de eventos falsos.
# --------------------------------------------------------------------------
CPU_ALTO = 70.0
CPU_BAJO = 50.0
CPU_NUCLEO_SATURADO = 90.0    # un nucleo individual por encima de esto

RAM_ALTA = 85.0
RAM_BAJA = 75.0

DISCO_LLENO = 90.0            # porcentaje de ocupacion
DISCO_ALIVIADO = 85.0

RED_PICO_KBS = 500.0          # kilobytes por segundo
RED_CALMA_KBS = 200.0

BATERIA_BAJA = 20.0
BATERIA_RECUPERADA = 30.0

PROCESO_PESADO = 50.0         # % de CPU de un solo proceso

# Variacion brusca entre dos muestras consecutivas: evento de anomalia.
SALTO_ANOMALO = 40.0

# --------------------------------------------------------------------------
# Ventana movil y almacenamiento
# --------------------------------------------------------------------------
VENTANA = 10              # muestras que se promedian para evaluar el umbral
MAX_EVENTOS_LOG = 200     # eventos que se conservan en pantalla
ARCHIVO_BITACORA = "bitacora.json"

# --------------------------------------------------------------------------
# Unidad de disco a vigilar. Se detecta sola segun el sistema operativo.
# --------------------------------------------------------------------------
UNIDAD_DISCO = "C:\\" if os.name == "nt" else "/"

# Cantidad de procesos que se muestran en el ranking.
TOP_PROCESOS = 8

# Procesos del sistema que no vale la pena reportar: en Linux los
# 'kworker' y 'kthread' aparecen y desaparecen constantemente y llenarian
# la bitacora de ruido.
PROCESOS_IGNORADOS = ("kworker", "kthread", "ksoftirqd", "migration",
                      "rcu_", "irq/", "svchost")


# ==========================================================================
# LABORATORIO: inicio del bloque de alertas sonoras (Laboratorio N.°1)
# Todo sonido, tiempo y umbral de las alertas vive aqui. Ningun modulo del
# paquete alertas ni de la deteccion de conexion contiene numeros literales.
# ==========================================================================
import tempfile

# --------------------------------------------------------------------------
# Modo silencioso (seccion J, punto 2): el reproductor sigue funcionando
# con sus colas y marcas de tiempo, pero no emite sonido. Se activa aqui,
# con "python main.py --silencio" o con el boton del dashboard.
# --------------------------------------------------------------------------
MODO_SILENCIOSO = False

# --------------------------------------------------------------------------
# Conexion de red
# --------------------------------------------------------------------------
PERIODO_CONEXION = 1.0        # cada cuanto se revisa si hay conexion (s)
CONFIRMAR_CAMBIO_RED = 2      # lecturas seguidas iguales antes de aceptar
                              # un cambio: un parpadeo del Wi-Fi no es un corte
RECORDATORIO_RED_S = 15.0     # cada cuanto se recuerda que la red sigue caida
DECIMALES_TIEMPO = 1          # redondeo de los segundos en los mensajes

# Direcciones que no cuentan como conexion: la del propio equipo (127.x) y
# la que Windows y macOS se asignan solos cuando no hay red (169.254.x).
PREFIJOS_IP_SIN_RED = ("127.", "169.254.")

# Interfaces virtuales que tienen IP aunque el equipo no tenga red real:
# VPN, maquinas virtuales, Docker, WSL y los enlaces internos de Apple.
# Se comparan por el inicio del nombre, sin importar mayusculas. El
# loopback no hace falta listarlo: su unica IP empieza con 127.
INTERFACES_IGNORADAS = ("utun", "awdl", "llw", "anpi", "bridge", "ap1",
                        "gif", "stf", "vmnet", "vboxnet", "docker", "veth",
                        "virtualbox", "vmware", "vethernet")

# --------------------------------------------------------------------------
# Sintesis del sonido: cada alerta se convierte en un archivo WAV al
# arrancar el nodo, para que reproducirla despues no cueste nada.
# --------------------------------------------------------------------------
TASA_MUESTREO = 22050         # muestras por segundo
CANALES = 1                   # mono
BYTES_POR_MUESTRA = 2         # 16 bits
MAXIMO_MUESTRA = 32767        # valor maximo de una muestra de 16 bits
VOLUMEN = 0.55                # fraccion del volumen maximo (0 a 1)
RAMPA_MS = 8                  # subida y bajada suave de cada nota: sin
                              # ella el parlante hace "clic" al empezar
MS_POR_SEGUNDO = 1000.0
CARPETA_SONIDOS = os.path.join(tempfile.gettempdir(), "nodo_alertas_wav")

# Timbres: lista de (armonico, peso). El puro es una sola onda senoidal;
# el brillante suma armonicos impares y suena mas aspero y urgente.
TIMBRES = {
    "puro": ((1, 1.0),),
    "brillante": ((1, 1.0), (3, 0.35), (5, 0.18)),
}

# Notas usadas, en hercios.
SOL4 = 392
DO5 = 523
MI5 = 659
SOL5 = 784
LA5 = 880
DO6 = 1047
MI6 = 1319
SOL6 = 1568

# --------------------------------------------------------------------------
# Reproductor no bloqueante
# --------------------------------------------------------------------------
MAX_COLA_ALERTAS = 5          # alertas en espera; una cola sin tope podria
                              # acumular minutos de sonido atrasado
ENFRIAMIENTO_S = 10.0         # la misma alerta no se repite antes de esto
PAUSA_ENTRE_ALERTAS_MS = 600  # silencio entre dos alertas seguidas
MAX_HISTORIAL_SONIDOS = 6     # ultimas alertas que muestra el dashboard
MAX_MS_ACTUALIZAR = 5.0       # tiempo maximo aceptable de una vuelta del
                              # reproductor; lo comprueban las pruebas

# --------------------------------------------------------------------------
# Tabla de alertas sonoras. Cada alerta es una melodia corta:
#   notas         lista de (frecuencia Hz, duracion ms)
#   pausa_ms      silencio entre una nota y la siguiente
#   repeticiones  veces que se toca la melodia completa
#   pausa_rep_ms  silencio entre repeticiones
#   timbre        clave de TIMBRES
#   urgente       True: pasa al frente de la cola
#   cancela       alertas pendientes que pierden sentido si esta suena
#   descripcion   como se escucha, para el dashboard y el informe
# --------------------------------------------------------------------------
SONIDOS = {
    "cpu_alta": {
        "notas": ((LA5, 90), (LA5, 90), (LA5, 90)),
        "pausa_ms": 60, "repeticiones": 2, "pausa_rep_ms": 260,
        "timbre": "brillante", "urgente": False, "cancela": (),
        "descripcion": "tres pitidos agudos y rapidos, dos veces",
    },
    "ram_alta": {
        "notas": ((DO5, 380), (SOL4, 520)),
        "pausa_ms": 90, "repeticiones": 2, "pausa_rep_ms": 300,
        "timbre": "puro", "urgente": False, "cancela": (),
        "descripcion": "dos notas graves y largas que bajan",
    },
    "red_pico": {
        "notas": ((DO6, 55), (MI6, 55), (SOL6, 55)),
        "pausa_ms": 25, "repeticiones": 3, "pausa_rep_ms": 120,
        "timbre": "puro", "urgente": False, "cancela": (),
        "descripcion": "gorjeo corto que sube, tres rafagas",
    },
    "red_desconectada": {
        "notas": ((SOL5, 200), (MI5, 200), (DO5, 200), (SOL4, 420)),
        "pausa_ms": 50, "repeticiones": 2, "pausa_rep_ms": 350,
        "timbre": "brillante", "urgente": True, "cancela": ("red_conectada",),
        "descripcion": "escala de cuatro notas que cae, dos veces",
    },
    "red_sigue_desconectada": {
        "notas": ((SOL4, 160), (SOL4, 160)),
        "pausa_ms": 140, "repeticiones": 1, "pausa_rep_ms": 0,
        "timbre": "brillante", "urgente": False, "cancela": (),
        "descripcion": "dos toques graves, como quien toca la puerta",
    },
    "red_conectada": {
        "notas": ((SOL4, 110), (DO5, 110), (MI5, 110), (SOL5, 260)),
        "pausa_ms": 30, "repeticiones": 1, "pausa_rep_ms": 0,
        "timbre": "puro", "urgente": True,
        "cancela": ("red_desconectada", "red_sigue_desconectada"),
        "descripcion": "la escala de la desconexion al reves: sube",
    },
    "cpu_normal": {
        "notas": ((MI5, 120), (DO6, 200)),
        "pausa_ms": 40, "repeticiones": 1, "pausa_rep_ms": 0,
        "timbre": "puro", "urgente": False, "cancela": ("cpu_alta",),
        "descripcion": "dos notas suaves que suben: problema resuelto",
    },
    "ram_normal": {
        "notas": ((MI5, 120), (DO6, 200)),
        "pausa_ms": 40, "repeticiones": 1, "pausa_rep_ms": 0,
        "timbre": "puro", "urgente": False, "cancela": ("ram_alta",),
        "descripcion": "dos notas suaves que suben: problema resuelto",
    },
    "red_calma": {
        "notas": ((MI5, 120), (DO6, 200)),
        "pausa_ms": 40, "repeticiones": 1, "pausa_rep_ms": 0,
        "timbre": "puro", "urgente": False, "cancela": ("red_pico",),
        "descripcion": "dos notas suaves que suben: problema resuelto",
    },
}

# Nombre legible de cada alerta en el dashboard.
NOMBRES_ALERTA = {
    "cpu_alta": "CPU alta",
    "ram_alta": "Memoria alta",
    "red_pico": "Pico de trafico",
    "red_desconectada": "Red desconectada",
    "red_sigue_desconectada": "Red sigue caida",
    "red_conectada": "Red recuperada",
    "cpu_normal": "CPU normal",
    "ram_normal": "Memoria normal",
    "red_calma": "Trafico normal",
}

# Orden de la demostracion "python main.py --probar-alertas": una alerta
# de cada tipo (las tres de normalizacion suenan igual).
ORDEN_PRUEBA = ("cpu_alta", "cpu_normal", "ram_alta", "red_pico",
                "red_desconectada", "red_sigue_desconectada", "red_conectada")

SEPARADOR = "-" * 64          # linea de la salida de --probar-alertas

# --------------------------------------------------------------------------
# Generador: trafico de red para provocar red_pico
# --------------------------------------------------------------------------
# Archivos de prueba de velocidad. Si uno falla se intenta el siguiente.
URLS_TRAFICO = ("https://proof.ovh.net/files/1Gb.dat",
                "http://speedtest.tele2.net/1GB.zip")
AGENTE_HTTP = "nodo-telemetria-utp/1.0"
TRAFICO_SEGUNDOS = 15
TRAFICO_BLOQUE = 65536        # bytes leidos por vuelta
TRAFICO_ESPERA = 5            # segundos maximos para conectar con el servidor
BYTES_POR_MB = 1024 * 1024
CORTE_RED_SEGUNDOS = 40       # duracion del corte de Wi-Fi de la prueba
INTERFAZ_WIFI_MAC = "en0"

# --------------------------------------------------------------------------
# Apariencia del panel de alertas del dashboard
# --------------------------------------------------------------------------
FUENTE_PANEL = ("Segoe UI", 10, "bold")
FUENTE_PANEL_GRANDE = ("Segoe UI", 13, "bold")
FUENTE_PANEL_TENUE = ("Segoe UI", 9)
ECUALIZADOR_BARRAS = 7
ECUALIZADOR_ANCHO = 6
ECUALIZADOR_SEPARACION = 3
ECUALIZADOR_ALTO = 26
ECUALIZADOR_MINIMO = 3        # altura de las barras en reposo
ECUALIZADOR_VELOCIDAD = 9.0   # que tan rapido ondulan las barras
ECUALIZADOR_DESFASE = 0.9     # diferencia de fase entre barras vecinas
INDICADOR_RED = 14            # diametro del circulo de estado de la red
MARGEN = 10                   # separacion general dentro del panel
MARGEN_PANEL = 14             # separacion del panel con el borde de la ventana
GEOMETRIA_VENTANA = "1120x780" # antes 1120x740; el panel nuevo ocupa ~90 px
MUESTRAS_CICLO = 25           # vueltas promediadas (25 x 200 ms = 5 s)
MARGEN_CHICO = 4
# LABORATORIO: fin del bloque de alertas sonoras
