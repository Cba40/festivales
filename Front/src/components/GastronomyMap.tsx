import 'leaflet/dist/leaflet.css'
import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, useMap } from 'react-leaflet'
import { X, Map } from 'lucide-react'
import type { PuntoComida } from '@/data/mappers'

const URBAN_FACTOR = 1.3

const haversine = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

const calcWalkingDist = (lat1: number, lng1: number, lat2: number, lng2: number): string => {
  const km = haversine(lat1, lng1, lat2, lng2)
  const kmUrban = km * URBAN_FACTOR
  const min = Math.round((kmUrban / 5) * 60)
  return min < 1 ? '< 1 min' : `${min} min`
}

const UserLocationMarker = () => {
  const map = useMap()
  const [pos, setPos] = useState<[number, number] | null>(null)

  useEffect(() => {
    if (!navigator.geolocation) return
    const id = navigator.geolocation.watchPosition(
      (p) => {
        const pt: [number, number] = [p.coords.latitude, p.coords.longitude]
        setPos(pt)
      },
      () => {},
      { enableHighAccuracy: true, timeout: 10000 }
    )
    return () => navigator.geolocation.clearWatch(id)
  }, [map])

  if (!pos) return null

  return (
    <CircleMarker
      center={pos}
      radius={8}
      pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.8, weight: 3 }}
    />
  )
}

interface Props {
  puntos: PuntoComida[]
  userLocation?: [number, number] | null
}

const GastronomyMap = ({ puntos, userLocation }: Props) => {
  const [selectedPunto, setSelectedPunto] = useState<PuntoComida | null>(null)

  useEffect(() => {
    console.log('[GastronomyMap] puntos:', puntos)
    puntos.forEach((p, i) => console.log(`[GastronomyMap] punto[${i}]:`, { nombre: p.nombre, geometryType: p.geometryType, coordinates: p.coordinates, lat: p.lat, lng: p.lng }))
  }, [puntos])

  const calcCenter = (): [number, number] => {
    if (userLocation) return userLocation
    if (puntos.length === 0) return [-30.975, -64.090]
    let latSum = 0, lngSum = 0, count = 0
    puntos.forEach(p => {
      if (p.lat !== 0 && p.lng !== 0) { latSum += p.lat; lngSum += p.lng; count++ }
    })
    if (count === 0) return [-30.975, -64.090]
    return [latSum / count, lngSum / count]
  }

  const center: [number, number] = calcCenter()

  const getColor = (estado: string): string => {
    switch (estado) {
      case 'bajo': return '#22c55e'
      case 'medio': return '#eab308'
      case 'alto': return '#ef4444'
      default: return '#6b7280'
    }
  }

  const getDestCoords = (p: PuntoComida): [number, number] | null => {
    if (p.geometryType === 'line') {
      const c = p.coordinates as [number, number][]
      if (Array.isArray(c[0]) && typeof c[0][0] === 'number' && typeof c[0][1] === 'number') return [c[0][0], c[0][1]]
    }
    const c = p.coordinates as [number, number]
    if (typeof c[0] === 'number' && typeof c[1] === 'number') return [c[0], c[1]]
    if (p.lat && p.lng) return [p.lat, p.lng]
    return null
  }

  const getCategoriaLabel = (cat: string) => {
    switch (cat) {
      case 'rapido': return 'Comida rápida'
      case 'comida': return 'Comida completa'
      case 'bebida': return 'Bebidas'
      default: return cat
    }
  }

  return (
    <>
      <MapContainer
        center={center}
        zoom={15}
        className="w-full h-full rounded-xl"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <UserLocationMarker />

        {puntos.map((p) => {
          if (p.geometryType === 'line') {
            const coords = p.coordinates as [number, number][]
            return (
              <Polyline
                key={p.id}
                positions={coords}
                pathOptions={{ color: getColor(p.estado), weight: 4, opacity: 0.8 }}
                eventHandlers={{ click: () => setSelectedPunto(p) }}
              />
            )
          }

          const coords = p.coordinates as [number, number]
          return (
            <CircleMarker
              key={p.id}
              center={coords}
              radius={10}
              pathOptions={{ color: getColor(p.estado), fillColor: getColor(p.estado), fillOpacity: 0.6, weight: 2 }}
              eventHandlers={{ click: () => setSelectedPunto(p) }}
            />
          )
        })}
      </MapContainer>

      {selectedPunto && (() => {
        const dest = getDestCoords(selectedPunto)
        const gmapsUrl = dest ? `https://www.google.com/maps/dir/?api=1&destination=${dest[0]},${dest[1]}` : '#'
        return (
          <>
            <div className="fixed inset-0 bg-black/50 z-[9999]" onClick={() => setSelectedPunto(null)} />
            <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
              <div
                className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
                onClick={() => setSelectedPunto(null)}
              />

              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
                {selectedPunto.nombre}
              </h3>

              <div className="space-y-2 mb-4">
                <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
                  <span className="font-semibold">{getCategoriaLabel(selectedPunto.categoria)}</span>
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  📍 {selectedPunto.referencia}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  🚶 {selectedPunto.distancia_min} min · ⏱️ {selectedPunto.espera_min} min
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-300">
                  {new Date(selectedPunto.updatedAt).toLocaleString()}
                </p>
              </div>

              {dest && (
                <a
                  href={gmapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center gap-2 bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95"
                >
                  <Map size={20} />
                  Iniciar ruta
                </a>
              )}

              <button
                onClick={() => setSelectedPunto(null)}
                className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95 flex items-center justify-center gap-2"
              >
                <X size={16} />
                Cerrar
              </button>
            </div>
          </>
        )
      })()}
    </>
  )
}

export default GastronomyMap
