# Learning & Analytics (L&A) — Implementación Fase 3

> Estado del documento: **vigente al cierre de la Etapa 3**.
> Todo el contenido refleja el sistema **tal como está implementado hoy**, incluidas sus limitaciones. No se documenta un estado deseado.

## 1. Resumen Ejecutivo

El módulo **Learning & Analytics (L&A)** agrega al Territorrial MVP un mecanismo para **evaluar el desempeño operativo del evento** a partir de cuatro métricas calculadas sobre datos ya existentes en la base (predicciones, observaciones operativas, eventos operativos y zone_behaviors).

- **Qué hace**: ejecuta el motor de métricas (`MetricService`), detecta anomalías contra umbrales simples y genera recomendaciones de configuración cuando corresponde.
- **Para qué sirve**: dar al operador municipal una vista honesta de cuánto se ajustan las predicciones y las configuraciones del motor a lo que realmente ocurrió.
- **Estado actual**: funcional e instrumentado. Las fórmulas v1 y los umbrales son **provisionales** y están marcados explícitamente como tales (`is_provisional: true`) para que la UI no los presente como verdades definitivas. Las métricas que no tienen datos suficientes se reportan como `BLOCKED` o `LIMITED`, nunca se inventan valores.

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vite/React)                    │
│  AnalyticsScreen (tab Analytics del Motor)                      │
│    └─ useMetricsEvaluation(evaluate(eventDayId, phaseId))       │
│         │  POST /api/analytics/evaluate                         │
└─────────┼───────────────────────────────────────────────────────┘
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API (FastAPI, app/api/routes/analytics.py)     │
│  POST /api/analytics/evaluate                                   │
│   1. Valida event_day_id y phase_id (404 si no existen)          │
│   2. MetricService.calculate_all(event_day_id, phase_id)         │
│   3. AnomalyDetector.detect_all(results)                         │
│   4. workflow_service.create_recommendation(anomalía)            │
│   5. EvaluationResponse (métricas + anomalías + recomendaciones) │
└───────┬─────────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────────┐
│  MetricService (src/application/learning/metric_service.py)     │
│  • calculate_density_deviation      ── predictions + observations│
│  • calculate_incident_frequency     ── operational_events        │
│  • calculate_phase_transition_latency ── (siempre BLOCKED)       │
│  • calculate_zone_behavior_adherence ── observations + behaviors │
└───────┬─────────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────────┐
│  Base de datos (lectura)                                         │
│  predictions · operational_observations · operational_events     │
│  zones · zone_types · zone_behaviors                             │
│  + escritura (workflow): configuration_recommendations           │
│    y recommendation_audit_entries                                │
└─────────────────────────────────────────────────────────────────┘
```

Componentes clave:

| Componente | Ubicación | Rol |
|---|---|---|
| `MetricService` | `Back/src/application/learning/metric_service.py` | Calcula las 4 métricas. No se modifica su lógica. |
| `MetricResult` | `Back/src/application/learning/metric_result.py` | Dataclass de resultado (name, display_name, status, value, reason, data_points, limitations, is_provisional). |
| `AnomalyDetector` | `Back/src/application/learning/anomaly_detector.py` | Decide si una métrica `ENABLED` es una anomalía (umbrales v1). |
| `workflow_service` | `Back/src/application/learning/workflow_service.py` | Persiste recomendaciones en `PENDING_REVIEW` + auditoría. |
| Endpoint | `Back/app/api/routes/analytics.py` | `POST /api/analytics/evaluate`. |
| Schemas | `Back/app/schemas/analytics.py` | Contrato tipado de request/response. |
| Hook | `Front/src/hooks/useMetricsEvaluation.ts` | Cliente del endpoint. |
| UI | `Front/src/features/dashboard/screens/AnalyticsScreen.tsx` | `MetricsEvaluationCard` + `MetricCard`. |

## 3. Las 4 Métricas

### 3.1 Desviación de Densidad (`density_deviation`)

- **Fórmula v1**: promedio de `|predicted_density - observed_density| / capacity` solo con coincidencia de zona y dentro de una ventana temporal de **±30 min** entre predicción y observación.
- **Estados posibles**: `ENABLED` (hay pares coincidentes), `BLOCKED` (sin predicciones, sin observaciones, sin coincidencias, o sin capacity y zonas).
- **Limitaciones documentadas**: la ventana ±30 min es un default provisional; el denominador usa `zones.capacity`; no distingue predicciones solapadas para la misma zona y ventana.

### 3.2 Frecuencia de Incidentes (`incident_frequency`)

- **Fórmula v1**: `cantidad de eventos con is_incident=true / horas del rango de timestamps de los eventos`.
- **Estados posibles**: `ENABLED` (hay incidentes y rango de horas válido), `LIMITED` (hay eventos pero 0 incidentes → valor `0.0`), `BLOCKED` (sin eventos o rango temporal nulo).
- **Limitaciones documentadas**: el denominador (horas) se deriva del rango de los propios eventos; no distingue incidentes superpuestos.

### 3.3 Latencia de Transición de Fase (`phase_transition_latency`)

- **Fórmula**: no existe fuente de observación. **Siempre `BLOCKED`** hasta que se defina cómo observar la transición efectiva de fases (RFC-006 no la define).
- Esta métrica jamás genera anomalías.

### 3.4 Adherencia a ZoneBehavior (`zone_behavior_adherence`)

- **Fórmula v1**: promedio de `1 - |observed_density - capacity × density_factor| / capacity` para observaciones con `zone_behaviors` coincidentes de la fase.
- **Estados posibles**: `ENABLED`, `BLOCKED` (sin behaviors, sin observaciones, o sin observaciones aplicables).
- **Limitaciones documentadas**: fórmula v1 provisional; **no incluye `accumulated_impact`** (en Stage 3 se proyecta `capacity × density_factor + accumulated_impact`); la resolución `zone_id → zone_type_id` usa `zones.type` como slug con fallback de subtipo.

### Estados posibles comunes

| Estado | Significado |
|---|---|
| `ENABLED` | Datos suficientes y fórmula pública ejecutada. |
| `LIMITED` | Parcialmente utilizable (ej. cero incidentes: frecuencia 0). |
| `BLOCKED` | No se puede calcular de forma honesta; `value` es `null`. |

Todas las métricas reportan `is_provisional: true` en esta fase.

## 4. Endpoint POST /api/analytics/evaluate

### Contrato

- **Ruta**: `POST /api/analytics/evaluate`
- **Autenticación**: requerida (`Authorization: Bearer <token>`, `verify_token`). Sin token → `401`.
- **Body** (`EvaluationRequest`):

```json
{
  "event_day_id": "<id de event_day>",
  "phase_id": "<uuid de operational_phase>"
}
```

- **Respuesta** (`EvaluationResponse`):

```json
{
  "metrics": [
    {
      "name": "density_deviation",
      "display_name": "Desviación de Densidad",
      "status": "ENABLED",
      "value": 0.18,
      "reason": "Promedio de ...",
      "data_points": 12,
      "limitations": ["..."],
      "is_provisional": true
    }
  ],
  "anomalies_detected": 1,
  "anomalies": [
    {
      "metric_name": "density_deviation",
      "severity": "high",
      "description": "...",
      "suggested_action": "...",
      "value": 0.45,
      "is_provisional": true
    }
  ],
  "recommendations_created": [
    { "id": "...", "status": "pending_review", "metric_name": "density_deviation" }
  ]
}
```

### Tipado estricto

- `status`: `Literal["ENABLED", "LIMITED", "BLOCKED"]`
- `severity`: `Literal["high", "medium", "low"]`
- `is_provisional`: `bool` (default `true`)

### Errores

| Código | Caso |
|---|---|
| `401` | Token ausente/inválido. |
| `404` | `event_day_id` o `phase_id` no existen (o UUID inválido). |
| `500` | Error interno al ejecutar `MetricService`. |

### Flux de anomalías → recomendaciones

1. `AnomalyDetector` evalúa **solo métricas `ENABLED` con valor**.
2. Umbrales v1 (documentados en `anomaly_detector.py`):
   - `density_deviation` > **0.2** → severidad `high`.
   - `zone_behavior_adherence` < **0.5** → severidad `high`.
   - `incident_frequency` > **1.0** (incidentes/hora) → severidad `high`.
3. Cada anomalía genera una `ConfigurationRecommendation` (`PARAMETER_ADJUSTMENT`, confianza 0.9, estado `pending_review`) vía `workflow_service.create_recommendation`.
4. Si la creación falla para una anomalía, se loguea y **continúa con las demás**: el flujo no se rompe.

## 5. UI del Tablero

- **Dónde**: Dashboard → **Motor** → tab **Analytics** → sección **"Evaluación de Métricas"**.
- **Uso**:
  1. Seleccionar **Jornada** (event_day) y **Fase operativa**.
  2. Pulsar **"Evaluar Métricas"**.
  3. Se muestran las 4 tarjetas de métricas (estado, provisionalidad, valor, razón, limitaciones), un panel de anomalías si existen y un aviso con la cantidad de recomendaciones creadas.
- La sección de recomendaciones de configuración y el registro de auditoría siguen mostrándose debajo.
- **El frontend nunca crea recomendaciones**: solo muestra las que genera el backend.

## 6. Estados de las Métricas

- **ENABLED** (verde/emerald): hay datos y la fórmula corrió.
- **LIMITED** (amarillo/amber): la métrica es parcialmente informativa (ej. frecuencia 0 por falta de incidentes).
- **BLOCKED** (gris/slate): no hay datos suficientes; `value = null`; la UI muestra "N/A".
- **Provisionalidad** (bandera ámbar "Fórmula provisional"): es **independiente** del estado. Una métrica `ENABLED` puede y debe seguir marcándose como provisional mientras los umbrales/formulas sean v1.

## 7. Limitaciones Conocidas

1. **Todas las fórmulas son v1 y provisionales** (`is_provisional: true`).
2. **Umbrales de anomalías** (0.2 / 0.5 / 1.0) son marcadores de posición, no valores calibrados.
3. **`accumulated_impact` no está incluido** en la adherencia (Stage 3 proyecta `capacity × density_factor + accumulated_impact`).
4. **Latencia de transición de fase**: sin fuente de observación, siempre `BLOCKED`.
5. **Ventana de coincidencia temporal (±30 min)**: default provisional.
6. **Datos de Neon al momento de implementar Etapa 1**: ~110 predicciones, 2 observaciones, 2 operational_events, 110 zone_behaviors. Con tan pocas observaciones, las métricas de densidad y adherencia solo pueden ser `ENABLED` con muy pocos `data_points`.
7. La resolución `zone_id → zone_type_id` depende de `zones.type` (slug) con fallback de subtipo; zonas sin mapping quedan fuera.
8. El workflow persiste recomendaciones y auditoría en la BD (escribir en `configuration_recommendations`); esto es intencional y gestionado por `workflow_service`.

## 8. Próximos Pasos

1. **Auditoría del flujo completo de datos**: desde la generación de predicciones (Stage 1-5 del context engine) hasta las observaciones, para entender cómo se producen los datos que alimentan estas métricas antes de defenderlas ante funcionarios.
2. **Calibrar umbrales y fórmulas** contra datos reales (remover la provisionalidad cuando se valide).
3. **Incorporar `accumulated_impact`** en la adherencia a zone_behaviors.
4. **Definir la fuente de observación de transición de fases** para desbloquear `phase_transition_latency`.
5. **Validación cruzada**: comparar los `data_points` disponibles por métrica y decidir umbrales mínimos de datos antes de mostrar `ENABLED`.