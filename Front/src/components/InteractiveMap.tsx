import 'leaflet/dist/leaflet.css'
import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useAppStore } from '@/core/state/store'

// Icono para la ubicación del usuario en tiempo real
const userIcon = L.divIcon({
  className: 'user-location-icon',
  html: `
    <div class="relative flex items-center justify-center w-6 h-6">
      <div class="absolute w-full h-full rounded-full bg-blue-500 opacity-40 animate-ping"></div>
      <div class="relative w-4 h-4 rounded-full bg-blue-600 border-2 border-white shadow-md"></div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

const UserLocationMarker = ({ onLocationUpdate }: { onLocationUpdate: (pos: [number, number]) => void }) => {
  const map = useMap()
  const storeLocation = useAppStore(s => s.userLocation)

  useEffect(() => {
    if (storeLocation) {
      onLocationUpdate(storeLocation)
      map.flyTo(storeLocation, map.getZoom())
    }
  }, [storeLocation, map, onLocationUpdate])

  if (!storeLocation) return null

  return <Marker position={storeLocation} icon={userIcon} />
}

export interface InteractiveMapPoint {
  id: string
  tipo: string // 'banos', 'hidratacion', 'descanso', 'salud', 'estacionamiento', 'transporte', 'salida', 'hospedaje', 'emergencia', 'comer', etc.
  nombre: string
  lat: number
  lng: number
  referencia: string
  distancia?: number
  updatedAt?: number
  originalData?: any // Objeto original
}

interface InteractiveMapProps {
  puntos: InteractiveMapPoint[]
  onSelectPunto: (punto: any) => void
  onUserLocationUpdate?: (pos: [number, number]) => void
}

export const InteractiveMap = ({ puntos, onSelectPunto, onUserLocationUpdate }: InteractiveMapProps) => {
  const getIcon = (tipo: string) => {
    let emoji = '📍'
    let color = 'bg-gray-500 shadow-gray-500/50'

    switch (tipo) {
      case 'banos':
        emoji = '🚻'
        color = 'bg-blue-500 shadow-blue-500/50'
        break
      case 'hidratacion':
        emoji = '💧'
        color = 'bg-cyan-500 shadow-cyan-500/50'
        break
      case 'descanso':
        emoji = '🪑'
        color = 'bg-purple-500 shadow-purple-500/50'
        break
      case 'salud':
      case 'emergencia':
        emoji = '🏥'
        color = 'bg-red-500 shadow-red-500/50'
        break
      case 'estacionamiento':
        emoji = '🚗'
        color = 'bg-green-600 shadow-green-600/50'
        break
      case 'transporte':
        emoji = '🚌'
        color = 'bg-blue-600 shadow-blue-600/50'
        break
      case 'salida':
        emoji = '🚪'
        color = 'bg-amber-500 shadow-amber-500/50'
        break
      case 'hospedaje':
      case 'pernoctar':
        emoji = '🏨'
        color = 'bg-indigo-600 shadow-indigo-600/50'
        break
      case 'comer':
        emoji = '🍔'
        color = 'bg-orange-500 shadow-orange-500/50'
        break
    }

    return L.divIcon({
      className: 'custom-service-icon',
      html: `
        <div class="relative w-9 h-9 rounded-full ${color} shadow-lg border-2 border-white dark:border-slate-800 flex items-center justify-center text-base font-bold text-white transition-transform hover:scale-110 active:scale-95 cursor-pointer">
          ${emoji}
        </div>
      `,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    })
  }

  const calcCenter = (): [number, number] => {
    const validPoints = puntos.filter((p) => p.lat !== 0 && p.lng !== 0)
    if (validPoints.length === 0) return [-30.975, -64.090] // Centro por defecto (Jesús María)
    
    let latSum = 0
    let lngSum = 0
    validPoints.forEach((p) => {
      latSum += p.lat
      lngSum += p.lng
    })
    return [latSum / validPoints.length, lngSum / validPoints.length]
  }

  const center = calcCenter()

  return (
    <div className="w-full bg-white dark:bg-slate-800 rounded-xl border-2 border-slate-200 dark:border-slate-700 aspect-square relative overflow-hidden shadow-md h-[380px] md:h-[450px]">
      <MapContainer
        center={center}
        zoom={15}
        className="w-full h-full"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <UserLocationMarker onLocationUpdate={(pt) => onUserLocationUpdate?.(pt)} />

        {puntos.map((punto) => {
          if (!punto.lat || !punto.lng) return null
          return (
            <Marker
              key={punto.id}
              position={[punto.lat, punto.lng]}
              icon={getIcon(punto.tipo)}
              eventHandlers={{
                click: () => onSelectPunto(punto.originalData || punto),
              }}
            />
          )
        })}
      </MapContainer>
    </div>
  )
}
