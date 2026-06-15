import 'leaflet/dist/leaflet.css'
import { useState, useMemo, useRef, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'

// Icono personalizado para el marcador del administrador
const adminIcon = L.divIcon({
  className: 'admin-marker-icon',
  html: `
    <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-red-600 border-2 border-white shadow-xl flex items-center justify-center text-white font-bold text-sm cursor-move animate-bounce">
      📍
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 32],
})

// Componente para escuchar clics en el mapa y reubicar el marcador
interface MapEventsProps {
  onMapClick: (lat: number, lng: number) => void
}

const MapEventsHandler = ({ onMapClick }: MapEventsProps) => {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

interface AdminMapSelectorProps {
  lat?: number
  lng?: number
  onChangeLocation: (lat: number, lng: number) => void
}

export const AdminMapSelector = ({ lat, lng, onChangeLocation }: AdminMapSelectorProps) => {
  // Coordenadas por defecto (Jesús María)
  const defaultLat = -30.975
  const defaultLng = -64.090

  const [position, setPosition] = useState<[number, number]>([
    lat || defaultLat,
    lng || defaultLng,
  ])

  // Sincronizar posición si cambian los props externos
  useEffect(() => {
    if (lat && lng && (lat !== position[0] || lng !== position[1])) {
      setPosition([lat, lng])
    }
  }, [lat, lng])

  const markerRef = useRef<L.Marker | null>(null)

  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current
        if (marker != null) {
          const latLng = marker.getLatLng()
          setPosition([latLng.lat, latLng.lng])
          onChangeLocation(latLng.lat, latLng.lng)
        }
      },
    }),
    [onChangeLocation]
  )

  const handleMapClick = (clickLat: number, clickLng: number) => {
    setPosition([clickLat, clickLng])
    onChangeLocation(clickLat, clickLng)
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500 dark:text-slate-300 font-medium">
        📍 Hacé click en cualquier lugar del mapa o arrastrá el marcador para fijar las coordenadas exactas:
      </p>
      
      <div className="w-full bg-white dark:bg-slate-800 rounded-lg border border-slate-300 dark:border-slate-600 aspect-[16/9] relative overflow-hidden shadow-sm h-[250px]">
        <MapContainer
          center={position}
          zoom={15}
          className="w-full h-full"
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapEventsHandler onMapClick={handleMapClick} />

          <Marker
            draggable={true}
            eventHandlers={eventHandlers}
            position={position}
            icon={adminIcon}
            ref={markerRef}
          />
        </MapContainer>
      </div>

      <div className="flex gap-4 text-xs text-slate-600 dark:text-slate-300">
        <div>
          <span className="font-semibold text-slate-700 dark:text-slate-200">Latitud:</span> {position[0].toFixed(6)}
        </div>
        <div>
          <span className="font-semibold text-slate-700 dark:text-slate-200">Longitud:</span> {position[1].toFixed(6)}
        </div>
      </div>
    </div>
  )
}
