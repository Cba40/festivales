"""Tests del evaluador de cumplimiento de Protocolos de Control de Observaciones.

Dos capas:

1. ``TestEvaluateTrigger`` y los formateadores: funciones puras, sin base.
2. ``TestObservationComplianceEvaluator``: el recorrido completo contra una
   sesion async con ``AsyncMock``, que devuelve las filas que cada consulta pide
   (protocolos, prediccion, observaciones, zonas).

Se testea tambien el caso en el que el metric trigger **no** trae dato, que es
el riesgo de un falso positivo: una regla no puede afirmar que se supero un
umbral sobre una metrica ausente.
"""