# Design System & Estándares de UI - CBA 4.0

## 1. Filosofía de Diseño

- **Consistencia por reutilización**: toda acción primaria, tarjeta, badge, diálogo de confirmación y navegación por secciones del dashboard usa los componentes del Design System (`Front/src/features/dashboard/components/ui/`). No se reimplementa estilo por pantalla.
- **Manejo honesto de datos**: cuando el motor no emite un dato, la UI muestra "Sin datos", "—" o un label de incertidumbre. Nunca se muestra un "0%" o valor fabricado que parezca real.
- **Estados siempre cubiertos**: toda vista que consume API maneja explícitamente `loading`, `error` y datos vacíos antes de renderizar contenido.

## 2. Paleta de Colores y Tipografía

- **Acento/Acción**: `indigo-600` (primary, tab activo, badge de info). `purple-600` solo para variante `dashboard` de Button.
- **Neutros**: `slate-50` a `slate-900` (fondos, textos, bordes). Fondo de superficie: `bg-white`; borde estándar: `border-slate-200`.
- **Estados funcionales**: `emerald-500/50` (éxito/bajo), `amber-500/50` (advertencia/medio), `red-600` (error/alto/destructivo).
- **Tipografía**: fuente por defecto de Tailwind. Tamaños típicos: labels `text-[10px]`/`text-xs` bold, títulos `text-sm`/`text-lg` semibold/bold, cuerpo `text-sm`.

Los colores se aplican **solo a través de las variantes** de los componentes (ver §3). No se hardcodean clases de color sueltas en pantallas nuevas.

## 3. Catálogo de Componentes

### Button
`Button.tsx` — Acción disparable con mouse/teclado.

- **Uso**: `primary` para guardar/crear/acciones principales; `secondary` para cancelar y recargas; `destructive` para acciones irreversibles; `ghost` para acciones contextuales de bajo peso; `dashboard` (púrpura) para acciones específicas del panel de dashboard.
- **Variantes**: `primary` | `secondary` | `destructive` | `ghost` | `dashboard`.
- **Tamaños**: `sm` (14px... `py-1.5 px-3 text-xs`), `md` (default, `py-2 px-4 text-sm`), `lg` (`py-2.5 px-5 text-base`).
- **Comportamiento por defecto**: `type="button"`, `disabled:opacity-50 disabled:cursor-not-allowed`, layout `inline-flex items-center justify-center gap-2`.

```tsx
<Button variant="secondary" size="sm" onClick={handleAction}>Cancelar</Button>
<Button variant="primary" size="lg">Guardar</Button>
<Button variant="destructive" onClick={deleteItem}>Eliminar</Button>
```

### Card
`Card.tsx` — Contenedor de superficie con borde y sombra.

- **Uso**: envolver formularios, métricas y bloques de contenido. `standard` para contenido estático; `action` (card clickeable) para navegación/selección; `metric` y `state` para indicadores.
- **Estructura**: `bg-white border border-slate-200 rounded-xl shadow-sm` + `p-5`.
- **Click**: si se pasa `onClick`, se renderiza como `<button type="button">` (accesible y consistente); si no, como `<div>`.

```tsx
<Card variant="standard">
  <FormularioDeCreacion />
</Card>

<Card variant="action" onClick={() => navigate('/detalle')}>
  <p>Ver detalle</p>
</Card>
```

### Badge
`Badge.tsx` — Etiqueta de estado compacta.

- **Uso**: señalar estado de un registro (éxito, advertencia, error, info, neutro). Alto contraste figura/fondo con borde sutil.
- **Variantes**:
  - `success`: `bg-emerald-50 text-emerald-700 border-emerald-200`
  - `warning`: `bg-amber-50 text-amber-700 border-amber-200`
  - `error`: `bg-red-50 text-red-700 border-red-200`
  - `info`: `bg-indigo-50 text-indigo-700 border-indigo-200`
  - `neutral`: `bg-slate-100 text-slate-600 border-slate-200`

```tsx
<Badge variant="success">Activo</Badge>
<Badge variant="warning">Saturación media</Badge>
```

### ConfirmDialog
`ConfirmDialog.tsx` — Diálogo de confirmación accesible que reemplaza `window.confirm`.

- **Props**: `open`, `title`, `message`, `confirmLabel` ("Confirmar"), `cancelLabel` ("Cancelar"), `variant` (`destructive` | `primary`, default `destructive`), `onConfirm`, `onCancel`.
- **Comportamiento**: cierra con `Escape`; autofocus en el botón de confirmar; `role="dialog"` + `aria-modal` + `aria-labelledby`; overlay `z-50 bg-black/40`. Botón cancelar = `Button secondary`, confirmar = `Button` `variant`.

```tsx
<ConfirmDialog
  open={confirming}
  title="Eliminar zona"
  message="Esta acción no se puede deshacer."
  variant="destructive"
  onConfirm={handleDelete}
  onCancel={() => setConfirming(false)}
/>
```

### RefreshButton
`RefreshButton.tsx` — Acción de recarga con feedback de spinner.

- **Props**: `onClick`, `loading` (default `false`), `size` (`sm` | `md`, default `sm`).
- **Uso**: cualquier lista/detalle que recargue datos del backend. Usa `Button variant="secondary"`.
- **Comportamiento**: `RefreshCw` con `animate-spin` mientras `loading`; `disabled` durante la carga; texto alterna "Actualizando..." / "Actualizar".

```tsx
<RefreshButton onClick={fetchData} loading={isLoading} />
```

### SectionTabs
`SectionTabs.tsx` — Navegación por secciones (tabs).

- **Props** (genérico `T extends string`): `sections: { key: T; label: string }[]`, `activeSection: T`, `onChange: (section: T) => void`, `className` (default `flex gap-2 mb-6`).
- **Regla estricta de estilo**: activo = `bg-indigo-600 text-white`; inactivo = `bg-white text-slate-600 border border-slate-200 hover:bg-slate-50`. No alterar estos colores por pantalla.

```tsx
<SectionTabs
  sections={[{ key: 'a', label: 'Resumen' }, { key: 'b', label: 'Detalle' }]}
  activeSection="a"
  onChange={setSection}
/>
```

### truncateId
`utils/format.ts` — Acortar IDs largos para UI.

- **Firma**: `truncateId(id: string, maxLength = 8): string` → retorna `id` si entra en `maxLength`, o `id.slice(0, maxLength) + '...'`.
- **Uso**: mostrar IDs (UUIDs) en tablas o badges sin romper el layout.

```tsx
<span>{truncateId(zona.zone_id)}</span>
```

### Componentes de L&A (feature-specific)

Definidos en `AnalyticsScreen.tsx` (tab Analytics del Motor). No están en el barrel `ui/` porque son específicos del feature, pero reutilizan `Card`/`Button` del DS y siguen las mismas reglas de color semántico.

#### MetricCard
Tarjeta individual de métrica que separa explícitamente **estado** de **provisionalidad**:

- **Badge de estado** con colores semánticos exactos (hardcodeados a propósito por contrato UI del endpoint):
  - `ENABLED` → `bg-emerald-100 text-emerald-800`
  - `LIMITED` → `bg-amber-100 text-amber-800`
  - `BLOCKED` → `bg-slate-100 text-slate-800`
- **Badge de provisionalidad** (independiente del estado): solo si `is_provisional === true` → `bg-amber-50 text-amber-700 border-amber-200` con ícono `AlertTriangle` y texto "Fórmula provisional". Una métrica `ENABLED` puede (y debe) seguir siendo provisional.
- **Valor**: formateado con `toFixed(2)`, o `"N/A"` si `value === null`.
- **Detalles**: `reason` como texto secundario y `<details>` colapsable con "Limitaciones (n)".

#### MetricsEvaluationCard
Contenedor de la sección "Evaluación de Métricas":

- Selectores de **Jornada** (`event_days.list`) y **Fase operativa** (`operational_phases.list`).
- Botón primario **"Evaluar Métricas"** que consume `POST /api/analytics/evaluate` vía `useMetricsEvaluation`. No dispara evaluación automática.
- Renderiza una grilla de `MetricCard`, un **panel de anomalías** (severidad tipada `high|medium|low`, con badge rojo y provisionalidad) y un aviso de recomendaciones creadas. **Nunca crea recomendaciones desde el frontend**.

```tsx
// Estados y colores (contrato con Back/app/schemas/analytics.py)
const METRIC_STATUS_CLASSES: Record<MetricStatus, string> = {
  ENABLED: 'bg-emerald-100 text-emerald-800',
  LIMITED: 'bg-amber-100 text-amber-800',
  BLOCKED: 'bg-slate-100 text-slate-800',
};
```

Reglas de color: emerald = datos disponibles; amber = parcial/provisional; slate = sin datos; red = anomalía. No usar estos colores para otros significados.

### Exportación
Todos se exportan desde el barrel `ui/index.ts`:

```ts
export { Button } from './Button';
export { Card } from './Card';
export { Badge } from './Badge';
export { ConfirmDialog } from './ConfirmDialog';
export { RefreshButton } from './RefreshButton';
export { SectionTabs } from './SectionTabs';
```

## 4. Reglas de Oro y Anti-patrones

- ✅ **HACER**: Usar `<Button>` / `<Card>` / `<Badge>` / `<ConfirmDialog>` / `<SectionTabs>` / `<RefreshButton>` para esos patrones.
- ❌ **NO HACER**: Usar `<button className="...">` nativo para acciones primarias o tabs cuando existe el componente del DS.
- ❌ **NO HACER**: Usar `window.confirm` para confirmaciones destructivas; usar `<ConfirmDialog>`.
- ✅ **HACER**: Usar `truncateId` para mostrar IDs en UI.
- ❌ **NO HACER**: Hardcodear colores de acento/estado; usar las variantes del DS (indigo = acción, emerald/amber/red = estado, slate = neutro).
- ✅ **HACER**: Envolver formularios de creación en `<Card variant="standard">`.
- ❌ **NO HACER**: Mostrar "0%" o "0" si el dato es `null`/ausente; mostrar "Sin datos" (como `EventStatusBar.tsx` con `intensityPct === null`) o "—" (como `getEstadoLabel` en `ZonaCardsList.tsx`).
- ✅ **HACER**: Mostrar incertidumbre explícita cuando falta confiabilidad (ej: "❗ Disponibilidad incierta" en `getConfianzaLabel`).
- ✅ **HACER**: Manejar `loading` y `error` en toda vista pública que consume API antes de renderizar el contenido (patrón de guards en `ServiciosGenerales.tsx`).
- ❌ **NO HACER**: Eliminar campos de tipos compartidos (`Zone`, etc.) sin verificar los consumidores — un "limpiado" de tipos que rompa lectores existentes es una regresión (ver auditoría de `distancia_min`/`referencia`).
- ✅ **HACER**: Cambios de UI/DS validados con `npm run typecheck` (sin errores nuevos) antes de cerrar la tarea.
- ✅ **HACER**: En métricas del motor, separar visualmente **estado** (`ENABLED`/`LIMITED`/`BLOCKED`) de **provisionalidad** (`is_provisional`), y mostrar `"N/A"` cuando `value` es `null` (ver `MetricCard` en `AnalyticsScreen.tsx`).
- ❌ **NO HACER**: Mostrar un número visible cuando `value` sea `null` (ej. "0" o "0.00"): la UI debe renderizar "N/A".
- ❌ **NO HACER**: Crear recomendaciones desde el frontend; el frontend solo consume `POST /api/analytics/evaluate` y muestra lo que el backend generó.