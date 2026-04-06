import { fases, type FaseEvento } from '@/config/eventoConfig'
import { estaEnVentana } from './ventanas'

export const getFaseActual = (hora: number): FaseEvento | null => {
  const activas = fases.filter(f => estaEnVentana(hora, f.rango))
  if (!activas.length) return null
  return activas[0]
}
