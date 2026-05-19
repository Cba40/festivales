import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X } from 'lucide-react'
import {
  getParadasOrdenadas,
  getModoTransporte,
  ParadaTransporte
} from '@/data/mockTransporte'
import { eventoData } from '@/data/eventoData'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'

const ServiciosTransporte = () => {
  const navigate = useNavigate()
  const [selectedParada, setSelectedParada] = useState<ParadaTransporte | null>(null)

  const paradasOrdenadas = getParadasOrdenadas(eventoData.transporte)
  const modo = getModoTransporte(eventoData.transporte)

  const principal = paradasOrdenadas[0]
  const alternativa = paradasOrdenadas[1]

  const abrirMapa = (parada: ParadaTransporte) => {
    if (parada.lat && parada.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${parada.lat},${parada.lng}`,
        '_blank'
      )
    }
    setSelectedParada(null)
  }

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

  // SIN SOLUCIÓN por score o estado
  if (modo === 'sin_solucion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Transporte" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚧 No conviene tomar transporte en este momento</p>
            <p className="text-sm mt-2 opacity-90">Tiempos de espera y acceso elevados</p>
          </div>

          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
            <button
              onClick={() => navigate('/salir')}
              className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform"
            >
              🚶 Ir caminando
            </button>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              ⏱️ Esperar 20–30 min
            </button>
          </div>
        </div>
      </div>
    )
  }

  // MODO GUIAR (CRÍTICO)
  if (modo === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Transporte" showBack onBack={() => navigate('/')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Zona actual saturada</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {/* Acción principal: MEJOR opción (index 0) */}
          {principal && (
            <button
              onClick={() => setSelectedParada(principal)}
              className="w-full"
            >
              <div className="bg-primary text-white p-6 rounded-xl text-left shadow-lg">
                <p className="text-lg font-bold">
                  👉 Dirigite ahora a {principal.nombre}
                </p>
                <p className="text-sm opacity-90 mt-2">📍 {principal.referencia}</p>
                <p className="text-sm opacity-90">🚶 {principal.distancia_min} min</p>
                <p className="text-sm opacity-90">⏱️ Espera: {principal.espera_min} min</p>
                <p className="text-sm opacity-90">🧭 Caminá por {principal.calle}</p>
                {principal.estado === 'alto' && (
                  <p className="text-xs opacity-75 mt-2">⚠️ Últimos lugares</p>
                )}
              </div>
            </button>
          )}

          {principal && (
            <p className="text-xs text-slate-500 dark:text-slate-400 -mt-2 text-center">
              {formatUpdatedAt(principal.updatedAt)}
            </p>
          )}

          {/* Fallback: segunda opción */}
          {alternativa && (
            <button
              onClick={() => setSelectedParada(alternativa)}
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

          {!alternativa && (
            <p className="text-sm text-slate-500 mt-2">
              ℹ️ Es la única opción disponible en este momento
            </p>
          )}

          {/* Confianza */}
          <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
            {getConfianzaLabel(getConfianza(principal?.estado || 'medio'))}
          </p>

          {/* Botón global */}
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

        {/* Bottom Sheet */}
        {selectedParada && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedParada(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedParada(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedParada.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedParada.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {selectedParada.distancia_min} min
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  ⏱️ Espera: {selectedParada.espera_min} min
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🧭 {selectedParada.calle}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatUpdatedAt(selectedParada.updatedAt)}
                </p>
              </div>

              <button
                onClick={() => abrirMapa(selectedParada)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedParada(null)}
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

  // MODO ASISTIR
  if (modo === 'asistir') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Transporte" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {/* Mejor opción ahora */}
          {principal && (
            <button
              onClick={() => setSelectedParada(principal)}
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
                  Menor espera + cercanía
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

          {/* Alternativa debajo */}
          {alternativa && (
            <button
              onClick={() => setSelectedParada(alternativa)}
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
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                  {formatUpdatedAt(alternativa.updatedAt)}
                </p>
              </div>
            </button>
          )}

          {/* Botón global */}
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

        {/* Bottom Sheet */}
        {selectedParada && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedParada(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedParada(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedParada.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedParada.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {selectedParada.distancia_min} min
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  ⏱️ Espera: {selectedParada.espera_min} min
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🧭 {selectedParada.calle}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatUpdatedAt(selectedParada.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {getConfianzaLabel(getConfianza(selectedParada.estado))}
                </p>
              </div>

              <button
                onClick={() => abrirMapa(selectedParada)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedParada(null)}
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

  // MODO INFORMAR (lista de paradas, máx 3)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Transporte" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
            Paradas disponibles
          </h2>
          <div className="text-xs text-gray-500 mt-2 mb-4">
            🟢 Bajo: rápido · 🟡 Medio: demora moderada · 🔴 Alto: mucha demora
          </div>
          <div className="space-y-3">
            {paradasOrdenadas.slice(0, 3).map((parada, index) => {
              const isTop = index === 0;
              return (
                <button
                  key={parada.id}
                  onClick={() => setSelectedParada(parada)}
                  className={`w-full p-4 bg-white dark:bg-slate-700 border ${isTop ? 'border-primary ring-1 ring-primary/20' : 'border-slate-200 dark:border-slate-600'} rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors`}
                >
                  <div className="flex justify-between items-center">
                    <span className={`font-bold mr-2 ${isTop ? 'text-primary dark:text-blue-400' : 'text-gray-900 dark:text-gray-100'}`}>
                      {isTop ? '🔥 Mejor opción ahora: ' : ''}{parada.nombre}
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold whitespace-nowrap shrink-0 ${getEstadoStyles(parada.estado)}`}
                    >
                      {getEstadoLabel(parada.estado)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    📍 {parada.referencia}
                  </p>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  🚶 {parada.distancia_min} min · ⏱️ {parada.espera_min} min
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  {formatUpdatedAt(parada.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {getConfianzaLabel(getConfianza(parada.estado))}
                </p>
              </button>
            )})}
          </div>
        </div>

        {/* Botón global */}
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

      {/* Bottom Sheet */}
      {selectedParada && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedParada(null)}
          />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div
              className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
              onClick={() => setSelectedParada(null)}
            />

            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
              {selectedParada.nombre}
            </h3>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                📍 {selectedParada.referencia}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🚶 {selectedParada.distancia_min} min
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                ⏱️ Espera: {selectedParada.espera_min} min
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🧭 {selectedParada.calle}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatUpdatedAt(selectedParada.updatedAt)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {getConfianzaLabel(getConfianza(selectedParada.estado))}
              </p>
            </div>

            <button
              onClick={() => abrirMapa(selectedParada)}
              className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
            >
              <Map size={20} />
              Iniciar ruta
            </button>

            <button
              onClick={() => setSelectedParada(null)}
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

export default ServiciosTransporte
