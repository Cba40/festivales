import { useState, useEffect } from 'react'

/**
 * Rastrea la ubicación GPS del usuario en tiempo real.
 * Se activa al montar el componente y actualiza continuamente.
 * No requiere que el mapa esté visible.
 */
export function useUserLocation(): [number, number] | null {
  const [location, setLocation] = useState<[number, number] | null>(null)

  useEffect(() => {
    if (!navigator.geolocation) return

    const id = navigator.geolocation.watchPosition(
      (pos) => {
        setLocation([pos.coords.latitude, pos.coords.longitude])
      },
      (err) => {
        console.warn('[useUserLocation] Error GPS:', err.message)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
    )

    return () => navigator.geolocation.clearWatch(id)
  }, [])

  return location
}
