"""Tests del middleware de rate limiting.

Se prueba el backend de memoria con un reloj inyectado, para que el
vencimiento de la ventana sea determinista y la suite no dependa de dormir.
Los tests que pasan por HTTP usan el backend real a traves de la app.
"""