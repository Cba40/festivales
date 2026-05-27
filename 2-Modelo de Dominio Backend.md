Modelo de Dominio Backend
Plataforma de Asistencia Territorial para Eventos Masivos

1. Objetivo del Modelo de Dominio
El objetivo del modelo de dominio es definir:
• las entidades centrales del sistema,
• sus responsabilidades,
• relaciones,
• comportamiento temporal,
• separación entre configuración y estado,
• persistencia histórica,
• flujo operacional del dato.
Este documento establece:
• qué existe en el sistema,
• qué cambia,
• qué se calcula,
• qué se persiste,
• qué pertenece al runtime,
• qué pertenece al histórico.
El objetivo principal es evitar:
• mezcla de responsabilidades,
• acoplamiento excesivo,
• confusión entre estado y configuración,
• arquitecturas CRUD tradicionales,
• pérdida de trazabilidad temporal.

2. Principios del Modelo de Dominio
El dominio debe ser:
• espacio-temporal,
• geoespacial,
• histórico,
• probabilístico,
• multi-evento,
• orientado a señales,
• desacoplado,
• extensible,
• contextual.
El sistema NO debe modelarse como:
• tablas CRUD aisladas,
• listados estáticos,
• entidades sin temporalidad.
La prioridad del dominio es:
representar comportamiento territorial dinámico.

3. Separación Fundamental del Dominio
El sistema debe separar estrictamente:
CapaFunciónConfiguraciónDefine estructura territorialEstado RuntimeEstado actual operacionalSeñalesInputs dinámicosInferenciasResultados calculadosHistóricoPersistencia temporalTelemetríaDatos crudos operacionalesRecomendacionesDecisiones contextualesEsta separación es crítica para escalabilidad y mantenibilidad.

4. Entidades Principales del Dominio

4.1 Municipios
Representa:
la organización territorial administradora.
Ejemplos:
• municipio,
• ciudad,
• entidad organizadora territorial.

Responsabilidades
• administrar eventos,
• configurar territorios,
• operar dashboard,
• cargar señales manuales,
• gestionar incidentes.

Naturaleza
TipoValorConfiguraciónSíRuntimeParcialHistóricoNoGeoespacialNo
Relación principal
• una Municipalidad tiene muchos Events.

4.2 Evento
Representa:
el contexto operacional principal.
Ejemplos:
• festival,
• recital,
• feria,
• evento deportivo,
• peregrinación.

Responsabilidades
• definir contexto temporal,
• asociar territorio,
• habilitar módulos,
• parametrizar comportamiento.

Contiene
• mapas,
• zonas,
• puntos,
• corredores,
• reglas,
• configuraciones,
• umbrales.

Naturaleza
TipoValorConfiguraciónSíRuntimeSíHistóricoParcialGeoespacialNo
Relación principal
• un Evento tiene muchas Zonas,
• muchos Puntos,
• muchos Corredores,
• muchas Señales,
• muchos Snapshots.

4.3 Zona
Representa:
áreas dinámicas territoriales.
Ejemplos:
• estacionamientos,
• corredores gastronómicos,
• áreas descanso,
• zonas descongestión.

Responsabilidades
• representar comportamiento territorial agregado,
• soportar recomendaciones,
• modelar saturación.

Geometría
Polygon

Componentes
Configuración
• nombre,
• tipo,
• geometría,
• capacidad estimada,
• prioridad,
• reglas operativas.
Estado Runtime
• saturación actual,
• densidad,
• accesibilidad,
• velocidad promedio,
• tendencia.
Histórico
• snapshots,
• estados temporales,
• evolución operacional.

Naturaleza
TipoValorConfiguraciónSíRuntimeSíHistóricoSíGeoespacialSí
4.4 Punto
Representa:
ubicaciones exactas.
Ejemplos:
• baños,
• policía,
• sanitarios,
• hidratación,
• asistencia.

Responsabilidades
• navegación inmediata,
• acceso rápido,
• referencia operacional.

Geometría
Point

Componentes
Configuración
• tipo,
• ubicación,
• nombre,
• prioridad.
Runtime
• disponibilidad,
• accesibilidad,
• estado operativo.
Histórico
• cambios de disponibilidad,
• incidentes asociados.

Naturaleza
TipoValorConfiguraciónSíRuntimeSíHistóricoSíGeoespacialSí
4.5 Flow
Representa:
circulación humana o vehicular.
Ejemplos:
• corredores peatonales,
• egresos,
• evacuaciones,
• rutas vehiculares.

Responsabilidades
• modelar circulación,
• detectar congestión,
• evaluar movilidad.

Geometría
LineString o Polygon

Runtime
• velocidad,
• densidad,
• dirección,
• congestión,
• estabilidad.

Histórico
• patrones de circulación,
• comportamiento temporal,
• colapsos históricos.

Naturaleza
TipoValorConfiguraciónSíRuntimeSíHistóricoSíGeoespacialSí
4.6 Signal
Representa:
inputs operacionales dinámicos.
Las señales alimentan:
• estados,
• inferencias,
• recomendaciones,
• probabilidades.

Tipos
• climáticas,
• temporales,
• operativas,
• territoriales,
• históricas,
• telemétricas.

Responsabilidades
• representar cambios contextuales,
• alimentar motores de cálculo.

Naturaleza
TipoValorConfiguraciónNoRuntimeSíHistóricoSíGeoespacialParcial
Importante
Signal NO representa estado.
Representa:
información entrante.

4.7 Incidente
Representa:
eventos operacionales relevantes.
Ejemplos:
• accidente,
• corte,
• colapso,
• emergencia médica,
• congestión extrema.

Responsabilidades
• alterar contexto territorial,
• modificar inferencias,
• afectar accesibilidad.

Naturaleza
TipoValorConfiguraciónNoRuntimeSíHistóricoSíGeoespacialSí
4.8 Snapshot
Representa:
una fotografía temporal del sistema.

Responsabilidades
persistir:
• estados,
• métricas,
• saturaciones,
• comportamiento territorial,
• inferencias temporales.

Importante
Snapshot NO es configuración.
Es:
persistencia histórica operacional.

Naturaleza
TipoValorConfiguraciónNoRuntimeNoHistóricoSíGeoespacialSí
4.9 Recommendation
Representa:
una decisión contextual generada por el sistema.
Ejemplos:
• mejor estacionamiento probable,
• salida recomendada,
• sanitario más accesible.

Responsabilidades
• reducir incertidumbre,
• simplificar decisiones,
• priorizar accesibilidad.

Componentes
• contexto,
• score,
• nivel de confianza,
• timestamp,
• señales utilizadas,
• entidad objetivo.

Naturaleza
TipoValorConfiguraciónNoRuntimeSíHistóricoSíGeoespacialParcial
Importante
Recommendation NO es dato fijo.
Es:
una inferencia contextual temporal.

4.10 Telemetría
Representa:
datos operacionales crudos.
Ejemplos:
• ubicación usuario,
• navegación,
• movimiento agregado,
• consultas,
• tiempos.

Responsabilidades
• alimentar señales,
• alimentar modelos históricos,
• detectar patrones.



Naturaleza
TipoValorConfiguraciónNoRuntimeSíHistóricoSíGeoespacialSí5. Relaciones Principales
Municipalidad
• tiene muchos Events.

Evento
• tiene muchas Zonas,
• tiene muchos Puntos,
• tiene muchos Corredores,
• tiene muchas Señaales,
• tiene muchos Incidentes,
• tiene muchos Snapshots,
• tiene muchas Recomendaciones.

Zone
• pertenece a un Evento,
• posee muchos Snapshots,
• recibe muchas Señales,
• puede estar afectada por muchos Incidentes.

Point
• pertenece a un Evento,
• puede recibir Señales,
• puede tener Snapshots,
• puede ser afectado por Incidentes.

Flow
• pertenece a un Evento,
• recibe Señales,
• posee Snapshots,
• puede colapsar por Incidentes.

Recomendaciones
• pertenece a un contexto temporal,
• referencia entidades territoriales,
• utiliza Señales,
• puede persistirse históricamente.

6. Separación Crítica del Dominio

Configuración
Define:
estructura relativamente estable.
Ejemplos:
• geometrías,
• nombres,
• tipos,
• reglas,
• capacidades base.
Se modifica poco.

Estado Runtime
Define:
estado operacional actual.
Ejemplos:
• saturación,
• congestión,
• disponibilidad,
• accesibilidad.
Cambia constantemente.

Histórico
Define:
persistencia temporal.
Ejemplos:
• snapshots,
• estados anteriores,
• recomendaciones emitidas,
• señales históricas.
Nunca debe sobrescribirse.

Señales
Representan:
inputs dinámicos del sistema.
Ejemplos:
• clima,
• incidentes,
• flujo,
• telemetría.

Inferencias
Representan:
resultados calculados.
Ejemplos:
• saturación probable,
• riesgo,
• accesibilidad,
• recomendación contextual.

7. Modelo Temporal

Qué se versiona
• estados territoriales,
• snapshots,
• recomendaciones,
• señales críticas,
• incidentes,
• métricas operacionales.

Qué se sobrescribe
Puede sobrescribirse:
• cache runtime,
• estado actual calculado.
Nunca:
• histórico.

Qué se calcula
• saturación,
• scores,
• probabilidades,
• accesibilidad,
• riesgo,
• flujo.

Qué se persiste
• snapshots,
• recomendaciones,
• señales,
• incidentes,
• métricas,
• telemetría agregada.

8. Modelo Geoespacial
GeometríaUsoPointbaños, policía, sanitariosPolygonzonas, estacionamientosLineStringflujos, circulación
Capacidades necesarias
• consultas espaciales,
• cercanía,
• intersecciones,
• densidad territorial,
• áreas dinámicas,
• cálculo de rutas,
• análisis de flujo.

9. Modelo Probabilístico
El sistema trabaja mediante:
• inferencia contextual,
• probabilidades,
• señales múltiples,
• comportamiento histórico.


Inputs
• horario,
• clima,
• densidad,
• flujo,
• histórico,
• incidentes,
• accesibilidad,
• telemetría,
• saturación previa.

Outputs
• score saturación,
• score accesibilidad,
• riesgo operacional,
• disponibilidad probable,
• confianza contextual.

Importante
El sistema NO devuelve:
certezas absolutas.
Devuelve:
estimaciones contextuales probabilísticas.

10. Lifecycle Operacional del Dato
El flujo conceptual del sistema es:
Señales →
procesamiento contextual →
actualización de estados →
motor probabilístico →
generación de inferencias →
recommendation engine →
respuesta usuario →
persistencia histórica →
aprendizaje futuro

11. Principio Central del Dominio
El dominio NO existe para almacenar entidades aisladas.
Existe para:
• interpretar comportamiento territorial,
• modelar contexto dinámico,
• procesar señales,
• generar decisiones rápidas,
• reducir incertidumbre operacional en tiempo real.

