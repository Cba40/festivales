import { useCallback, useEffect } from 'react'
import { resolveActiveEvent } from '@/services/activeEvent'
import { useAppStore } from '@/core/state/store'

/**
 * Resuelve el `event_id` activo y lo deja en el store.
 *
 * Se monta una vez, arriba de todo (`App.tsx`), antes que cualquier pantalla que
 * pida datos: sin `activeEventId` los services no tienen contra qué consultar.
 *
 * Devuelve el estado para que quien lo monte pueda bloquear el render mientras
 * resuelve. Esperar es correcto acá — una request sin `event_id` devuelve 404 y se
 * perdería en un estado de error que después no se distingue de "no hay evento".
 */
export function useActiveEvent() {
  const activeEventId = useAppStore((s) => s.activeEventId);
  const eventDayId = useAppStore((s) => s.eventDayId);
  const activeEventName = useAppStore((s) => s.activeEventName);
  const isLoading = useAppStore((s) => s.isLoadingActiveEvent);
  const isMissing = useAppStore((s) => s.activeEventMissing);

  const resolve = useCallback(() => resolveActiveEvent().catch(() => null), []);

  useEffect(() => {
    void resolve();
  }, [resolve]);

  return {
    activeEventId,
    eventDayId,
    activeEventName,
    /** true mientras se consulta `/events/active`. */
    isLoading,
    /** true si resolvió y no hay jornada activa configurada. */
    isMissing,
    /** Re-resuelve. Para cuando el operador marca una jornada sin recargar. */
    resolve,
  }
}

/**
 * `event_id` activo para componentes, como string.
 *
 * Devuelve `''` mientras resuelve o si no hay jornada configurada, para que los
 * templates de URL (`/events/${id}/zones`) no queden con el literal "null".
 * Los hooks y services que necesitan distinguir "aún no sé" de "no hay" usan
 * `useActiveEvent()` o `getActiveEventId()`, que sí devuelven `null`.
 */
export function useResolvedEventId(): string {
  return useAppStore((s) => s.activeEventId) ?? '';
}