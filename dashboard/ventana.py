"""
dashboard/ventana.py
Interfaz grafica del nodo, escrita con tkinter (viene con Python).

Es programacion orientada a eventos en estado puro:

  - after(ms, funcion) es el temporizador que dispara el refresco;
    cumple el mismo papel que las marcas de tiempo del nucleo, pero
    dentro del bucle de la interfaz.
  - command=funcion registra el manejador de cada boton. Se escribe
    sin parentesis: se pasa la funcion, no su resultado.
  - protocol('WM_DELETE_WINDOW', ...) es el manejador del evento de
    cerrar la ventana.

La ventana nunca bloquea: cada refresco llama a nucleo.ciclo(), que
devuelve enseguida, y vuelve a programarse.
"""

import math                   # LABORATORIO
from collections import deque # LABORATORIO
import sys
import time                   # LABORATORIO
import tkinter as tk

import config
import nucleo
import sensores
import alertas                # LABORATORIO
import almacenamiento as registro

# --------------------------------------------------------------------------
# Paleta
# --------------------------------------------------------------------------
FONDO = "#11161d"
TARJETA = "#1b232e"
BORDE = "#2b3643"
TEXTO = "#e6edf3"
TENUE = "#8b98a8"

VERDE = "#3fb950"
AMBAR = "#d29922"
ROJO = "#f85149"
MAGENTA = "#bc8cff"
AZUL = "#58a6ff"

COLOR_NIVEL = {"INFO": TENUE, "AVISO": AMBAR,
               "ALERTA": ROJO, "FALLA": MAGENTA}

ANCHO_BARRA = 300
ALTO_BARRA = 14

_tarjetas = {}
_pausado = False
_ventana = None
_lista_eventos = None
_lista_procesos = None
_estado_texto = None
_reloj = None
_ultimo_evento = None        # LABORATORIO: ultimo registro mostrado, no un conteo

# LABORATORIO: inicio
# Color de cada alerta sonora en el panel: rojo lo critico, ambar los
# avisos y verde lo que anuncia que un problema se resolvio.
COLOR_SONIDO = {"cpu_alta": ROJO, "ram_alta": ROJO, "red_desconectada": ROJO,
                "red_pico": AMBAR, "red_sigue_desconectada": AMBAR}
_panel = {}                   # widgets del panel de alertas
_boton_sonido = None
_duracion_ciclo = deque(maxlen=config.MUESTRAS_CICLO)   # ultimas vueltas
# LABORATORIO: fin


def _color_barra(clave, lectura):
    """El color de la barra depende de si la metrica esta en alarma."""
    if lectura is None:
        return BORDE
    p = lectura["porcentaje"]
    if clave == "bateria":
        if lectura["valor"] <= config.BATERIA_BAJA:
            return ROJO
        return VERDE if lectura["extra"]["conectado"] else AZUL
    if p >= 85:
        return ROJO
    if p >= 60:
        return AMBAR
    return VERDE


def _crear_tarjeta(padre, clave, fila, columna):
    """Construye una tarjeta de metrica y devuelve sus widgets."""
    marco = tk.Frame(padre, bg=TARJETA, highlightbackground=BORDE,
                     highlightthickness=1)
    marco.grid(row=fila, column=columna, padx=8, pady=8, sticky="nsew")

    titulo = tk.Label(marco, text=sensores.etiqueta(clave), bg=TARJETA,
                      fg=TENUE, font=("Segoe UI", 10, "bold"), anchor="w")
    titulo.pack(fill="x", padx=14, pady=(12, 0))

    valor = tk.Label(marco, text="--", bg=TARJETA, fg=TEXTO,
                     font=("Segoe UI", 26, "bold"), anchor="w")
    valor.pack(fill="x", padx=14)

    barra = tk.Canvas(marco, width=ANCHO_BARRA, height=ALTO_BARRA,
                      bg=FONDO, highlightthickness=0)
    barra.pack(fill="x", padx=14, pady=(2, 6))

    detalle = tk.Label(marco, text="sin datos", bg=TARJETA, fg=TENUE,
                       font=("Segoe UI", 9), anchor="w", justify="left")
    detalle.pack(fill="x", padx=14, pady=(0, 12))

    return {"marco": marco, "valor": valor, "barra": barra,
            "detalle": detalle}


def _dibujar_barra(canvas, porcentaje, color):
    canvas.delete("all")
    ancho = max(canvas.winfo_width(), ANCHO_BARRA)
    canvas.create_rectangle(0, 0, ancho, ALTO_BARRA, fill=BORDE, width=0)
    largo = max(0, min(100.0, porcentaje)) / 100.0 * ancho
    if largo > 0:
        canvas.create_rectangle(0, 0, largo, ALTO_BARRA, fill=color, width=0)


def _actualizar_tarjetas(lecturas):
    for clave, widgets in _tarjetas.items():
        lectura = lecturas.get(clave)
        if lectura is None:
            widgets["valor"].config(text="--", fg=TENUE)
            widgets["detalle"].config(text="sensor no disponible")
            _dibujar_barra(widgets["barra"], 0, BORDE)
            continue
        widgets["valor"].config(
            text=f"{lectura['valor']:g} {lectura['unidad']}", fg=TEXTO)
        widgets["detalle"].config(text=lectura["detalle"])
        _dibujar_barra(widgets["barra"], lectura["porcentaje"],
                       _color_barra(clave, lectura))


def _actualizar_procesos(lecturas):
    lectura = lecturas.get("procesos")
    _lista_procesos.delete(0, tk.END)
    if lectura is None:
        _lista_procesos.insert(tk.END, "  sensor no disponible")
        return
    _lista_procesos.insert(tk.END, f"  {'PID':>7}  {'PROCESO':<24}"
                                   f"{'CPU':>7}{'RAM':>7}")
    for p in lectura["extra"]["top"]:
        _lista_procesos.insert(
            tk.END, f"  {p['pid']:>7}  {p['nombre']:<24}"
                    f"{p['cpu']:>6.1f}%{p['ram']:>6.1f}%")


def _actualizar_eventos():
    """Agrega a la lista solo los eventos que aun no se han mostrado."""
    global _ultimo_evento
    todos = registro.eventos()
    # LABORATORIO: inicio
    # Correccion: la bitacora es un deque(maxlen=MAX_EVENTOS_LOG). Al
    # llenarse, su largo deja de crecer y comparar largos hacia creer que
    # no habia eventos nuevos: la lista se congelaba. Ahora se busca el
    # ultimo registro mostrado y se agregan los que vienen despues de el.
    posiciones = [i for i, e in enumerate(todos) if e is _ultimo_evento]
    nuevos = todos[posiciones[0] + 1:] if posiciones else todos
    if not posiciones:                   # primera vez o bitacora limpiada
        _lista_eventos.delete(0, tk.END)
    for e in nuevos:
        linea = f" {e['hora']}  [{e['nivel']:<6}] {e['mensaje']}"
        _lista_eventos.insert(tk.END, linea)
        _lista_eventos.itemconfig(tk.END,
                                  fg=COLOR_NIVEL.get(e["nivel"], TEXTO))
    sobrantes = _lista_eventos.size() - config.MAX_EVENTOS_LOG
    if sobrantes > 0:
        _lista_eventos.delete(0, sobrantes - 1)
    if nuevos:
        _lista_eventos.see(tk.END)
        _ultimo_evento = nuevos[-1]
    # LABORATORIO: fin


# LABORATORIO: inicio
# --------------------------------------------------------------------------
# Panel de alertas sonoras y conexion de red
# --------------------------------------------------------------------------
def _columna_panel(padre, columna, titulo):
    """Una columna del panel: titulo, fila principal y detalle."""
    marco = tk.Frame(padre, bg=TARJETA)
    marco.grid(row=0, column=columna, sticky="nsew",
               padx=config.MARGEN, pady=config.MARGEN)
    tk.Label(marco, text=titulo, bg=TARJETA, fg=TENUE,
             font=config.FUENTE_PANEL, anchor="w").pack(fill="x")
    fila = tk.Frame(marco, bg=TARJETA)
    fila.pack(fill="x", pady=(config.MARGEN_CHICO, 0))
    detalle = tk.Label(marco, text="", bg=TARJETA, fg=TENUE, anchor="w",
                       font=config.FUENTE_PANEL_TENUE, justify="left")
    detalle.pack(fill="x")
    return fila, detalle


def _crear_panel_alertas(padre):
    marco = tk.Frame(padre, bg=TARJETA, highlightbackground=BORDE,
                     highlightthickness=1)
    marco.pack(fill="x", padx=config.MARGEN_PANEL,
               pady=(0, config.MARGEN_CHICO))
    titulos = ("Conexion de red", "Alerta sonora", "Cola y modo")
    columnas = []
    for i, titulo in enumerate(titulos):
        marco.columnconfigure(i, weight=1, uniform="panel")
        columnas.append(_columna_panel(marco, i, titulo))
    (fila_red, _panel["red_detalle"]), \
        (fila_sonido, _panel["sonido_detalle"]), \
        (fila_cola, _panel["cola_detalle"]) = columnas

    # Conexion de red: circulo de color y estado.
    _panel["red_led"] = tk.Canvas(fila_red, width=config.INDICADOR_RED,
                                  height=config.INDICADOR_RED, bg=TARJETA,
                                  highlightthickness=0)
    _panel["red_led"].pack(side="left", padx=(0, config.MARGEN))
    _panel["red_texto"] = tk.Label(fila_red, text="--", bg=TARJETA, fg=TEXTO,
                                   font=config.FUENTE_PANEL_GRANDE)
    _panel["red_texto"].pack(side="left")

    # Alerta que suena, con un ecualizador animado. Si el sonido
    # bloqueara el ciclo, las barras se quedarian congeladas.
    ancho = config.ECUALIZADOR_BARRAS * (config.ECUALIZADOR_ANCHO
                                         + config.ECUALIZADOR_SEPARACION)
    _panel["ecualizador"] = tk.Canvas(fila_sonido, width=ancho,
                                      height=config.ECUALIZADOR_ALTO,
                                      bg=TARJETA, highlightthickness=0)
    _panel["ecualizador"].pack(side="left", padx=(0, config.MARGEN))
    _panel["sonido_texto"] = tk.Label(fila_sonido, text="En espera",
                                      bg=TARJETA, fg=TEXTO,
                                      font=config.FUENTE_PANEL_GRANDE)
    _panel["sonido_texto"].pack(side="left")

    # Modo y cola.
    _panel["modo"] = tk.Label(fila_cola, text="--", bg=TARJETA, fg=TEXTO,
                              font=config.FUENTE_PANEL_GRANDE)
    _panel["modo"].pack(side="left")


def _dibujar_ecualizador(activo, color):
    canvas = _panel["ecualizador"]
    canvas.delete("all")
    t = time.monotonic() * config.ECUALIZADOR_VELOCIDAD
    paso = config.ECUALIZADOR_ANCHO + config.ECUALIZADOR_SEPARACION
    for i in range(config.ECUALIZADOR_BARRAS):
        alto = config.ECUALIZADOR_MINIMO
        if activo:
            onda = abs(math.sin(t + i * config.ECUALIZADOR_DESFASE))
            alto += (config.ECUALIZADOR_ALTO - config.ECUALIZADOR_MINIMO) * onda
        x = i * paso
        canvas.create_rectangle(x, config.ECUALIZADOR_ALTO - alto,
                                x + config.ECUALIZADOR_ANCHO,
                                config.ECUALIZADOR_ALTO,
                                fill=color if activo else BORDE, width=0)


def _actualizar_panel():
    # ---- red ----
    red = nucleo.red()
    led = _panel["red_led"]
    led.delete("all")
    if red["conectado"] is None:
        color, texto, detalle = TENUE, "Sin lecturas", red["detalle"]
    elif red["conectado"]:
        color, texto, detalle = VERDE, "CONECTADA", red["detalle"]
    else:
        caida = time.time() - red["desde"]
        color, texto = ROJO, "SIN RED"
        detalle = f"caida hace {caida:.0f} s | aviso cada " \
                  f"{config.RECORDATORIO_RED_S:g} s"
    led.create_oval(0, 0, config.INDICADOR_RED, config.INDICADOR_RED,
                    fill=color, width=0)
    _panel["red_texto"].config(text=texto, fg=color)
    _panel["red_detalle"].config(text=detalle)

    # ---- sonido ----
    estado = alertas.estado()
    if estado is None:
        return
    actual = estado["actual"]
    color = TENUE if estado["silencio"] else COLOR_SONIDO.get(actual, VERDE)
    _dibujar_ecualizador(actual is not None, color)
    if actual:
        extra = " (silencio)" if estado["silencio"] else ""
        _panel["sonido_texto"].config(text=estado["nombre"] + extra, fg=color)
        _panel["sonido_detalle"].config(
            text=f"{estado['descripcion']} | quedan {estado['restante']:.1f} s")
    else:
        ultimo = estado["historial"]
        _panel["sonido_texto"].config(text="En espera", fg=TENUE)
        _panel["sonido_detalle"].config(
            text=(f"ultima: {config.NOMBRES_ALERTA[ultimo[0]['alerta']]} "
                  f"a las {ultimo[0]['hora']}") if ultimo
            else "ninguna alerta ha sonado")

    # ---- cola y modo ----
    if estado["silencio"]:
        _panel["modo"].config(text="MODO SILENCIOSO", fg=AMBAR)
    else:
        _panel["modo"].config(text="SONIDO ACTIVO", fg=VERDE)
    cola = ", ".join(estado["cola"]) if estado["cola"] else "vacia"
    ciclo = ""
    if _duracion_ciclo:
        ms = [d * config.MS_POR_SEGUNDO for d in _duracion_ciclo]
        ciclo = (f" | ciclo: prom {sum(ms) / len(ms):.1f} ms, "
                 f"max {max(ms):.1f} ms")
    _panel["cola_detalle"].config(
        text=f"cola: {cola}\n{estado['salida']}{ciclo}")
    if _boton_sonido is not None:
        _boton_sonido.config(text="Con sonido" if estado["silencio"]
                             else "Silenciar")
# LABORATORIO: fin


# --------------------------------------------------------------------------
# Manejadores de los botones
# --------------------------------------------------------------------------
def _alternar_pausa():
    global _pausado
    _pausado = not _pausado
    registro.registrar_evento(
        "INFO", "usuario", "Monitoreo en pausa" if _pausado
        else "Monitoreo reanudado")


def _forzar_reporte():
    nucleo.generar_reporte()


# LABORATORIO: inicio
def _alternar_sonido():
    silencio = alertas.alternar_silencio()
    registro.registrar_evento(
        "INFO", "usuario", "Modo silencioso activado" if silencio
        else "Sonido activado")


def _probar_alertas():
    alertas.probar_todas()
    registro.registrar_evento("INFO", "usuario",
                              "Prueba de todas las alertas sonoras")
# LABORATORIO: fin


def _limpiar():
    registro.limpiar_eventos()
    _lista_eventos.delete(0, tk.END)


def _salir():
    alertas.detener()         # LABORATORIO: que no quede sonando al cerrar
    _ventana.destroy()


# --------------------------------------------------------------------------
# Bucle de refresco
# --------------------------------------------------------------------------
def _refrescar():
    """Se ejecuta cada REFRESCO_MS. Es el manejador del temporizador."""
    if not _pausado:
        inicio = time.perf_counter()                 # LABORATORIO
        resultado = nucleo.ciclo()
        _duracion_ciclo.append(time.perf_counter() - inicio)   # LABORATORIO
        _actualizar_tarjetas(resultado["lecturas"])
        _actualizar_procesos(resultado["lecturas"])
        _actualizar_eventos()

    _estado_texto.config(
        text="PAUSADO" if _pausado else "MONITOREANDO",
        fg=AMBAR if _pausado else VERDE)
    _actualizar_panel()                              # LABORATORIO
    _reloj.config(text=__import__("time").strftime("%H:%M:%S"))

    # Se vuelve a programar a si misma: este es el temporizador.
    _ventana.after(config.REFRESCO_MS, _refrescar)


def iniciar():
    """Arma la ventana y entra en el bucle de eventos de tkinter."""
    global _ventana, _lista_eventos, _lista_procesos, _estado_texto, _reloj

    nucleo.iniciar()

    _ventana = tk.Tk()
    _ventana.title(f"Nodo de telemetria - {config.NODO}")
    _ventana.configure(bg=FONDO)
    _ventana.geometry(config.GEOMETRIA_VENTANA)     # LABORATORIO: mas alta
    _ventana.minsize(900, 640)

    # ---- encabezado ----
    cabecera = tk.Frame(_ventana, bg=FONDO)
    cabecera.pack(fill="x", padx=14, pady=(12, 0))

    tk.Label(cabecera, text=f"{config.NODO}", bg=FONDO, fg=TEXTO,
             font=("Segoe UI", 15, "bold")).pack(side="left")
    tk.Label(cabecera, text=f"  ·  {config.UBICACION}", bg=FONDO, fg=TENUE,
             font=("Segoe UI", 10)).pack(side="left")

    _reloj = tk.Label(cabecera, text="", bg=FONDO, fg=TENUE,
                      font=("Consolas", 11))
    _reloj.pack(side="right", padx=(10, 0))
    _estado_texto = tk.Label(cabecera, text="MONITOREANDO", bg=FONDO,
                             fg=VERDE, font=("Segoe UI", 10, "bold"))
    _estado_texto.pack(side="right")

    # ---- datos del estudiante ----
    datos = tk.Frame(_ventana, bg=FONDO)
    datos.pack(fill="x", padx=14, pady=(2, 0))
    tk.Label(datos, text=f"Estudiante: {config.ESTUDIANTE}  ·  "
                         f"Cedula: {config.CEDULA}  ·  "
                         f"Grupo: {config.GRUPO}  ·  {config.ASIGNATURA}",
             bg=FONDO, fg=AZUL, font=("Segoe UI", 10, "bold")).pack(side="left")

    # ---- tarjetas de metricas ----
    grilla = tk.Frame(_ventana, bg=FONDO)
    grilla.pack(fill="x", padx=6, pady=6)
    for c in range(3):
        grilla.columnconfigure(c, weight=1, uniform="col")

    for i, clave in enumerate(sensores.LECTORES):
        _tarjetas[clave] = _crear_tarjeta(grilla, clave, i // 3, i % 3)

    _crear_panel_alertas(_ventana)                   # LABORATORIO

    # ---- paneles inferiores ----
    inferior = tk.Frame(_ventana, bg=FONDO)
    inferior.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    inferior.columnconfigure(0, weight=1)
    inferior.columnconfigure(1, weight=1)
    inferior.rowconfigure(0, weight=1)

    izq = tk.Frame(inferior, bg=TARJETA, highlightbackground=BORDE,
                   highlightthickness=1)
    izq.grid(row=0, column=0, sticky="nsew", padx=8, pady=4)
    tk.Label(izq, text="Procesos con mayor consumo", bg=TARJETA, fg=TENUE,
             font=("Segoe UI", 10, "bold"), anchor="w").pack(
        fill="x", padx=12, pady=(10, 4))
    _lista_procesos = tk.Listbox(izq, bg=TARJETA, fg=TEXTO, bd=0,
                                 font=("Consolas", 9),
                                 highlightthickness=0,
                                 selectbackground=BORDE, activestyle="none")
    _lista_procesos.pack(fill="both", expand=True, padx=6, pady=(0, 10))

    der = tk.Frame(inferior, bg=TARJETA, highlightbackground=BORDE,
                   highlightthickness=1)
    der.grid(row=0, column=1, sticky="nsew", padx=8, pady=4)
    tk.Label(der, text="Bitacora de eventos", bg=TARJETA, fg=TENUE,
             font=("Segoe UI", 10, "bold"), anchor="w").pack(
        fill="x", padx=12, pady=(10, 4))
    contenedor = tk.Frame(der, bg=TARJETA)
    contenedor.pack(fill="both", expand=True, padx=6, pady=(0, 10))
    scroll_y = tk.Scrollbar(contenedor, orient="vertical")
    scroll_y.pack(side="right", fill="y")
    scroll_x = tk.Scrollbar(contenedor, orient="horizontal")
    scroll_x.pack(side="bottom", fill="x")
    _lista_eventos = tk.Listbox(contenedor, bg=TARJETA, fg=TEXTO, bd=0,
                                font=("Consolas", 9), highlightthickness=0,
                                selectbackground=BORDE, activestyle="none",
                                yscrollcommand=scroll_y.set,
                                xscrollcommand=scroll_x.set)
    _lista_eventos.pack(side="left", fill="both", expand=True)
    scroll_y.config(command=_lista_eventos.yview)
    scroll_x.config(command=_lista_eventos.xview)

    # ---- botones ----
    pie = tk.Frame(_ventana, bg=FONDO)
    # LABORATORIO: el pie se empaqueta antes que los paneles inferiores
    # para que los botones nunca queden fuera de la ventana.
    pie.pack(fill="x", padx=14, pady=(0, 12), side="bottom", before=inferior)

    def boton(texto, comando, color=BORDE):
        # command recibe la FUNCION, sin parentesis: es un callback.
        if sys.platform == "darwin":
            # En macOS tk.Button ignora el color de fondo y el texto claro
            # queda invisible. Se usa una etiqueta y se registra el
            # manejador del clic con bind().
            b = tk.Label(pie, text=texto, bg=color, fg=TEXTO, padx=16,
                         pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2")
            b.bind("<Button-1>", lambda evento: comando())
        else:
            b = tk.Button(pie, text=texto, command=comando, bg=color,
                          fg=TEXTO, bd=0, padx=16, pady=7,
                          font=("Segoe UI", 9, "bold"),
                          activebackground=AZUL, activeforeground=FONDO,
                          cursor="hand2")
        b.pack(side="left", padx=(0, 8))
        return b

    boton("Pausar / Reanudar", _alternar_pausa)
    boton("Generar reporte", _forzar_reporte)
    boton("Limpiar bitacora", _limpiar)
    global _boton_sonido                             # LABORATORIO
    _boton_sonido = boton("Silenciar", _alternar_sonido)   # LABORATORIO
    boton("Probar alertas", _probar_alertas)         # LABORATORIO
    boton("Salir", _salir)

    tk.Label(pie, text=f"umbrales: CPU {config.CPU_ALTO:g}%  ·  "
                       f"RAM {config.RAM_ALTA:g}%  ·  "
                       f"disco {config.DISCO_LLENO:g}%  ·  "
                       f"red {config.RED_PICO_KBS:g} KB/s",
             bg=FONDO, fg=TENUE, font=("Segoe UI", 8)).pack(side="right")

    _ventana.protocol("WM_DELETE_WINDOW", _salir)   # manejador del cierre
    _ventana.after(config.REFRESCO_MS, _refrescar)  # arranca el temporizador
    _ventana.mainloop()                             # bucle de eventos
