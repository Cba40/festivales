import 'leaflet/dist/leaflet.css'
import { MapContainer, TileLayer, Marker } from 'react-leaflet'
import L from 'leaflet'

const referenceIcon = L.divIcon({
  className: 'reference-marker-icon',
  html: `
    <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 border-2 border-white shadow-xl text-white font-bold text-sm">
      ★
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 32],
})

interface EventReferencePointMapProps {
  lat: number | null
  lng: number | null
}

export const EventReferencePointMap = ({ lat, lng }: EventReferencePointMapProps) => {
  if (lat == null || lng == null) {
    return (
      <div className="w-full bg-white dark:bg-slate-800 rounded-lg border border-slate-300 dark:border-slate-600 h-[250px] flex items-center justify-center">
        <p className="text-sm text-slate-500 dark:text-slate-300 italic">
          Guardá latitud y longitud para visualizar el punto de referencia operacional.
        </p>
      </div>
    )
  }

  const position: [number, number] = [lat, lng]

  return (
    <div className="w-full bg-white dark:bg-slate-800 rounded-lg border border-slate-300 dark:border-slate-600 aspect-[16/9] relative overflow-hidden shadow-sm h-[250px]">
      <MapContainer
        center={position}
        zoom={15}
        className="w-full h-full"
        scrollWheelZoom={false}
        dragging={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={position} icon={referenceIcon} />
      </MapContainer>
    </div>
  )
}