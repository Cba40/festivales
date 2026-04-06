import { eventoData, PuntoPernoctar } from '@/data/eventoData'

export const getPernoctesOrdenados = (): PuntoPernoctar[] => {
  return [...eventoData.pernoctar].sort((a, b) => {
    const prioridad = {
      disponible: 0,
      consultar: 1,
      completo: 2
    }

    const aScore = prioridad[a.disponibilidad || 'consultar']
    const bScore = prioridad[b.disponibilidad || 'consultar']

    if (aScore !== bScore) return aScore - bScore

    return a.distancia_min - b.distancia_min
  })
}

export const getPernoctePrincipal = (): PuntoPernoctar | null => {
  const lista = getPernoctesOrdenados()
  return lista[0] || null
}
