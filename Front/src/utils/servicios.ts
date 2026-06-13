import { type PuntoServicio } from '@/data/mappers'

export const getServiciosPorSubtipo = (servicios: PuntoServicio[], subtipo: string) => {
  return servicios
    .filter(s => s.subtipo === subtipo)
    .sort((a, b) => a.distancia_min - b.distancia_min)
}

export const getServicioMasCercano = (servicios: PuntoServicio[], subtipo: string) => {
  const filtrados = getServiciosPorSubtipo(servicios, subtipo)
  return filtrados[0] || null
}

export const getSegundoMasCercano = (servicios: PuntoServicio[], subtipo: string) => {
  const filtrados = getServiciosPorSubtipo(servicios, subtipo)
  return filtrados[1] || null
}
