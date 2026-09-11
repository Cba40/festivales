import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '../components/Header'
import { useAppStore } from '@/core/state/store'
import { useTerritorialPrediction } from '@/hooks/useContextEngine'
import type { Zone } from '@/features/dashboard/types'

const SAT_ORDER: Record<string, number> = { bajo: 0, medio: 1, alto: 2, colapsado: 3 }

const bySaturation = (a: Zone, b: Zone) =>
  (SAT_ORDER[a.saturation] ?? 0) - (SAT_ORDER[b.saturation] ?? 0)

const hasCoords = (zona: Zone) =>
  typeof zona.lat === 'number' && typeof zona.lng === 'number'

const ResolverAhora = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const { data: prediction, loading, error, refresh } = useTerritorialPrediction()
  const [selectedZona, setSelectedZona] = useState<Zone | null>(null)

  useEffect(() => {
    refresh()
  }, [refresh])

  const parkingZones = useMemo(
    () => zones.filter(z => z.type === 'estacionamiento').sort(bySaturation),
    [zones]
  )
  const exitZones = useMemo(
    () => zones.filter(z => z.type === 'salida').sort(bySaturation),
    [zones]
  )

  const parkingPrincipal = parkingZones[0]
  const parkingAlternativa = parkingZones[1]
  const exitPrincipal = exitZones[0]
  const exitAlternativa = exitZones[1]

  const recomendarParking =
    !!parkingPrincipal && parkingPrincipal.saturation !== 'colapsado'
  const recomendarSalida =
    !!exitPrincipal && exitPrincipal.saturation !== 'colapsado'

  const zonaPrincipal: Zone | undefined = recomendarParking
    ? parkingPrincipal
    : recomendarSalida
    ? exitPrincipal
    : parkingPrincipal ?? exitPrincipal

  const zonaAlternativa: Zone | undefined = recomendarParking
    ? parkingAlternativa && parkingAlternativa.saturation !== 'colapsado'
      ? parkingAlternativa
      : undefined
    : recomendarSalida
    ? exitAlternativa && exitAlternativa.saturation !== 'colapsado'
      ? exitAlternativa
      : undefined
    : undefined

  const tipoAccion: 'estacionar' | 'salir' | 'fallback' = recomendarParking
    ? 'estacionar'
    : recomendarSalida
    ? 'salir'
    : parkingPrincipal
    ? 'estacionar'
    : 'fallback'

  const mensaje = recomendarParking
    ? 'Buscá estacionamiento ahora'
    : recomendarSalida
    ? 'Prepará salida anticipada'
    : parkingPrincipal && parkingPrincipal.saturation === 'colapsado'
    ? 'Zonas colapsadas → dirigite a la menos saturada'
    : '¿Qué necesitás ahora?'

  const altaDemandaCount =
    prediction?.zone_states.filter(
      z => z.saturation_level != null && z.saturation_level >= 0.8
    ).length ??
    zones.filter(z => z.saturation === 'alto' || z.saturation === 'colapsado').length

  const saturacionContexto = altaDemandaCount >= 3 ? 'alta' : altaDemandaCount >= 1 ? 'media' : 'baja'
  const saturacionColor =
    saturacionContexto === 'alta' ? 'text-warning' : 'text-success'

  const hora = prediction?.timestamp
    ? new Date(prediction.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'

  const handleIniciarRuta = (zona: Zone) => {
    if (hasCoords(zona)) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
  }

  if (loading && !prediction && zones.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Resolver ahora" showBack onBack={() => navigate('/')} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500">Cargando...</p>
        </div>
      </div>
    )
  }

  if (error && zones.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Resolver ahora" showBack onBack={() => navigate('/')} />
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

  if (tipoAccion !== 'fallback' && zonaPrincipal) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Resolver ahora" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {/* 1. CONTEXTO (arriba, pequeño) */}
          <div className="flex justify-between text-xs text-slate-500 dark:text-slate-300">
            <span>
              📍 {altaDemandaCount > 0 ? `${altaDemandaCount} zonas con alta demanda` : 'Todas las zonas disponibles'}
            </span>
            <span>🕒 {hora}</span>
            <span className={saturacionColor}>⚠️ {saturacionContexto}</span>
          </div>

          {/* 2. MENSAJE PRINCIPAL (grande, dominante) */}
          <div className="bg-primary text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">{mensaje}</p>
          </div>

          {/* 3. DETALLE CLAVE — Zona principal */}
          {zonaPrincipal && (
            <button
              onClick={() => setSelectedZona(zonaPrincipal)}
              className="w-full transition-transform active:scale-95"
            >
              <div className="bg-success text-white p-6 rounded-xl text-left shadow-lg">
                <p className="text-lg font-bold">
                  👉 Dirigite ahora a {zonaPrincipal.name}
                </p>
                {zonaPrincipal.referencia && (
                  <p className="text-sm opacity-90">📍 {zonaPrincipal.referencia}</p>
                )}
                {zonaPrincipal.distancia_min != null && (
                  <p className="text-sm opacity-90">🚶 {zonaPrincipal.distancia_min} min</p>
                )}
                {(zonaPrincipal.saturation === 'alto' || zonaPrincipal.saturation === 'colapsado') && (
                  <p className="text-xs opacity-75 mt-1">⚠️ Últimos lugares (alto riesgo)</p>
                )}
              </div>
            </button>
          )}

          {/* 4. ALTERNATIVA (visible, no escondida) */}
          {zonaAlternativa && (
            <button
              onClick={() => setSelectedZona(zonaAlternativa)}
              className="w-full transition-transform active:scale-95"
            >
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  Si está lleno → {zonaAlternativa.name}
                </p>
                {zonaAlternativa.referencia && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">{zonaAlternativa.referencia}</p>
                )}
                {zonaAlternativa.distancia_min != null && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    {zonaAlternativa.distancia_min} min
                  </p>
                )}
              </div>
            </button>
          )}

          {/* 5. ACCIÓN PRINCIPAL */}
          {zonaPrincipal && hasCoords(zonaPrincipal) && (
            <button
              onClick={() => handleIniciarRuta(zonaPrincipal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg"
            >
              🗺️ Iniciar ruta
            </button>
          )}

          {/* 6. ESTADO / CONFIANZA */}
          <p className="text-xs text-slate-400 dark:text-slate-400 text-center">
            ✅ Estimación en tiempo real
          </p>
        </div>

        {/* BOTTOM SHEET */}
        {selectedZona && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedZona(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedZona(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedZona.name}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedZona.referencia || 'Sin referencia'}
                </p>
                {selectedZona.distancia_min != null && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    🚶 {selectedZona.distancia_min} min
                  </p>
                )}
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📊 Estado: {selectedZona.saturation}
                </p>
                {selectedZona.capacidad_estimada != null && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    👥 Capacidad estimada: {selectedZona.capacidad_estimada} personas
                  </p>
                )}
              </div>

              {hasCoords(selectedZona) && (
                <button
                  onClick={() => handleIniciarRuta(selectedZona)}
                  className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95"
                >
                  🗺️ Iniciar ruta
                </button>
              )}

              <button
                onClick={() => setSelectedZona(null)}
                className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95"
              >
                Cerrar
              </button>
            </div>
          </>
        )}
      </div>
    )
  }

  // FALLBACK — ¿Qué necesitás ahora? (cuando no hay zonas con datos suficientes)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Resolver ahora" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        {/* 1. CONTEXTO */}
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-300">
          <span>
            📍 {altaDemandaCount > 0 ? `${altaDemandaCount} zonas con alta demanda` : 'Todas las zonas disponibles'}
          </span>
          <span>🕒 {hora}</span>
          <span className={saturacionColor}>⚠️ {saturacionContexto}</span>
        </div>

        {/* 7. FALLBACK: ¿Qué necesitás ahora? */}
        <div className="text-center mb-4 mt-8">
          <p className="text-slate-600 dark:text-slate-300 text-sm">
            No puedo determinar exactamente qué necesitás ahora
          </p>
          <p className="text-slate-500 dark:text-slate-300 text-xs mt-1">
            Elegí una acción:
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => navigate('/estacionar')}
            className="w-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 p-4 rounded-xl text-left font-bold text-slate-800 dark:text-slate-100 transition-colors"
          >
            🚗 Estacionar
          </button>
          <button
            onClick={() => navigate('/emergencia')}
            className="w-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 p-4 rounded-xl text-left font-bold text-slate-800 dark:text-slate-100 transition-colors"
          >
            🚨 Emergencia
          </button>
          <button
            onClick={() => navigate('/salir')}
            className="w-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 p-4 rounded-xl text-left font-bold text-slate-800 dark:text-slate-100 transition-colors"
          >
            🚪 Salir
          </button>
          <button
            onClick={() => navigate('/servicios/transporte')}
            className="w-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 p-4 rounded-xl text-left font-bold text-slate-800 dark:text-slate-100 transition-colors"
          >
            🚌 Moverme
          </button>
        </div>
      </div>
    </div>
  )
}

export default ResolverAhora