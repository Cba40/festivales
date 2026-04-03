import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '../components/Header'
import { zonasSalida, getSalidasOrdenadas, ZonaSalida } from '../data/mockSalidas'
import { getTipoRecomendado } from '../utils/tipoRecomendado'
import { formatUpdatedAt } from '../utils/formatTime'

type TipoTransporte = 'auto' | 'transporte' | 'peatonal'

const Salir = () => {
  const navigate = useNavigate()
  const tipoRecomendado = getTipoRecomendado(zonasSalida)
  const [tipo, setTipo] = useState<TipoTransporte>(tipoRecomendado)
  const [selectedZona, setSelectedZona] = useState<ZonaSalida | null>(null)

  const salidasOrdenadas = useMemo(() => {
    return getSalidasOrdenadas(zonasSalida, tipo)
  }, [tipo])

  const opcionPrincipal = salidasOrdenadas[0]
  const opcionAlternativa = salidasOrdenadas[1]
  const zonaColapsada = zonasSalida.find(z => z.congestion === 'colapsado' && z.tipo === tipo)

  const todasMal = zonasSalida
    .filter(z => {
      if (tipo === 'auto') return z.tipo === 'auto' || z.tipo === 'peatonal'
      if (tipo === 'transporte') return z.tipo === 'transporte' || z.tipo === 'peatonal'
      if (tipo === 'peatonal') return z.tipo === 'peatonal' || z.tipo === 'auto'
      return true
    })
    .every(z => z.congestion === 'alta' || z.congestion === 'colapsado')

  const handleIniciarRuta = (zona: ZonaSalida) => {
    window.open(
      `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
      '_blank'
    )
  }

  const congestionLabel = opcionPrincipal
    ? opcionPrincipal.congestion === 'baja'
      ? '✅ Alta probabilidad de salida fluida'
      : opcionPrincipal.congestion === 'media'
        ? '⚠️ Demoras posibles'
        : '❗ Alta congestión — riesgo de demora'
    : ''

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Salir" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        {/* 0. BADGE RECOMENDADO */}
        {tipoRecomendado && (
          <button
            onClick={() => setTipo(tipoRecomendado)}
            className="w-full bg-primary/10 border-2 border-primary text-primary dark:text-blue-400 py-2 rounded-xl text-sm font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
          >
            👉 Recomendado ahora:
            {tipoRecomendado === 'auto' && '🚗 Auto'}
            {tipoRecomendado === 'transporte' && '🚌 Transporte'}
            {tipoRecomendado === 'peatonal' && '🚶 Caminando'}
            <span className="text-xs opacity-75">(tocar para aplicar)</span>
          </button>
        )}

        {/* 1. SELECTOR (arriba del todo) */}
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => setTipo('auto')}
            className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
              tipo === 'auto'
                ? 'bg-primary text-white'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
            }`}
          >
            🚗 Auto
          </button>
          <button
            onClick={() => setTipo('transporte')}
            className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
              tipo === 'transporte'
                ? 'bg-primary text-white'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
            }`}
          >
            🚌 Transporte
          </button>
          <button
            onClick={() => setTipo('peatonal')}
            className={`p-3 rounded-xl font-bold transition-transform active:scale-95 ${
              tipo === 'peatonal'
                ? 'bg-primary text-white'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
            }`}
          >
            🚶 Caminando
          </button>
        </div>

        {/* SATURACIÓN TOTAL */}
        {todasMal && (
          <div className="bg-warning/20 border border-warning p-4 rounded-xl">
            <p className="font-bold text-warning">🚧 Salidas saturadas</p>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Opciones: Esperar 10–15 min • Alejarse caminando
            </p>
          </div>
        )}

        {/* 2. MENSAJE PRINCIPAL */}
        {opcionPrincipal && (
          <div className="bg-primary text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">
              Dirigite ahora a {opcionPrincipal.nombre}
            </p>
          </div>
        )}

        {/* 3. BLOQUE PRINCIPAL (compacto) */}
        {opcionPrincipal && (
          <button
            onClick={() => setSelectedZona(opcionPrincipal)}
            className="w-full transition-transform active:scale-95"
          >
            <div className="bg-success text-white p-4 rounded-xl text-left shadow-lg">
              <p className="font-bold">📍 {opcionPrincipal.referencia}</p>
              <p className="text-sm">🚶 {opcionPrincipal.distancia_min} min</p>
              <p className="text-xs opacity-75">✅ Menor congestión</p>
              <p className="text-xs opacity-75">🕒 {formatUpdatedAt(opcionPrincipal.updatedAt)}</p>
              <p className="text-xs text-slate-100 mt-1">{congestionLabel}</p>
              <p className="text-sm font-bold mt-2">
                ⏱️ Tiempo estimado de salida: {opcionPrincipal.distancia_min + 5} min
              </p>
            </div>
          </button>
        )}

        {/* 4. ALTERNATIVA */}
        {opcionAlternativa && opcionAlternativa.congestion !== 'colapsado' && (
          <button
            onClick={() => setSelectedZona(opcionAlternativa)}
            className="w-full transition-transform active:scale-95"
          >
            <div className="bg-slate-100 dark:bg-slate-700 border-2 border-slate-300 dark:border-slate-600 p-4 rounded-xl text-left">
              <p className="font-bold text-slate-800 dark:text-slate-100">
                Si está saturado → {opcionAlternativa.nombre}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">📍 {opcionAlternativa.referencia}</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">🚶 {opcionAlternativa.distancia_min} min</p>
            </div>
          </button>
        )}

        {/* 5. ADVERTENCIA (si aplica) */}
        {zonaColapsada && (
          <div className="bg-danger text-white p-4 rounded-xl text-center">
            <p className="font-bold">🚫 Evitá {zonaColapsada.nombre}</p>
          </div>
        )}

        {/* 6. ACCIÓN */}
        {opcionPrincipal && (
          <button
            onClick={() => handleIniciarRuta(opcionPrincipal)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg transition-transform active:scale-95 shadow-lg"
          >
            🗺️ Iniciar ruta
          </button>
        )}
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
              <p className="text-sm text-slate-600 dark:text-slate-300">
                🚶 {selectedZona.distancia_min} min
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                📊 Congestión: {selectedZona.congestion}
              </p>
              {selectedZona.capacidad_estimada && (
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  👥 Capacidad estimada: {selectedZona.capacidad_estimada} personas
                </p>
              )}
              <p className="text-xs text-slate-500 dark:text-slate-400">
                🕒 {formatUpdatedAt(selectedZona.updatedAt)}
              </p>
            </div>

            <button
              onClick={() => handleIniciarRuta(selectedZona)}
              className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95"
            >
              🗺️ Iniciar ruta
            </button>

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

export default Salir
