"""
Paquete dashboard
-----------------
Dos presentaciones distintas para el mismo motor de monitoreo:

    ventana.py   interfaz grafica con tkinter
    consola.py   version de texto, por si tkinter no esta disponible

Ninguna de las dos sabe que es un porcentaje de CPU o un byte de red:
ambas reciben el diccionario estandar que devuelve cada sensor y lo
dibujan igual. Por eso agregar una metrica nueva no obliga a tocar el
dashboard.
"""
