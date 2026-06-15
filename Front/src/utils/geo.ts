// Lógica de cálculo geográfico Haversine y tiempos de viaje (caminando y auto)

export const URBAN_FACTOR = 1.3

export const haversine = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
  const R = 6371 // Radio de la Tierra en km
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

export const getDistancias = (
  puntoLat: number,
  puntoLng: number,
  userLoc: [number, number] | null,
  fallbackMin: number
) => {
  if (!userLoc || !puntoLat || !puntoLng) {
    return {
      walking: `${fallbackMin} min`,
      driving: `${Math.max(1, Math.round(fallbackMin / 3))} min`
    }
  }

  const [userLat, userLng] = userLoc
  const km = haversine(userLat, userLng, puntoLat, puntoLng)

  // Caminando: ~5 km/h promedio en entorno urbano/congestionado
  const kmWalking = km * URBAN_FACTOR
  const minWalking = Math.round((kmWalking / 5) * 60)
  const walkingStr = minWalking < 1 ? '< 1 min' : `${minWalking} min`

  // En auto: ~25 km/h promedio en zona del festival
  const kmDriving = km * 1.5
  const minDriving = Math.round((kmDriving / 25) * 60)
  const drivingStr = minDriving < 1 ? '< 1 min' : `${minDriving} min`

  return { walking: walkingStr, driving: drivingStr }
}
