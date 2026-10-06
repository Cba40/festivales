/**
 * `event_id` del evento activo.
 *
 * Reexporta el resolver del store global para que los componentes que hoy
 * importan `EVENT_ID` desde este archivo ($\`context-engine\`) no tengan que
 * cambiar su import.
 *
 * OJO — es una **constante**, no una lectura del store:
 *
 * - Sirve para ser importada y pasada por props, no para hacer requests.
 * - Para pedir datos usá \`getActiveEventId()\` / \`requireActiveEventId()\`
 *   (\`services/activeEvent\`) o el hook \`useResolvedEventId()\`, que leen el
 *   store en el momento de la llamada.
 *
 * Antes este archivo exportaba \`import.meta.env.VITE_EVENT_ID || 'default-event-id'\`,
 * horneada en el bundle al compilar. Queda en \`''\`: un ID inventado produce un 404
 * opaco ("No se encontraron zonas para el evento") en vez de un estado vacío
 * distinguible.
 */
export const EVENT_ID = ''