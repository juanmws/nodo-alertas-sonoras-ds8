"""
alertas/reproductor.py
Reproductor de alertas que NO bloquea el ciclo de monitoreo.

LABORATORIO: modulo nuevo.

La tentacion es escribir:

    for frecuencia, duracion in melodia:
        winsound.Beep(frecuencia, duracion)      # espera a que termine
        time.sleep(pausa)                        # y ademas se duerme

Eso congela el dashboard durante toda la melodia. Este reproductor usa el
mismo patron que nucleo.py para leer los sensores:

  - una COLA (collections.deque) con las alertas que esperan su turno;
  - una MARCA DE TIEMPO que dice cuando queda libre el parlante.

actualizar() se llama en cada vuelta del ciclo. Si el parlante sigue
ocupado, devuelve en el acto. Si ya quedo libre, saca la siguiente alerta
de la cola, la manda a sonar en segundo plano y anota la nueva marca.
Nunca hay un sleep() ni una espera.
"""

import time
from collections import deque

import config
from . import sintetizador


class Reproductor:

    def __init__(self, salida, archivo=sintetizador.archivo,
                 duracion=sintetizador.duracion, reloj=time.monotonic,
                 silencio=None):
        self._salida = salida
        self._archivo = archivo          # nombre de alerta -> ruta del WAV
        self._duracion = duracion        # nombre de alerta -> segundos
        self._reloj = reloj
        self.silencio = (config.MODO_SILENCIOSO if silencio is None
                         else silencio)

        # Alertas que esperan su turno. maxlen evita que un minuto de
        # eventos se convierta en un minuto de sonido atrasado.
        self._cola = deque(maxlen=config.MAX_COLA_ALERTAS)

        # Marcas de tiempo.
        self._fin_actual = None          # cuando termina la alerta que suena
        self._libre_en = None            # fin + pausa entre alertas
        self._ultima_vez = {}            # alerta -> cuando se acepto por ultima vez

        self.actual = None               # alerta que esta sonando
        self.historial = deque(maxlen=config.MAX_HISTORIAL_SONIDOS)
        self.error = None

    # ------------------------------------------------------------------
    def _ahora(self, ahora):
        return self._reloj() if ahora is None else ahora

    def encolar(self, nombre, ahora=None, forzar=False):
        """Pone una alerta en espera. Devuelve True si fue aceptada.

        Se rechaza si el evento no tiene sonido, si la misma alerta sono
        hace menos de ENFRIAMIENTO_S, si ya esta en la cola o sonando, o si
        la cola esta llena y la alerta no es urgente.
        """
        patron = config.SONIDOS.get(nombre)
        if patron is None:
            return False
        ahora = self._ahora(ahora)

        ultima = self._ultima_vez.get(nombre)
        enfriando = (ultima is not None
                     and ahora - ultima < config.ENFRIAMIENTO_S)
        if (enfriando and not forzar) or nombre in self._cola:
            return False

        # Una alerta puede dejar sin sentido a otras: si la red volvio, ya
        # no tiene caso anunciar que se cayo.
        for otra in patron["cancela"]:
            if otra in self._cola:
                self._cola.remove(otra)
        if self._sonando(ahora) in patron["cancela"]:
            self._interrumpir()

        if patron["urgente"]:
            # Pasa al frente. Si la cola esta llena, deque descarta sola la
            # ultima, que es la menos importante.
            self._cola.appendleft(nombre)
        elif len(self._cola) == self._cola.maxlen:
            return False
        else:
            self._cola.append(nombre)

        self._ultima_vez[nombre] = ahora
        return True

    def actualizar(self, ahora=None):
        """Una vuelta del reproductor. Nunca espera.

        Devuelve el nombre de la alerta que empezo a sonar en esta vuelta,
        o None si no empezo ninguna.
        """
        ahora = self._ahora(ahora)
        if self._fin_actual is not None and ahora >= self._fin_actual:
            self.actual = None                     # la melodia ya termino
        if self._libre_en is not None and ahora < self._libre_en:
            return None                            # parlante ocupado: seguir
        if not self._cola:
            self._libre_en = None
            return None

        nombre = self._cola.popleft()
        if not self.silencio:
            try:
                self._salida.reproducir(self._archivo(nombre))
                self.error = None
            except OSError as error:
                # Sin parlante o sin reproductor: el monitoreo sigue igual.
                self.error = str(error)

        pausa = config.PAUSA_ENTRE_ALERTAS_MS / config.MS_POR_SEGUNDO
        self.actual = nombre
        self._fin_actual = ahora + self._duracion(nombre)
        self._libre_en = self._fin_actual + pausa
        self.historial.appendleft({"hora": time.strftime("%H:%M:%S"),
                                   "alerta": nombre,
                                   "silencio": self.silencio})
        return nombre

    # ------------------------------------------------------------------
    def _sonando(self, ahora):
        """Alerta que suena en este instante, o None."""
        if self._fin_actual is not None and ahora < self._fin_actual:
            return self.actual
        return None

    def _interrumpir(self):
        """Corta la alerta en curso y deja el parlante libre de inmediato."""
        self._salida.detener()
        self.actual = None
        self._fin_actual = None
        self._libre_en = None

    def alternar_silencio(self):
        self.silencio = not self.silencio
        if self.silencio:
            self._salida.detener()
        return self.silencio

    def restante(self, ahora=None):
        """Segundos que le quedan a la alerta en curso, o None."""
        if self.actual is None or self._fin_actual is None:
            return None
        return max(self._fin_actual - self._ahora(ahora), 0.0)

    def pendientes(self):
        return list(self._cola)

    def nombre_salida(self):
        return self._salida.NOMBRE

    def ocupado(self, ahora=None):
        """True si hay algo sonando, en pausa o esperando en la cola."""
        ahora = self._ahora(ahora)
        return bool(self._cola) or (self._libre_en is not None
                                    and ahora < self._libre_en)

    def detener(self):
        self._cola.clear()
        self._interrumpir()
