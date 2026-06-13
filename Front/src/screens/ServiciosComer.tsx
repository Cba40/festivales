import { useState, useMemo, lazy, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, MapIcon, List } from 'lucide-react'
import PuntoDetallePanel from '@/components/PuntoDetallePanel'

const GastronomyMap = lazy(() => import('@/components/GastronomyMap'))
import {
  getComidaOrdenada,
  getModoComer,
} from '@/data/mockComer'
import { useAppStore } from '@/core/state/store'
import { mapZonesToComida } from '@/data/mappers'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'
import type { PuntoComida } from '@/data/mappers'

const getEstadoStyles = (estado: string) => {
  switch (estado) {
    case 'bajo':
      return 'bg-success/20 text-success'
    case 'medio':
      return 'bg-warning/20 text-warning'
    case 'alto':
      return 'bg-danger/20 text-danger'
    case 'colapsado':
      return 'bg-gray-500/20 text-gray-500'
    default:
      return 'bg-gray-500/20 text-gray-500'
  }
}

const getEstadoLabel = (estado: string) => {
  switch (estado) {
    case 'bajo': return '🟢 Bajo'
    case 'medio': return '🟡 Medio'
    case 'alto': return '🔴 Alto'
    case 'colapsado': return '⚫ Colapsado'
    default: return estado
  }
}

const ServiciosComer = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [selectedPunto, setSelectedPunto] = useState<PuntoComida | null>(null)
  const [mostrarOpciones, setMostrarOpciones] = useState(false)
  const [showMap, setShowMap] = useState(false)

  const comidas = useMemo(() => mapZonesToComida(zones), [zones])
  const comidasOrdenadas = useMemo(() => getComidaOrdenada(comidas), [comidas])
  const modo = useMemo(() => getModoComer(comidas), [comidas])

  const principal = comidasOrdenadas[0]
  const alternativa = comidasOrdenadas[1]

  const abrirMapa = (punto: PuntoComida) => {
    if (punto.lat && punto.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${punto.lat},${punto.lng}`,
        '_blank'
      )
    }
    setSelectedPunto(null)
  }

  if (modo === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚧 No hay opciones convenientes para comer</p>
            <p className="text-sm mt-2 opacity-90">Alta demanda en todas las zonas gastronómicas</p>
          </div>

          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              ⏱️ Esperar 20–30 min
            </button>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              🚶 Explorar otra zona
            </button>
          </div>

          <div className="mt-4 text-center space-y-2">
            <p className="text-xs text-slate-400 dark:text-slate-500">
              No hay opciones recomendadas en este momento
            </p>
            <button
              className="text-xs underline text-slate-500 dark:text-slate-400"
              onClick={() => setMostrarOpciones(true)}
            >
              Ver opciones igualmente
            </button>
          </div>

          {mostrarOpciones && (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-red-500 text-center">
                ⚠️ Disponibilidad muy baja — podés no encontrar lugar
              </p>
              {comidasOrdenadas.slice(0, 2).map((punto) => (
                <button
                  key={punto.id}
                  onClick={() => setSelectedPunto(punto)}
                  className="w-full p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg text-left"
                >
                  <span className="font-bold text-gray-900 dark:text-gray-100">{punto.nombre}</span>
                  <span className={`ml-2 px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(punto.estado)}`}>
                    {getEstadoLabel(punto.estado)}
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    🚶 {punto.distancia_min} min · ⏱️ {punto.espera_min} min
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  if (modo === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Zona gastronómica saturada</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {principal && (
            <button
              onClick={() => setSelectedPunto(principal)}
              className="w-full"
            >
              <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg">
                <p className="text-lg font-bold">
                  👉 Dirigite ahora a {principal.nombre}
                </p>
                <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
                <p className="text-sm opacity-90">🚶 {principal.distancia_min} min</p>
                <p className="text-sm opacity-90">⏱️ Espera: {principal.espera_min} min</p>
                {principal.estado === 'alto' && (
                  <p className="text-xs opacity-75 mt-2">⚠️ Últimos lugares</p>
                )}
              </div>
            </button>
          )}

          {alternativa && principal?.estado !== 'colapsado' && (
            <button
              onClick={() => setSelectedPunto(alternativa)}
              className="w-full"
            >
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  👉 Si está lleno → {alternativa.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                  📍 {alternativa.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {alternativa.distancia_min} min · ⏱️ {alternativa.espera_min} min
                </p>
              </div>
            </button>
          )}

          <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
            {getConfianzaLabel(getConfianza(principal?.estado || 'medio'))}
          </p>

          {principal && (
            <button
              onClick={() => abrirMapa(principal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg flex items-center justify-center gap-2"
            >
              <Map size={20} />
              Iniciar ruta
            </button>
          )}
        </div>
      </div>
    )
  }

  if (modo === 'asistir') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {principal && (
            <button
              onClick={() => setSelectedPunto(principal)}
              className="w-full"
            >
              <div className="bg-white dark:bg-slate-800 border-l-4 border-primary p-4 rounded-xl text-left shadow-md">
                <p className="font-bold text-slate-800 dark:text-slate-100 text-lg">
                  👉 Mejor opción ahora: {principal.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">
                  📍 {principal.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {principal.distancia_min} min · ⏱️ {principal.espera_min} min
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                  {formatUpdatedAt(principal.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {getConfianzaLabel(getConfianza(principal.estado))}
                </p>
              </div>
            </button>
          )}

          {alternativa && (
            <button
              onClick={() => setSelectedPunto(alternativa)}
              className="w-full"
            >
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  Alternativa: {alternativa.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                  📍 {alternativa.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {alternativa.distancia_min} min · ⏱️ {alternativa.espera_min} min
                </p>
              </div>
            </button>
          )}

          {principal && (
            <button
              onClick={() => abrirMapa(principal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg flex items-center justify-center gap-2"
            >
              <Map size={20} />
              Iniciar ruta
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Comer" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        <button
          onClick={() => setShowMap(!showMap)}
          className="w-full bg-primary text-white py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
        >
          {showMap ? <List size={20} /> : <MapIcon size={20} />}
          {showMap ? 'Ver lista' : 'Ver mapa completo'}
        </button>

        {showMap ? (
          <div className="h-[60vh] min-h-[400px] rounded-xl overflow-hidden border border-slate-200 dark:border-slate-600">
            <Suspense fallback={<div className="flex items-center justify-center h-full text-slate-500">Cargando mapa...</div>}>
              <GastronomyMap puntos={comidas} userLocation={null} onSelect={setSelectedPunto} />
            </Suspense>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
            <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
              Zonas gastronómicas disponibles
            </h2>
            <div className="text-xs text-gray-500 mt-2 mb-4">
              🟢 Bajo: rápido · 🟡 Medio: demora moderada · 🔴 Alto: mucha demora
            </div>
            <div className="space-y-3">
              {comidasOrdenadas.slice(0, 3).map((punto) => (
                <button
                  key={punto.id}
                  onClick={() => setSelectedPunto(punto)}
                  className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold mr-2 text-gray-900 dark:text-gray-100">
                      {punto.nombre}
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap shrink-0 ${getEstadoStyles(punto.estado)}`}
                    >
                      {getEstadoLabel(punto.estado)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    📍 {punto.referencia}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    🚶 {punto.distancia_min} min · ⏱️ {punto.espera_min} min
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    {formatUpdatedAt(punto.updatedAt)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {getConfianzaLabel(getConfianza(punto.estado))}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <PuntoDetallePanel punto={selectedPunto} onClose={() => setSelectedPunto(null)} />
    </div>
  )
}

export default ServiciosComer
