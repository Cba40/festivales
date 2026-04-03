import { useState } from 'react';
import { Header } from '@/components/Header';
import { ZonaCard } from '@/components/ZonaCard';
import { Map, X } from 'lucide-react';
import { mockZones, getZonasOrdenadas, getModoGuiar } from '@/data/mockZones';
import { Zona } from '@/types';
import { useNavigate } from 'react-router-dom';
import { getConfianza, getConfianzaLabel } from '@/utils/confianza';
import { formatUpdatedAt } from '@/utils/formatTime';

const Estacionar = () => {
  const navigate = useNavigate();
  const [selectedZone, setSelectedZone] = useState<Zona | null>(null);
  const [showLejanas, setShowLejanas] = useState(false);

  const modoGuiar = getModoGuiar();
  const zonasOrdenadas = getZonasOrdenadas();
  const zonaActual = mockZones.find((z) => z.id === 'zona-actual');
  const zonaFallback = zonasOrdenadas[1];

  const todasColapsadas = zonasOrdenadas.every((z) => z.estado === 'colapsado');
  const zonasLejanas = mockZones.filter(z => z.distancia_min > 15);

  const abrirMapa = (zona: Zona) => {
    if (zona.lat && zona.lng) {
      window.open(
        `https://www.google.com/maps/dir/?api=1&destination=${zona.lat},${zona.lng}`,
        '_blank'
      );
    } else {
      alert(`Ruta a ${zona.nombre} (coordenadas pendientes)`);
    }
    setSelectedZone(null);
  };

  const getEstadoStyles = (estado: string) => {
    switch (estado) {
      case 'bajo':
        return 'bg-success/20 text-success';
      case 'medio':
        return 'bg-warning/20 text-warning';
      case 'alto':
        return 'bg-danger/20 text-danger';
      case 'colapsado':
        return 'bg-gray-500/20 text-gray-500';
      default:
        return 'bg-gray-500/20 text-gray-500';
    }
  };

  // FALLBACK FINAL: no hay zonas lejanas y todas colapsadas
  if (todasColapsadas && zonasLejanas.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />
        <div className="flex-1 p-4 space-y-4">
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🚫 No hay opciones disponibles</p>
            <p className="text-sm opacity-90 mt-2">En este momento</p>
          </div>
          <div className="bg-slate-100 dark:bg-slate-700 p-4 rounded-xl space-y-3">
            <p className="font-bold text-slate-800 dark:text-slate-200">Opciones:</p>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              ⏱️ Esperar 15–20 min
            </button>
            <button className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 p-3 rounded-lg font-bold active:scale-95 transition-transform">
              📍 Mantener posición
            </button>
          </div>
        </div>
      </div>
    );
  }

  // MODO GUIAR: todas colapsadas pero hay zonas lejanas
  if (todasColapsadas) {
    const zonaSur =
      zonasOrdenadas.find((z) => z.id === 'zona-sur') || zonasOrdenadas[0];

    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="bg-danger text-white px-4 py-3">
          <h2 className="font-bold text-lg">Zonas cercanas completas</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-lg">
            <h3 className="font-bold text-gray-800 dark:text-gray-100 mb-4 text-lg">
              Estrategias disponibles:
            </h3>

            <div className="space-y-4">
              <button
                onClick={() => setSelectedZone(zonaSur)}
                className="w-full text-left border-l-4 border-primary pl-4 hover:bg-gray-50 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <div className="font-bold text-gray-900 dark:text-gray-100 mb-1">
                  Dirigite a {zonaSur.nombre}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  {zonaSur.distancia_min} cuadras · Aproximadamente{' '}
                  {Math.ceil(zonaSur.distancia_min * 1.5)} min caminando
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {zonaSur.capacidad_estimada} lugares estimados disponibles
                </div>
              </button>

              <div className="border-l-4 border-warning pl-4">
                <div className="font-bold text-gray-900 dark:text-gray-100 mb-1">
                  Esperá 15-20 minutos
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Las zonas cercanas podrían liberar lugares
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Media probabilidad · Verificá nuevamente en unos minutos
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowLejanas(true)}
            className="w-full bg-primary text-white rounded-xl px-6 py-4 font-bold flex items-center justify-center gap-2 shadow-lg active:scale-95 transition-all"
          >
            <Map size={20} />
            🗺️ Ver opciones lejanas (15–20 min)
          </button>

          <button
            onClick={() => window.location.reload()}
            className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-xl px-6 py-3 font-bold active:scale-95 transition-all"
          >
            ⏱️ Reintentar en 15 min
          </button>
        </div>

        {/* Bottom Sheet - Zonas Lejanas */}
        {showLejanas && zonasLejanas.length > 0 && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setShowLejanas(false)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setShowLejanas(false)}
              />
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-3">
                Zonas lejanas
              </h3>
              <div className="space-y-3">
                {zonasLejanas.slice(0, 2).map((zona) => (
                  <button
                    key={zona.id}
                    onClick={() => {
                      setSelectedZone(zona);
                      setShowLejanas(false);
                    }}
                    className="w-full p-3 bg-gray-50 dark:bg-slate-700 rounded-lg text-left"
                  >
                    <div className="font-bold text-gray-900 dark:text-gray-100">
                      {zona.nombre}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {zona.distancia_min} cuadras · {zona.referencia}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Bottom Sheet - Zone detail */}
        {selectedZone && !showLejanas && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedZone(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4"
                onClick={() => setSelectedZone(null)}
              />

              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                Dirigite ahora a {selectedZone.nombre}
              </h3>

              <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1 mb-4">
                <p>🚶 {selectedZone.distancia_min * 1.5} min caminando</p>
                <p>📍 {selectedZone.referencia}</p>
                <p className="text-gray-400 dark:text-gray-500">
                  {selectedZone.updatedAt ? formatUpdatedAt(selectedZone.updatedAt) : selectedZone.timestamp}
                </p>
              </div>

              {selectedZone.estado === 'alto' && (
                <div className="bg-warning/20 text-warning p-2 rounded-lg text-sm font-bold mb-4 text-center">
                  ⚠️ Últimos lugares (alto riesgo)
                </div>
              )}

              <button
                onClick={() => abrirMapa(selectedZone)}
                className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedZone(null)}
                className="w-full mt-3 py-2 text-gray-500 dark:text-gray-400 text-sm flex items-center justify-center gap-2"
              >
                <X size={16} />
                Cancelar
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  // MODO INFORMAR: lista de zonas disponibles
  if (!modoGuiar) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
            <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-4">
              Zonas disponibles
            </h2>
            <div className="space-y-3">
              {zonasOrdenadas.map((zona) => (
                <button
                  key={zona.id}
                  onClick={() => setSelectedZone(zona)}
                  className="w-full p-4 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-left hover:border-primary dark:hover:border-primary/70 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-gray-900 dark:text-gray-100">
                      {zona.nombre}
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(zona.estado)}`}
                    >
                      {zona.estado}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                    🚶 {zona.distancia_min * 1.5} min · {zona.referencia}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    {zona.updatedAt ? formatUpdatedAt(zona.updatedAt) : zona.timestamp}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {getConfianzaLabel(getConfianza(zona.estado))}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Sheet */}
        {selectedZone && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedZone(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4"
                onClick={() => setSelectedZone(null)}
              />

              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                Dirigite ahora a {selectedZone.nombre}
              </h3>

              <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1 mb-4">
                <p>🚶 {selectedZone.distancia_min * 1.5} min caminando</p>
                <p>📍 {selectedZone.referencia}</p>
                <p className="text-gray-400 dark:text-gray-500">
                  {selectedZone.updatedAt ? formatUpdatedAt(selectedZone.updatedAt) : selectedZone.timestamp}
                </p>
              </div>

              {selectedZone.estado === 'alto' && (
                <div className="bg-warning/20 text-warning p-2 rounded-lg text-sm font-bold mb-4 text-center">
                  ⚠️ Últimos lugares (alto riesgo)
                </div>
              )}

              <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                {getConfianzaLabel(getConfianza(selectedZone.estado))}
              </p>

              {zonaFallback && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Si está llena →{' '}
                  <span className="font-bold">{zonaFallback.nombre}</span>
                </p>
              )}

              <button
                onClick={() => abrirMapa(selectedZone)}
                className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedZone(null)}
                className="w-full mt-3 py-2 text-gray-500 dark:text-gray-400 text-sm flex items-center justify-center gap-2"
              >
                <X size={16} />
                Cancelar
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  // MODO ASISTIR: recomendada + alternativa
  if (zonasOrdenadas.length > 1 && !todasColapsadas) {
    const zonaRecomendada = zonasOrdenadas[0];

    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Estacionar" showBack onBack={() => navigate('/')} />

        <div className="flex-1 p-4 space-y-4">
          <button
            onClick={() => setSelectedZone(zonaRecomendada)}
            className="w-full"
          >
            <ZonaCard
              zona={zonaRecomendada}
              tipo="primaria"
              distanciaTexto={`${zonaRecomendada.distancia_min} cuadras`}
              accionTexto={`Dirigite ahora a ${zonaRecomendada.nombre}`}
            />
          </button>

          {zonaRecomendada.updatedAt && (
            <p className="text-xs text-slate-500 dark:text-slate-400 -mt-2 text-center">
              {formatUpdatedAt(zonaRecomendada.updatedAt)}
            </p>
          )}

          {zonaFallback && (
            <button
              onClick={() => setSelectedZone(zonaFallback)}
              className="w-full"
            >
              <ZonaCard
                zona={zonaFallback}
                tipo="fallback"
                distanciaTexto={`${zonaFallback.distancia_min} cuadras · ${Math.ceil(zonaFallback.distancia_min * 1.5)} min`}
                accionTexto={`Alternativa: ${zonaFallback.nombre}`}
              />
            </button>
          )}

          {zonaRecomendada.tendencia === 'subiendo' && (
            <div className="bg-warning/20 border border-warning text-warning p-3 rounded-xl text-center text-sm font-bold">
              ⚠️ Se está completando
            </div>
          )}

          <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md">
            <h3 className="font-bold text-gray-800 dark:text-gray-100 mb-3">
              Otras zonas:
            </h3>
            <div className="space-y-2">
              {zonasOrdenadas.slice(2).map((zona) => (
                <button
                  key={zona.id}
                  onClick={() => setSelectedZone(zona)}
                  className="w-full p-3 bg-gray-50 dark:bg-slate-700 rounded-lg text-left hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-gray-900 dark:text-gray-100">
                      {zona.nombre}
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold ${getEstadoStyles(zona.estado)}`}
                    >
                      {zona.estado}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {zona.distancia_min * 1.5} min · {zona.referencia}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {getConfianzaLabel(getConfianza(zona.estado))}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Sheet */}
        {selectedZone && (
          <>
            <div
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setSelectedZone(null)}
            />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4"
                onClick={() => setSelectedZone(null)}
              />

              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                Dirigite ahora a {selectedZone.nombre}
              </h3>

              <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1 mb-4">
                <p>🚶 {selectedZone.distancia_min * 1.5} min caminando</p>
                <p>📍 {selectedZone.referencia}</p>
                <p className="text-gray-400 dark:text-gray-500">
                  {selectedZone.updatedAt ? formatUpdatedAt(selectedZone.updatedAt) : selectedZone.timestamp}
                </p>
              </div>

              {selectedZone.estado === 'alto' && (
                <div className="bg-warning/20 text-warning p-2 rounded-lg text-sm font-bold mb-4 text-center">
                  ⚠️ Últimos lugares (alto riesgo)
                </div>
              )}

              <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                {getConfianzaLabel(getConfianza(selectedZone.estado))}
              </p>

              {zonaFallback && selectedZone.id !== zonaFallback.id && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                  Si está llena →{' '}
                  <span className="font-bold">{zonaFallback.nombre}</span>
                </p>
              )}

              <button
                onClick={() => abrirMapa(selectedZone)}
                className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
              >
                <Map size={20} />
                Iniciar ruta
              </button>

              <button
                onClick={() => setSelectedZone(null)}
                className="w-full mt-3 py-2 text-gray-500 dark:text-gray-400 text-sm flex items-center justify-center gap-2"
              >
                <X size={16} />
                Cancelar
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  // MODO GUIAR COMPLETO: 6 bloques
  const zonaPrimaria = zonasOrdenadas[0];
  const distanciaPrimaria = zonaPrimaria.distancia_min;
  const tiempoPrimaria = Math.ceil(distanciaPrimaria * 1.5);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header
        title="Estacionar - Modo Guiar"
        showBack
        onBack={() => navigate('/')}
      />

      <div className="flex-1 p-4 space-y-3">
        {/* BLOQUE 1: Estado actual */}
        {zonaActual && (
          <ZonaCard
            zona={zonaActual}
            tipo="completa"
            accionTexto="Zona actual COMPLETA"
          />
        )}

        {/* BLOQUE 2: Acción principal */}
        <button
          onClick={() => setSelectedZone(zonaPrimaria)}
          className="w-full"
        >
          <ZonaCard
            zona={zonaPrimaria}
            tipo="primaria"
            distanciaTexto={`${distanciaPrimaria} cuadras`}
            accionTexto={`Dirigite ahora a ${zonaPrimaria.nombre}`}
          />
        </button>

        {zonaPrimaria.updatedAt && (
          <p className="text-xs text-slate-500 dark:text-slate-400 -mt-1 text-center">
            {formatUpdatedAt(zonaPrimaria.updatedAt)}
          </p>
        )}

        {/* BLOQUE 3: Tiempo estimado */}
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-md border-l-4 border-success">
          <div className="flex items-center gap-2 text-gray-800 dark:text-gray-100">
            <span className="text-xl">⏱</span>
            <span className="font-bold">
              {tiempoPrimaria} min caminando (estimado)
            </span>
          </div>
        </div>

        {/* BLOQUE 4: Riesgo (si estado es 'alto') */}
        {zonaPrimaria.estado === 'alto' && (
          <div className="bg-warning text-white rounded-xl p-4 shadow-md">
            <div className="flex items-center gap-2">
              <span className="text-xl">🟡</span>
              <div>
                <div className="font-bold">Últimos lugares</div>
                <div className="text-sm opacity-90">
                  Alto riesgo de llenarse pronto
                </div>
              </div>
            </div>
          </div>
        )}

        {/* BLOQUE 5: Fallback */}
        {zonaFallback && (
          <button
            onClick={() => setSelectedZone(zonaFallback)}
            className="w-full"
          >
            <ZonaCard
              zona={zonaFallback}
              tipo="fallback"
              distanciaTexto={`${zonaFallback.distancia_min} cuadras · ${Math.ceil(zonaFallback.distancia_min * 1.5)} min`}
              accionTexto={`Si está llena → ${zonaFallback.nombre}`}
            />
          </button>
        )}

        {/* BLOQUE 6: Advertencia */}
        <div className="bg-danger text-white rounded-xl p-4 shadow-md">
          <div className="flex items-center gap-2">
            <span className="text-xl">🔴</span>
            <div>
              <div className="font-bold">
                No estaciones en Zona Centro
              </div>
              <div className="text-sm opacity-90">
                Zona completamente llena
              </div>
            </div>
          </div>
        </div>

        {/* Botón Mapa */}
        <button
          onClick={() => setSelectedZone(zonaPrimaria)}
          className="w-full bg-primary text-white rounded-xl px-6 py-4 font-bold flex items-center justify-center gap-2 shadow-lg active:scale-95 transition-all"
        >
          <Map size={20} />
          Ver ruta en mapa
        </button>
      </div>

      {/* Bottom Sheet */}
      {selectedZone && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedZone(null)}
          />
          <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-50 max-w-md mx-auto shadow-2xl">
            <div
              className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4"
              onClick={() => setSelectedZone(null)}
            />

            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              Dirigite ahora a {selectedZone.nombre}
            </h3>

            <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1 mb-4">
              <p>🚶 {selectedZone.distancia_min * 1.5} min caminando</p>
              <p>📍 {selectedZone.referencia}</p>
              <p className="text-gray-400 dark:text-gray-500">
                {selectedZone.updatedAt ? formatUpdatedAt(selectedZone.updatedAt) : selectedZone.timestamp}
              </p>
            </div>

            {selectedZone.estado === 'alto' && (
              <div className="bg-warning/20 text-warning p-2 rounded-lg text-sm font-bold mb-4 text-center">
                ⚠️ Últimos lugares (alto riesgo)
              </div>
            )}

            <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
              {getConfianzaLabel(getConfianza(selectedZone.estado))}
            </p>

            {zonaFallback && selectedZone.id !== zonaFallback.id && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Si está llena →{' '}
                <span className="font-bold">{zonaFallback.nombre}</span>
              </p>
            )}

            <button
              onClick={() => abrirMapa(selectedZone)}
              className="w-full bg-primary text-white py-4 rounded-xl font-bold text-lg hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
            >
              <Map size={20} />
              Iniciar ruta
            </button>

            <button
              onClick={() => setSelectedZone(null)}
              className="w-full mt-3 py-2 text-gray-500 dark:text-gray-400 text-sm flex items-center justify-center gap-2"
            >
              <X size={16} />
              Cancelar
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default Estacionar;
