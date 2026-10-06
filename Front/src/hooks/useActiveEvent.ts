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
 *
 * `isLoading` no es decorativo: `App.tsx` lo usa como gate de arranque para que
 * ninguna pantalla se monte sin `event_id`.
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
 * Por qué `activeEventId` viene del store como `string | null`.
 * ----------------------------------------------------------------------
 * El hook devuelve `activeEventId` tal como está en el store (`string | null`).
 * Los componentes deben usar narrowing (`if (!eventId) return null`) o el gate
 * de `App.tsx` para bloquear el render hasta que el evento se resuelva.
 * Antes, una función auxiliar hacía `?? ''` para evitar el literal "null", lo que
 * provocaba URLs como `/events//alerts` cuando el ID era realmente `null` — el
 * compilador se apagaba justo donde importaba y el backend ni siquiera recibía
 * la request por la falta de headers CORS en la redirección 308.
 *
 * Ahora la estrategia es explícita: o esperan a que resuelva (`isLoading`),
 * o bloquean el render desde la raíz (`App.tsx`). No hay coerción oculta.
 */