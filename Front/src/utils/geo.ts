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
  puntoLat: number | null,
  puntoLng: number | null,
  userLoc: [number, number] | null,
  fallbackMin: number
) => {
  // `== null` en vez de truthiness: 0 es una coordenada válida (ecuador,
  // meridiano de Greenwich) y `!0` la tomaba por "sin dato".
  //
  // El `(0, 0)` explícito es compatibilidad, no semántica: 26 de los 27 call
  // sites del repo hacen `getDistancias(zona.lat ?? 0, zona.lng ?? 0, ...)`, o
  // sea que hoy `null` ya llega coercionado a 0. Sin esta rama, cambiar el guard
  // a `== null` haría que esas 26 llamadas con coordenadas ausentes diesen
  // Haversine contra Null Island. La salida es idéntica a la de hoy para esos
  // callers, y los que pasen el `null` real (Estacionar) ya salen bien.
  //
  // La única coordenada que esto sigue tratando como ausente es un (0, 0)
  // exacto, que no corresponde a ningún escenario del despliegue.
  if (!userLoc || puntoLat == null || puntoLng == null || (puntoLat === 0 && puntoLng === 0)) {
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
