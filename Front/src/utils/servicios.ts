import { eventoData } from '@/data/eventoData'

export const getServiciosPorSubtipo = (subtipo: string) => {
  return eventoData.servicios
    .filter(s => s.subtipo === subtipo)
    .sort((a, b) => a.distancia_min - b.distancia_min)
}

export const getServicioMasCercano = (subtipo: string) => {
  const filtrados = getServiciosPorSubtipo(subtipo)
  return filtrados[0] || null
}

export const getSegundoMasCercano = (subtipo: string) => {
  const filtrados = getServiciosPorSubtipo(subtipo)
  return filtrados[1] || null
}
