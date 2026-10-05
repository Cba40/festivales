import { useEffect } from 'react';
import { AlertTriangle, CheckCircle, Clock, RefreshCw, ShieldBan } from 'lucide-react';
import {
  useTerritorialPrediction,
  useAutoRefresh,
  type ZoneStateItem,
} from '../../../hooks/useContextEngine';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || '';

/**
 * [TEMPORAL - PRE-DEMO] Interruptor de la métrica de intensidad territorial.
 *
 * Motivo: el cálculo actual (promedio de `saturation_level`) mostraba 100% en
 * fases de baja intensidad (ej. 0.5). Causa probable: el valor de
 * `estimated_vehicles` en `event_days` es demasiado alto en relación a la
 * `capacity` de las zonas, saturando el modelo matemático
 * (min(ocupados, capacity) / capacity).
 *
 * Pendiente: revisar y corregir la fórmula o ajustar los datos de prueba
 * post-demo. Para reactivarla, poner `true` acá: el bloque de JSX se conserva
 * intacto abajo, solo deja de renderizarse.
 *
 * Se usa una constante con nombre y no un `false && (...)` literal en el JSX
 * porque ESLint marca eso con `no-constant-binary-expression`, y porque un
 * minificador puede eliminar por completo una rama `false &&` junto con el
 * código que se quiere conservar para reactivarla.
 */
const SHOW_TERRITORIAL_INTENSITY = false;

/**
 * Intensidad territorial en porcentaje, o `null` si no hay dato.
 *
 * Antes contaba zonas en dos cubos sobre `operational_state` (100 para
 * CLOSED/HIGH_DEMAND, 50 para REGULATED/MODERATE, 0 para el resto) y promediaba.
 * Ese numero era congelado: `operational_state` sale de
 * `projected_density / capacity`, y `projected_density = capacity ×
 * density_factor` con el MISMO `density_factor` en todas las fases, asi que
 * cambiar la fase no lo movia. Medido: 39/39 zonas en MODERATE en la fase de
 * intensidad 0.1 y en la de 1.0.
 *
 * Ahora promedia `saturation_level`, que es la salida del modelo especializado
 * y SI responde a `EventDayPhase.intensity`.
 *
 * Devuelve `null`, no 0, cuando ninguna zona trae el dato. Cero significa
 * "territorio vacio" y "sin dato" significa "el modelo no corrio": confundirlos
 * es exactamente lo que `DESIGN_SYSTEM.md` veta ("no mostrar 0% si el dato es
 * null"). El componente ya distingue los dos casos y muestra "Sin datos".
 */
function computeIntensityPct(zones: ZoneStateItem[]): number | null {
  const validZones = zones.filter((z) => z.saturation_level != null);
  if (validZones.length === 0) return null;
  const avg =
    validZones.reduce((sum, z) => sum + (z.saturation_level as number), 0) /
    validZones.length;
  return Math.round(avg * 100);
}

interface EventStatusBarProps {
  autoRefreshMs?: number;
}

export function EventStatusBar({ autoRefreshMs = 30000 }: EventStatusBarProps) {
  const { data, loading, error, refresh } = useTerritorialPrediction(EVENT_ID);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useAutoRefresh(refresh, autoRefreshMs, !!EVENT_ID);

  if (loading && !data) {
    return (
      <div className="px-4 py-3 bg-slate-100 border-b border-slate-200 flex items-center gap-3">
        <div className="w-4 h-4 rounded-full bg-slate-300 animate-pulse" />
        <div className="flex-1">
          <div className="h-4 bg-slate-200 rounded w-36 animate-pulse mb-1" />
          <div className="h-3 bg-slate-200 rounded w-24 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-3 bg-red-50 border-b border-red-200 flex items-center gap-3">
        <AlertTriangle size={18} className="text-red-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-red-700">Información del evento no disponible</p>
          <p className="text-xs text-red-500 truncate">{error}</p>
        </div>
        <button
          onClick={() => refresh()}
          className="shrink-0 p-1.5 rounded-lg hover:bg-red-100 transition-colors"
          aria-label="Reintentar"
        >
          <RefreshCw size={16} className="text-red-500" />
        </button>
      </div>
    );
  }

  if (!data || data.zone_states.length === 0) {
    return (
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-3">
        <Clock size={18} className="text-slate-400 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-600">Evento no iniciado</p>
          <p className="text-xs text-slate-400">Las predicciones estarán disponibles cuando comience la jornada</p>
        </div>
      </div>
    );
  }

  const zones = data.zone_states;
  const intensityPct = computeIntensityPct(zones);
  // Cuantas zonas hay con saturacion medida. El promedio sale de esas, no de
  // todas: hoy los estacionamientos (parking_v1) y los banos (bathroom_v1)
  // tienen modelo, y el resto de tipos todavia no. El numero es "intensidad de
  // las zonas modeladas", no del territorio entero. Decirlo en el title evita
  // que se lea como cobertura total.
  const zonasMedidas = zones.filter((z) => z.saturation_level != null).length;
  const restrictedZones = zones.filter((z) => z.active_restriction !== 'OPEN').length;
  const barColor = intensityPct === null ? 'bg-slate-300' : intensityPct > 75 ? 'bg-red-500' : intensityPct > 50 ? 'bg-amber-500' : 'bg-emerald-500';
  const dotColor = intensityPct === null ? 'bg-slate-300' : intensityPct > 75 ? 'bg-red-500' : intensityPct > 50 ? 'bg-amber-500' : 'bg-emerald-500';

  return (
    <div className="px-4 py-3 border-b flex items-center gap-3 bg-white border-l-4 border-l-emerald-500">
      <div className={`w-3 h-3 rounded-full shrink-0 ${dotColor}`} role="img" aria-label={`Intensidad territorial: ${intensityPct !== null ? `${intensityPct}%` : 'sin datos'}`} />
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <p className="text-sm font-bold text-slate-800">Territorio activo</p>
          <span className="text-[11px] font-semibold text-slate-400">{zones.length} zona{zones.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          {SHOW_TERRITORIAL_INTENSITY && (
          <div className="flex items-center gap-1.5">
            <div className={`h-1.5 w-16 rounded-full bg-slate-200 overflow-hidden`}>
              <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${intensityPct ?? 0}%` }} />
            </div>
            <span>{intensityPct !== null ? `${intensityPct}% intensidad territorial` : 'Sin datos'}</span>
            {intensityPct === null ? (
              <span
                className="text-[10px] text-slate-400"
                title="Ninguna zona trae saturación: el modelo especializado no corrió para ninguna de ellas."
              >
                Intensidad territorial proyectada
              </span>
            ) : (
              zonasMedidas < zones.length && (
                <span
                  className="text-[10px] text-slate-400"
                  title={`Promedio de saturación de las ${zonasMedidas} zonas con modelo especializado, sobre ${zones.length} en total. Las zonas sin modelo quedan fuera del promedio.`}
                >
                  {zonasMedidas}/{zones.length} zonas
                </span>
              )
            )}
          </div>
          )}
          {restrictedZones > 0 && (
            <span className="flex items-center gap-1">
              <ShieldBan size={12} className="text-amber-500" />
              {restrictedZones} restringida{restrictedZones !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <p className="text-[11px] text-slate-400">
          {data.timestamp ? `Actualizado ${new Date(data.timestamp).toLocaleTimeString()}` : ''}
        </p>
      </div>
      <div className="shrink-0">
        <CheckCircle size={16} className="text-emerald-500" aria-label="Activo" />
      </div>
    </div>
  );
}
