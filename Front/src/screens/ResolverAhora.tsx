import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '../components/Header'
import { inferirNecesidad, ResultadoInferencia } from '../data/mockResolver'
import { eventoData } from '@/data/eventoData'
import type { ZonaSalida } from '@/data/eventoData'
import { Zona } from '../types'

type ZonaSeleccionada = ZonaSalida | Zona | null

const hasCoords = (zona: ZonaSeleccionada): zona is (ZonaSalida | Zona) => {
  return zona !== null && 'lat' in zona && 'lng' in zona
}

const ResolverAhora = () => {
  const navigate = useNavigate()
  const [selectedZona, setSelectedZona] = useState<ZonaSeleccionada>(null)

  const inferencia: ResultadoInferencia = inferirNecesidad()

  const handleIniciarRuta = (zona: ZonaSeleccionada) => {
    if (hasCoords(zona)) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      )
    }
  }

  const saturacionColor =
    inferencia.contexto.saturacion === 'colapsada' ? 'text-danger' :
    inferencia.contexto.saturacion === 'alta' ? 'text-warning' :
    'text-success'

  // CASO A: Inferencia exitosa (80%)
  if (inferencia.tipo !== 'fallback') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Resolver ahora" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          {/* 1. CONTEXTO (arriba, pequeño) */}
          <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>📍 {inferencia.contexto.zona}</span>
            <span>🕒 {inferencia.contexto.hora}</span>
            <span className={saturacionColor}>
              ⚠️ {inferencia.contexto.saturacion}
            </span>
          </div>

          {/* 2. MENSAJE PRINCIPAL (grande, dominante) */}
          <div className="bg-primary text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">{inferencia.mensaje}</p>
          </div>

          {/* 3. DETALLE CLAVE — Zona principal */}
          {inferencia.zonaPrincipal && (
            <button
              onClick={() => setSelectedZona(inferencia.zonaPrincipal)}
              className="w-full transition-transform active:scale-95"
            >
              <div className="bg-success text-white p-6 rounded-xl text-left shadow-lg">
                <p className="text-lg font-bold">
                  👉 Dirigite ahora a {inferencia.zonaPrincipal.nombre}
                </p>
                <p className="text-sm opacity-90">📍 {inferencia.zonaPrincipal.referencia}</p>
                {'distancia_min' in inferencia.zonaPrincipal && (
                  <p className="text-sm opacity-90">🚶 {inferencia.zonaPrincipal.distancia_min} min</p>
                )}
                {'estado' in inferencia.zonaPrincipal && inferencia.zonaPrincipal.estado === 'alto' && (
                  <p className="text-xs opacity-75 mt-1">⚠️ Últimos lugares (alto riesgo)</p>
                )}
              </div>
            </button>
          )}

          {/* 4. ALTERNATIVA (visible, no escondida) */}
          {inferencia.zonaAlternativa && (
            <button
              onClick={() => setSelectedZona(inferencia.zonaAlternativa)}
              className="w-full transition-transform active:scale-95"
            >
              <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
                <p className="font-bold text-slate-800 dark:text-slate-100">
                  Si está lleno → {inferencia.zonaAlternativa.nombre}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">{inferencia.zonaAlternativa.referencia}</p>
                {'distancia_min' in inferencia.zonaAlternativa && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">{inferencia.zonaAlternativa.distancia_min} min</p>
                )}
              </div>
            </button>
          )}

          {/* 5. ACCIÓN PRINCIPAL */}
          {inferencia.zonaPrincipal && hasCoords(inferencia.zonaPrincipal) && (
            <button
              onClick={() => handleIniciarRuta(inferencia.zonaPrincipal)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg"
            >
              🗺️ Iniciar ruta
            </button>
          )}

          {/* 6. ESTADO / CONFIANZA */}
          <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
            {inferencia.confianza === 'alta' ? '✅' : '⚠️'} Estimación en tiempo real
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
                {selectedZona.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedZona.referencia}
                </p>
                {'distancia_min' in selectedZona && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    🚶 {selectedZona.distancia_min} min
                  </p>
                )}
                {'congestion' in selectedZona && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    📊 Congestión: {String(selectedZona.congestion)}
                  </p>
                )}
                {'estado' in selectedZona && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    📊 Estado: {String(selectedZona.estado)}
                  </p>
                )}
                {'capacidad_estimada' in selectedZona && selectedZona.capacidad_estimada !== undefined && (
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    👥 Capacidad estimada: {selectedZona.capacidad_estimada} personas
                  </p>
                )}
                {'timestamp' in selectedZona && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    🕒 {selectedZona.timestamp}
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

  // CASO B: FALLBACK — ¿Qué necesitás ahora? (20%, 3 opciones máximo)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Resolver ahora" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        {/* 1. CONTEXTO */}
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>📍 {inferencia.contexto.zona}</span>
          <span>🕒 {inferencia.contexto.hora}</span>
          <span className={saturacionColor}>
            ⚠️ {inferencia.contexto.saturacion}
          </span>
        </div>

        {/* 7. FALLBACK: ¿Qué necesitás ahora? */}
        <div className="text-center mb-4 mt-8">
          <p className="text-slate-600 dark:text-slate-300 text-sm">
            No puedo determinar exactamente qué necesitás ahora
          </p>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-1">
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
