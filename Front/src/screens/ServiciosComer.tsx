import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Map, X } from 'lucide-react'
import {
  getComidaOrdenada,
  getModoComer,
  todasColapsadas,
  PuntoComida
} from '@/data/mockComer'
import { eventoData } from '@/data/eventoData'
import { getConfianza, getConfianzaLabel } from '@/utils/confianza'
import { formatUpdatedAt } from '@/utils/formatTime'

const ServiciosComer = () => {
  const navigate = useNavigate()
  const [selectedPunto, setSelectedPunto] = useState<PuntoComida | null>(null)

  const puntosOrdenados = getComidaOrdenada(eventoData.comer)
  const modo = getModoComer(eventoData.comer)
  const sinSolucion = todasColapsadas(eventoData.comer)

  // Edge case: datos vacíos
  if (!puntosOrdenados.length) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/servicios')} />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-600 dark:text-slate-300 text-center">
            No hay datos disponibles en este momento
          </p>
        </div>
      </div>
    )
  }

  const principal = puntosOrdenados[0]
  const alternativa = puntosOrdenados[1]

  const abrirMapa = (punto: PuntoComida) => {
    if (punto.lat && punto.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${punto.lat},${punto.lng}`,
        '_blank'
      )
    }
    setSelectedPunto(null)
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

  // 🚧 SIN SOLUCIÓN REAL (todas colapsado)
  if (sinSolucion) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/servicios')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚧 No hay opciones convenientes en este momento</p>
            <p className="text-sm opacity-90 mt-2">No hay opciones disponibles en este momento</p>
          </div>

          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
            <p className="font-bold text-slate-800 dark:text-slate-200">Opciones:</p>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              ⏱️ Esperar 20–30 min
            </button>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              🚶 Alejarse de esta zona
            </button>
          </div>
        </div>
      </div>
    )
  }

  // MODO GUIAR
  if (modo === 'guiar') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Comer" showBack onBack={() => navigate('/servicios')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">👉 Alta demanda en esta zona</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          {/* Acción principal: MEJOR opción (index 0) */}
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

          {principal && (
            <p className="text-xs text-slate-500 dark:text-slate-400 -mt-2 text-center">
              {formatUpdatedAt(principal.updatedAt)}
            </p>
          )}

          {/* Fallback: segunda opción */}
          {alternativa && (
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
              Ir ahora
            </button>
          )}
        </div>

        {/* Bottom Sheet */}
        {selectedPunto && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedPunto(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedPunto(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedPunto.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedPunto.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {selectedPunto.distancia_min} min
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  ⏱️ Espera: {selectedPunto.espera_min} min
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatUpdatedAt(selectedPunto.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {getConfianzaLabel(getConfianza(selectedPunto.estado))}
                </p>
              </div>

              <button
                onClick={() => abrirMapa(selectedPunto)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Ir ahora
              </button>

              <button
                onClick={() => setSelectedPunto(null)}
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
        <Header title="Comer" showBack onBack={() => navigate('/servicios')} />

        <div className="flex-1 p-4 space-y-4">
          {/* Mejor opción ahora */}
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

          {/* Alternativa debajo */}
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
              Ir ahora
            </button>
          )}
        </div>

        {/* Bottom Sheet */}
        {selectedPunto && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedPunto(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedPunto(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedPunto.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedPunto.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {selectedPunto.distancia_min} min
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  ⏱️ Espera: {selectedPunto.espera_min} min
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatUpdatedAt(selectedPunto.updatedAt)}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {getConfianzaLabel(getConfianza(selectedPunto.estado))}
                </p>
              </div>

              <button
                onClick={() => abrirMapa(selectedPunto)}
                className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Ir ahora
              </button>

              <button
                onClick={() => setSelectedPunto(null)}
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

  // MODO INFORMAR (lista, máx 3)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Comer" showBack onBack={() => navigate('/servicios')} />

      <div className="flex-1 p-4 space-y-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
            Puntos de comida disponibles
          </h2>
          <div className="space-y-3">
            {puntosOrdenados.slice(0, 3).map((punto) => (
              <button
                key={punto.id}
                onClick={() => setSelectedPunto(punto)}
                className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-gray-900 dark:text-gray-100">
                    {punto.nombre}
                  </span>
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(punto.estado)}`}
                  >
                    {punto.estado}
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

        {/* Botón global */}
        {principal && (
          <button
            onClick={() => abrirMapa(principal)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg flex items-center justify-center gap-2"
          >
            <Map size={20} />
            Ir ahora
          </button>
        )}
      </div>

      {/* Bottom Sheet */}
      {selectedPunto && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedPunto(null)}
          />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div
              className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
              onClick={() => setSelectedPunto(null)}
            />

            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
              {selectedPunto.nombre}
            </h3>

            <div className="space-y-2 mb-4">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                📍 {selectedPunto.referencia}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🚶 {selectedPunto.distancia_min} min
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                ⏱️ Espera: {selectedPunto.espera_min} min
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatUpdatedAt(selectedPunto.updatedAt)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {getConfianzaLabel(getConfianza(selectedPunto.estado))}
              </p>
            </div>

            <button
              onClick={() => abrirMapa(selectedPunto)}
              className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95 flex items-center justify-center gap-2"
            >
              <Map size={20} />
              Ir ahora
            </button>

            <button
              onClick={() => setSelectedPunto(null)}
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

export default ServiciosComer
