import { Header } from '../components/Header';
import { ZonaCard } from '../components/ZonaCard';
import { Map } from 'lucide-react';
import { mockZones, getZonasOrdenadas, getModoGuiar } from '../data/mockZones';

interface EstacionarProps {
  onBack: () => void;
}

export const Estacionar = ({ onBack }: EstacionarProps) => {
  const modoGuiar = getModoGuiar();
  const zonasOrdenadas = getZonasOrdenadas();
  const zonaActual = mockZones.find((z) => z.id === 'zona-actual');

  const todasColapsadas = zonasOrdenadas.every((z) => z.estado === 'colapsado');

  if (!modoGuiar) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header title="Estacionar" showBack onBack={onBack} />

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-white rounded-xl p-4 shadow-md">
            <h2 className="text-lg font-bold text-gray-800 mb-4">
              Zonas disponibles
            </h2>
            <div className="space-y-3">
              {zonasOrdenadas.map((zona) => (
                <div key={zona.id} className="border-l-4 border-[#22c55e] pl-3">
                  <div className="font-semibold">{zona.nombre}</div>
                  <div className="text-sm text-gray-600">
                    {zona.distancia_min} cuadras · {zona.capacidad_estimada} lugares
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (todasColapsadas) {
    const zonaSur = zonasOrdenadas.find((z) => z.id === 'zona-sur') || zonasOrdenadas[0];

    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header title="Estacionar" showBack onBack={onBack} />

        <div className="bg-[#dc2626] text-white px-4 py-3">
          <h2 className="font-bold text-lg">Zonas cercanas completas</h2>
        </div>

        <div className="flex-1 p-4 space-y-4">
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <h3 className="font-bold text-gray-800 mb-4 text-lg">
              Estrategias disponibles:
            </h3>

            <div className="space-y-4">
              <div className="border-l-4 border-[#1e3a8a] pl-4">
                <div className="font-bold text-gray-900 mb-1">
                  Dirigite a {zonaSur.nombre}
                </div>
                <div className="text-sm text-gray-600">
                  {zonaSur.distancia_min} cuadras · Aproximadamente 20 min caminando
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {zonaSur.capacidad_estimada} lugares estimados disponibles
                </div>
              </div>

              <div className="border-l-4 border-[#f59e0b] pl-4">
                <div className="font-bold text-gray-900 mb-1">
                  Esperá 15-20 minutos
                </div>
                <div className="text-sm text-gray-600">
                  Las zonas cercanas podrían liberar lugares
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Media probabilidad · Verificá nuevamente en unos minutos
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={() => alert('Mostrando mapa...')}
            className="w-full bg-[#1e3a8a] text-white rounded-xl px-6 py-4 font-bold flex items-center justify-center gap-2 shadow-lg active:scale-95 transition-all"
          >
            <Map size={20} />
            Ver mapa general
          </button>
        </div>
      </div>
    );
  }

  const zonaPrimaria = zonasOrdenadas[0];
  const zonaFallback = zonasOrdenadas[1];
  const distanciaPrimaria = zonaPrimaria.distancia_min;
  const tiempoPrimaria = Math.ceil(distanciaPrimaria * 1.5);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header title="Estacionar - Modo Guiar" showBack onBack={onBack} />

      <div className="flex-1 p-4 space-y-3">
        {zonaActual && (
          <ZonaCard
            zona={zonaActual}
            tipo="completa"
            accionTexto="Zona actual COMPLETA"
          />
        )}

        <ZonaCard
          zona={zonaPrimaria}
          tipo="primaria"
          distanciaTexto={`${distanciaPrimaria} cuadras`}
          accionTexto={`Dirigite ahora a ${zonaPrimaria.nombre}`}
        />

        <div className="bg-white rounded-xl p-4 shadow-md border-l-4 border-[#22c55e]">
          <div className="flex items-center gap-2 text-gray-800">
            <span className="text-xl">⏱</span>
            <span className="font-bold">{tiempoPrimaria} min caminando (estimado)</span>
          </div>
        </div>

        {zonaPrimaria.estado === 'alto' && (
          <div className="bg-[#f59e0b] text-white rounded-xl p-4 shadow-md">
            <div className="flex items-center gap-2">
              <span className="text-xl">🟡</span>
              <div>
                <div className="font-bold">Últimos lugares</div>
                <div className="text-sm opacity-90">Alto riesgo de llenarse pronto</div>
              </div>
            </div>
          </div>
        )}

        {zonaFallback && (
          <ZonaCard
            zona={zonaFallback}
            tipo="fallback"
            distanciaTexto={`${zonaFallback.distancia_min} cuadras · ${Math.ceil(zonaFallback.distancia_min * 1.5)} min`}
            accionTexto={`Si está llena → ${zonaFallback.nombre}`}
          />
        )}

        <div className="bg-[#dc2626] text-white rounded-xl p-4 shadow-md">
          <div className="flex items-center gap-2">
            <span className="text-xl">🔴</span>
            <div>
              <div className="font-bold">No estaciones en Zona Centro</div>
              <div className="text-sm opacity-90">Zona completamente llena</div>
            </div>
          </div>
        </div>

        <button
          onClick={() => alert('Mostrando ruta en mapa...')}
          className="w-full bg-[#1e3a8a] text-white rounded-xl px-6 py-4 font-bold flex items-center justify-center gap-2 shadow-lg active:scale-95 transition-all"
        >
          <Map size={20} />
          Ver ruta en mapa
        </button>
      </div>
    </div>
  );
};
