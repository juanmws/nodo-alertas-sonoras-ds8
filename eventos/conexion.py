"""
eventos/conexion.py
Detector de la conexion de red.

LABORATORIO: modulo nuevo. No modifica detectores.py: la conexion es una
senal nueva y tiene su propio detector.

Combina dos tipos de evento del curso:

  1. Por flanco ... red_desconectada y red_conectada. Solo se avisa cuando
                    el estado CAMBIA respecto al anterior.
  2. Por tiempo ... red_sigue_desconectada. Mientras la red siga caida,
                    se recuerda cada RECORDATORIO_RED_S segundos.

Antirrebote: un cambio se acepta cuando se repite en CONFIRMAR_CAMBIO_RED
lecturas seguidas. Un parpadeo de una sola lectura del Wi-Fi no es un
corte y no debe hacer sonar nada. Es la misma idea de la histeresis,
aplicada a una senal digital.

Se escribe como clase porque necesita recordar su estado entre llamadas
y asi las pruebas pueden crear un detector limpio en cada caso.
"""

import config


class DetectorConexion:

    def __init__(self):
        self.conectado = None        # estado confirmado; None = sin lecturas
        self._cambios = []           # marcas de las lecturas que contradicen
                                     # al estado confirmado
        self._caida_desde = None     # cuando empezo el corte actual
        self._ultimo_aviso = None    # ultima vez que se aviso del corte

    def _segundos(self, desde, hasta):
        return round(hasta - desde, config.DECIMALES_TIEMPO)

    def _recordatorio(self, ahora):
        """Evento por tiempo: lo dispara el reloj, no un cambio de senal."""
        if self.conectado is not False:
            return []
        if ahora - self._ultimo_aviso < config.RECORDATORIO_RED_S:
            return []
        self._ultimo_aviso = ahora
        return [("red_sigue_desconectada",
                 {"segundos": self._segundos(self._caida_desde, ahora)})]

    def _caida(self, desde, ahora):
        self.conectado = False
        self._caida_desde = desde
        self._ultimo_aviso = ahora
        return [("red_desconectada", {"segundos": self._segundos(desde, ahora)})]

    def revisar(self, conectado, ahora):
        """Recibe la lectura actual (True/False) y la hora; devuelve la
        lista de eventos (nombre, dato) que provoca."""
        if conectado is None:                  # el sensor no respondio
            return []

        if self.conectado is None:             # primera lectura
            if conectado:
                self.conectado = True
                return []
            # Arrancar sin red tambien merece aviso.
            return self._caida(ahora, ahora)

        if conectado == self.conectado:        # sin cambio: el rebote se olvida
            self._cambios.clear()
            return self._recordatorio(ahora)

        self._cambios.append(ahora)
        if len(self._cambios) < config.CONFIRMAR_CAMBIO_RED:
            return self._recordatorio(ahora)   # aun no se confirma

        # Cambio confirmado: FLANCO. Cuenta desde la primera lectura distinta.
        desde = min(self._cambios)
        self._cambios.clear()
        if not conectado:
            return self._caida(desde, ahora)

        segundos = self._segundos(self._caida_desde, desde)
        self.conectado = True
        self._caida_desde = None
        self._ultimo_aviso = None
        return [("red_conectada", {"segundos": segundos})]
