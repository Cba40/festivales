import { apiClient } from '@/core/api/client'
import { useAppStore } from '@/core/state/store'

/**
 * Resolución del evento activo desde la jornada que configuró el operador.
 *
 * Este módulo es la única fuente de `event_id` para las peticiones de datos. Reemplaza
 * a `import.meta.env.VITE_EVENT_ID`, que Vite hornea en el bundle al compilar: con
 * esa variable, cambiar de evento exigía redeploy y un valor obsoleto en `.env`
 * hacía que la app pidiera zonas de un evento inexistente sin avisar
 * ("No se encontraron zonas para el evento").
 *
 * El endpoint `GET /api/events/active` lee `event_days` y devuelve el `event_id` de
 * la jornada activa. Sin jornada configurada responde 404 y acá queda
 * `activeEventId === null`: es una condición operativa ("configurá una jornada"),
 * no un error que haya que tapar con un ID inventado.
 *
 * Por qué NO se exporta una constante tipo `const EVENT_ID = ...`
 * ----------------------------------------------------------------
 * Sería el patrón viejo y no puede funcionar: el store se resuelve en runtime,
 * después de que el módulo ya se evaluó. Una constante leída al importar el
 * archivo quedaría congelada en `null` para siempre. La resolución tiene que
 * ser una llamada en el momento de usar el ID.
 */

/** Lo que devuelve `GET /api/events/active`. */
interface ActiveEventResponse {
  event_id: string
  event_day_id: string
  event_name: string | null
  date: string
}

/**
 * `event_id` activo, o `null` si todavía no resolvió o no hay jornada configurada.
 *
 * Pensado para los servicios, que son funciones y hooks: leen el valor en el
 * momento de construir la request. Para componentes, usá `useActiveEvent()`, que
 * además re-renderiza cuando resuelve.
 */
export function getActiveEventId(): string | null {
  return useAppStore.getState().activeEventId
}

/**
 * Lanza si no hay evento activo.
 *
 * Para los puntos del flujo donde sin `event_id` la request no tiene sentido
 * (predicciones, ranking de productos, reportes). Prefiere un error explícito en
 * el service a que la UI muestre "0 zonas" sin explicación: el mensaje de acá
 * dice qué hacer, el 404 de `predictions` sólo "no se encontraron zonas".
 */
export function requireActiveEventId(): string {
  const id = getActiveEventId()
  if (id) return id
  const { isLoadingActiveEvent } = useAppStore.getState()
  throw new Error(
    isLoadingActiveEvent
      ? 'El evento activo todavía se está resolviendo'
      : 'No hay evento activo configurado. Marcá una jornada como activa desde el dashboard.',
  )
}

/**
 * Resuelve el evento activo y lo guarda en el store.
 *
 * Idempotente: volver a llamarla no rompe nada, refresca el valor. Eso permite
 * re-resolver cuando el operador marca una jornada nueva sin recargar la página,
 * que es el caso que justifica que el ID viva en el store y no en el bundle.
 *
 * Devuelve el `event_id` resuelto, o `null` si no hay jornada activa.
 */
export async function resolveActiveEvent(): Promise<string | null> {
  try {
    const { data } = await apiClient.get<ActiveEventResponse>(
      '/events/active',
      { headers: { 'X-Request-Origin': 'prefetch' } },
    )
    useAppStore.getState().setActiveEvent(
      data.event_id,
      data.event_day_id ?? null,
      data.event_name ?? null,
    )
    return data.event_id
  } catch (err) {
    const status: unknown =
      err &&
      typeof err === 'object' &&
      'response' in err &&
      (err as { response?: { status?: unknown } }).response?.status

    // 404 es el caso esperado sin jornada configurada y no merece seguir el
    // interceptor de refresh de `apiClient`, que interpretaría cualquier 404 como
    // una sesión vencida. Se marca el estado para que la UI pueda explicarlo.
    if (status === 404) {
      useAppStore.getState().setActiveEventMissing(true)
      return null
    }

    // Cualquier otro fallo (red caída, 500) también deja la app sin evento, pero
    // sin marcarlo como "no configurado": no es lo mismo que no tener jornada.
    useAppStore.getState().setActiveEventMissing(false)
    useAppStore.setState({ isLoadingActiveEvent: false })
    throw err
  }
}