import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { X, UtensilsCrossed, MapPin, Clock } from 'lucide-react'
import {
  useGastronomyRecommendations,
  type ZonaGastronomicaItem,
} from '@/services/gastronomyProduct'
import { formatUpdatedAt } from '@/utils/formatTime'

interface CorredorGastronomico {
  id: string
  nombre: string
  saturacion: 'baja' | 'media' | 'alta' | 'desconocida'
  categoriaLabel: string
  posibilidadSentarse: 'alta' | 'media' | 'baja'
  distancia: number | null
  x: number
  y: number
  referencia: string
  updatedAt: number
}

const toSaturacion = (level: number | null): CorredorGastronomico['saturacion'] => {
  if (level === null) return 'desconocida'
  if (level < 0.6) return 'baja'
  if (level < 0.8) return 'media'
  return 'alta'
}

const toSentarse = (level: number | null): 'alta' | 'media' | 'baja' => {
  if (level === null || level < 0.5) return 'alta'
  if (level < 0.8) return 'media'
  return 'baja'
}

const getCategoriaLabel = (categoria: string): string => {
  switch (categoria) {
    case 'foodtruck': return 'Food Truck'
    case 'comida_al_paso': return 'Comida al paso'
    case 'penas': return 'Peñas'
    case 'patio_de_comidas': return 'Patio de comidas'
    case 'restaurante': return 'Restaurante'
    default: return categoria || 'Gastronomía'
  }
}

const getSentarseLabel = (posibilidad: string): string => {
  switch (posibilidad) {
    case 'alta': return '🟢 Fácil encontrar lugar'
    case 'media': return '🟡 Moderadamente disponible'
    default: return '🔴 Muy concurrido'
  }
}

const normalizeCoords = (
  zonas: ZonaGastronomicaItem[]
): Map<string, { x: number; y: number }> => {
  const withCoords = zonas.filter(z => z.lat != null && z.lng != null)
  const positions = new Map<string, { x: number; y: number }>()

  if (withCoords.length === 0) return positions
  if (withCoords.length === 1) {
    positions.set(withCoords[0].zone_id, { x: 50, y: 50 })
    return positions
  }

  const lats = withCoords.map(z => z.lat as number)
  const lngs = withCoords.map(z => z.lng as number)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)
  const spanLat = maxLat - minLat || 1
  const spanLng = maxLng - minLng || 1

  for (const z of withCoords) {
    const x = ((z.lng as number) - minLng) / spanLng * 80 + 10
    const y = 90 - ((z.lat as number) - minLat) / spanLat * 80
    positions.set(z.zone_id, { x: Math.round(x), y: Math.round(y) })
  }
  return positions
}

const GastronomiaExpanded = () => {
  const navigate = useNavigate()
  const { data, loading, error, refresh } = useGastronomyRecommendations()
  const [selectedCorredor, setSelectedCorredor] = useState<CorredorGastronomico | null>(null)

  useEffect(() => {
    refresh()
  }, [refresh])

  const zonas = data?.zonas ?? []
  const updatedAt = data?.timestamp ? Date.parse(data.timestamp) : Date.now()
  const positionMap = useMemo(() => normalizeCoords(zonas), [zonas])

  const corredores: CorredorGastronomico[] = useMemo(
    () =>
      zonas.map(z => {
        const pos = positionMap.get(z.zone_id)
        return {
          id: z.zone_id,
          nombre: z.name,
          saturacion: toSaturacion(z.saturation_level),
          categoriaLabel: getCategoriaLabel(z.categoria),
          posibilidadSentarse: toSentarse(z.saturation_level),
          distancia: z.distancia_min,
          x: pos?.x ?? 50,
          y: pos?.y ?? 50,
          referencia: z.referencia || '',
          updatedAt,
        }
      }),
    [zonas, positionMap, updatedAt]
  )

  const getSaturacionColor = (saturacion: string) => {
    switch (saturacion) {
      case 'baja': return 'bg-success/20 text-success'
      case 'media': return 'bg-warning/20 text-warning'
      case 'alta': return 'bg-danger/20 text-danger'
      default: return 'bg-gray-500/20 text-gray-500 dark:text-gray-300'
    }
  }

  const getSaturacionLabel = (saturacion: string) => {
    switch (saturacion) {
      case 'baja': return 'Baja saturación'
      case 'media': return 'Media saturación'
      case 'alta': return 'Alta saturación'
      default: return 'Sin datos de saturación'
    }
  }

  if (loading && corredores.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Zonas Gastronómicas" showBack onBack={() => navigate('/servicios/comer')} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando zonas gastronómicas...</p>
        </div>
      </div>
    )
  }

  if (error && corredores.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Zonas Gastronómicas" showBack onBack={() => navigate('/servicios/comer')} />
        <div className="flex-1 p-4 flex flex-col items-center justify-center space-y-4">
          <p className="text-danger font-bold">Error al cargar</p>
          <p className="text-sm text-slate-500 text-center">{error}</p>
          <button
            onClick={refresh}
            className="bg-primary text-white px-6 py-2 rounded-lg font-bold"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Zonas Gastronómicas" showBack onBack={() => navigate('/servicios/comer')} />

      <div className="flex-1 p-4 space-y-4 overflow-y-auto">
        {/* Mapa visual */}
        <div className="w-full bg-white dark:bg-slate-800 rounded-xl border-2 border-slate-200 dark:border-slate-700 aspect-square relative overflow-hidden shadow-md">
          {/* Grid sutil de referencia */}
          <div className="absolute inset-0 opacity-10">
            {[...Array(5)].map((_, i) => (
              <div
                key={`h-${i}`}
                className="absolute border-b border-slate-300 dark:border-slate-600 w-full"
                style={{ top: `${(i + 1) * 20}%` }}
              />
            ))}
            {[...Array(5)].map((_, i) => (
              <div
                key={`v-${i}`}
                className="absolute border-r border-slate-300 dark:border-slate-600 h-full"
                style={{ left: `${(i + 1) * 20}%` }}
              />
            ))}
          </div>

          {/* Puntos en el mapa */}
          {corredores.map(corredor => {
            const getMarkerColor = (sat: string) => {
              switch (sat) {
                case 'baja': return 'bg-success shadow-success/50'
                case 'media': return 'bg-warning shadow-warning/50'
                case 'alta': return 'bg-danger shadow-danger/50'
                default: return 'bg-gray-500 shadow-gray-500/50'
              }
            }

            const getEmoji = (sat: string) => {
              switch (sat) {
                case 'baja': return '🟢'
                case 'media': return '🟡'
                case 'alta': return '🔴'
                default: return '⚪'
              }
            }

            return (
              <button
                key={corredor.id}
                onClick={() => setSelectedCorredor(corredor)}
                className="absolute transform -translate-x-1/2 -translate-y-1/2 group z-10"
                style={{ left: `${corredor.x}%`, top: `${corredor.y}%` }}
                title={corredor.nombre}
              >
                {/* Aura */}
                <div className={`absolute -inset-2 rounded-full ${getMarkerColor(corredor.saturacion)} opacity-30 group-hover:opacity-50 transition-opacity blur-md`} />
                {/* Punto */}
                <div className={`relative w-8 h-8 rounded-full ${getMarkerColor(corredor.saturacion)} shadow-lg group-hover:scale-110 transition-transform flex items-center justify-center text-white font-bold text-sm border-2 border-white dark:border-slate-800`}>
                  {getEmoji(corredor.saturacion)}
                </div>
              </button>
            )
          })}
        </div>

        {/* Leyenda */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-3 shadow-md">
          <p className="text-xs font-bold text-slate-600 dark:text-slate-300 mb-2">Leyenda:</p>
          <div className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
            <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-success" /> Baja saturación — Fácil encontrar lugar</p>
            <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-warning" /> Media saturación — Moderadamente disponible</p>
            <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-danger" /> Alta saturación — Muy concurrido</p>
            <p className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-gray-400" /> Sin datos de saturación — Zona informativa</p>
          </div>
        </div>

        {/* Lista de corredores */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1">
            {corredores.length} zonas disponibles
          </p>
          {corredores.map(corredor => (
            <button
              key={corredor.id}
              onClick={() => setSelectedCorredor(corredor)}
              className="w-full text-left bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary dark:hover:border-primary/50 transition-colors group"
            >
              <div className="flex items-start gap-3">
                <span className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
                  corredor.saturacion === 'baja' ? 'bg-success' :
                  corredor.saturacion === 'media' ? 'bg-warning' :
                  corredor.saturacion === 'alta' ? 'bg-danger' : 'bg-gray-400'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-primary dark:group-hover:text-primary">
                    {corredor.nombre}
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex items-center gap-1">
                    <UtensilsCrossed size={12} /> {corredor.categoriaLabel}
                  </p>
                  {corredor.distancia != null && (
                    <p className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-1">
                      <Clock size={12} /> {corredor.distancia} min
                    </p>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom Sheet */}
      {selectedCorredor && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedCorredor(null)}
          />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div
              className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
              onClick={() => setSelectedCorredor(null)}
            />

            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3">
              {selectedCorredor.nombre}
            </h3>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <UtensilsCrossed size={16} /> <strong>{selectedCorredor.categoriaLabel}</strong>
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <MapPin size={16} /> {selectedCorredor.referencia || 'Sin referencia'}
              </p>
              {selectedCorredor.distancia != null && (
                <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2">
                  <Clock size={16} /> {selectedCorredor.distancia} min caminando
                </p>
              )}
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {getSentarseLabel(selectedCorredor.posibilidadSentarse)}
              </p>
              <div className={`text-sm font-semibold p-2 rounded ${getSaturacionColor(selectedCorredor.saturacion)}`}>
                {getSaturacionLabel(selectedCorredor.saturacion)}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-300 mt-2">
                {formatUpdatedAt(selectedCorredor.updatedAt)}
              </p>
            </div>

            <button
              onClick={() => setSelectedCorredor(null)}
              className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
            >
              <X size={16} />
              Cerrar
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default GastronomiaExpanded