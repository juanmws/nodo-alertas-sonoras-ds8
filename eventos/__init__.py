"""
Paquete eventos
---------------
Separa dos responsabilidades que siempre se confunden:

  detectores.py  decide SI ocurrio un evento  (mira los numeros)
  manejadores.py decide QUE HACER con el      (reacciona)
  despachador.py conecta uno con otro         (diccionario evento -> funcion)

Gracias a esa separacion se puede cambiar la reaccion a un evento sin
tocar la logica que lo detecta, y viceversa.
"""

from .detectores import detectar
from .despachador import atender, eventos_conocidos, suscribir  # LABORATORIO
from .conexion import DetectorConexion                          # LABORATORIO
