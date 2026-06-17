import { useAppStore } from '@/core/state/store'

/**
 * Retorna la ubicación GPS del usuario en tiempo real desde el store global.
 */
export function useUserLocation(): [number, number] | null {
  return useAppStore((s) => s.userLocation)
}
