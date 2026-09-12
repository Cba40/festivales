# L&A — Guía de Uso para la Demo Municipal

> Guía de presentación del módulo Learning & Analytics frente a funcionarios.
> El objetivo no es impresionar con algoritmos, sino **mostrar un sistema honesto**
> que sabe decir cuándo **no** tiene datos suficientes.

## 1. Preparación

Para que la demo muestre valor real (no valores fabricados), el entorno necesita:

| Dato | Tabla/Endpoint | Por qué importa |
|---|---|---|
| Predicciones de densidad | `predictions` | Alimenta la **Desviación de Densidad**. |
| Observaciones operativas | `operational_observations` | Contraste contra predicciones y contra zone_behaviors. |
| Eventos operativos | `operational_events` | Alimenta la **Frecuencia de Incidentes** (requiere `is_incident=true` para pasar de `LIMITED` a `ENABLED`). |
| Zone behaviors de la fase | `zone_behaviors` (por `operational_phase_id`) | Alimenta la **Adherencia a ZoneBehavior**. |
| Zonas con `capacity` | `zones` | Denominador de desviación de densidad y adherencia. |

**Checklist antes de la demo:**

- [ ] Existe al menos un `event_day` activo en el evento de prueba.
- [ ] Existe al menos una `operational_phase` creada.
- [ ] Hay predicciones y observaciones para el mismo `event_day` (idealmente con timestamps cercanos, dentro de la ventana de ±30 min).
- [ ] El usuario tiene una sesión admin válida (el endpoint exige `Authorization: Bearer ...`).

> **Si faltan datos, la UI lo dirá**: la métrica se mostrará `BLOCKED` con `N/A` y su razón. Eso **es** el comportamiento correcto que queremos mostrar.

## 2. Flujo de Demo (paso a paso)

1. **Ingresar al Dashboard** → sección **Motor** → tab **Analytics**.
2. En **"Evaluación de Métricas"**, seleccionar **Jornada** y **Fase operativa**.
3. Pulsar **"Evaluar Métricas"**.
4. Señalar que la pantalla llama a `POST /api/analytics/evaluate` y que **las recomendaciones las genera el backend**, no la interfaz.
5. Recorrer las **4 tarjetas**:
   - **Desviación de Densidad**: cuánto se apartó lo observado de lo proyectado.
   - **Frecuencia de Incidentes**: incidentes por hora (o "0" / bloqueada).
   - **Latencia de Transición de Fase**: explicar que no existe fuente de observación → `BLOCKED`.
   - **Adherencia a ZoneBehavior**: qué tan bien describieron los `density_factor` de la fase lo observado.
6. Si hay anomalías, mostrar el **panel de anomalías** (severidad, descripción y acción sugerida) y abrir la **lista de recomendaciones** debajo, donde la recomendación quedó en estado **Pendiente** (esperando revisión humana).

## 3. Explicación de Estados (para funcionarios)

| Estado | Qué decirle al funcionario |
|---|---|
| **ENABLED** | "El sistema tiene datos y pudo calcular la métrica." |
| **LIMITED** | "El sistema tiene datos parciales; por ejemplo, todavía no hubo incidentes, así que la frecuencia es cero." |
| **BLOCKED** | "El sistema no tiene datos suficientes y **prefiere no inventar un número**. Eso es intencional." |
| **Fórmula provisional** | "Estos cálculos y umbrales aún se están validando; son una primera versión, no la palabra final." |

**Mensaje sobre provisionalidad** (decirlo siempre, incluso si todas las métricas salen `ENABLED`):

> "Coloreamos el estado de la métrica (verde/amarillo/gris) y, por separado, marcamos con una etiqueta ámbar que la fórmula es provisional. Una métrica puede estar 'encendida' (ENABLED) y al mismo tiempo ser provisional: significa que se calculó, pero que el sistema todavía no la considera definitiva."

## 4. Narrativa Institucional

**Frase clave**:

> "Este módulo no maquilla datos. Cuando no hay información suficiente, lo dice. Cuando la hay, la muestra con sus limitaciones y con umbrales marcados como provisionales. Así, cada número que veamos hoy se puede auditar y calibrar antes de usarlo en decisiones."

**Refuerzos recomendados**:

- **Honestidad antes que brillo**: mostrar una métrica `BLOCKED` con su razón es una fortaleza, no una falla.
- **El motor no decide solo**: las anomalías generan recomendaciones en estado *Pendiente de revisión*; un operador las aprueba o rechaza (registro de auditoría). La decisión humana sigue siendo el centro.
- **Rastro de auditoría**: cada recomendación tiene bitácora (`generated`, `resolved`), para que nunca quede claro-mágico cómo llegó.

## 5. Qué NO decir ni hacer en la demo

- ❌ No inventar umbrales como "la norma del sistema". Son v1 (0.2 / 0.5 / 1.0) y provisionales.
- ❌ No afirmar que el sistema "predice incidentes" — mide la frecuencia de lo que ya ocurrió.
- ❌ No modificar configuraciones en vivo para "hacerla ver mejor" durante la demo.
- ❌ No ocultar una métrica `BLOCKED`: es la oportunidad de contar la narrativa de honestidad.