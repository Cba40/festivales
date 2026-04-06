import { calcularScore, getModo, getUmbralContexto } from '../utils/decisionEngine'
import { getHoraEvento } from '@/utils/contextoEvento'

export interface ParadaTransporte {
  id: string
  nombre: string
  distancia_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  espera_min: number
  referencia: string
  calle: string
  lat: number
  lng: number
  updatedAt: number
}

export const paradas: ParadaTransporte[] = [
  {
    id: '1',
    nombre: 'Terminal Principal',
    distancia_min: 5,
    estado: 'alto',
    espera_min: 20,
    referencia: 'Frente a la Plaza',
    calle: 'Av. San Martín',
    lat: -30.9785,
    lng: -64.0950,
    updatedAt: Date.now() - 2 * 60000
  },
  {
    id: '2',
    nombre: 'Parada Secundaria',
    distancia_min: 8,
    estado: 'bajo',
    espera_min: 10,
    referencia: 'Esquina Av. Colón',
    calle: 'Av. Colón',
    lat: -30.9810,
    lng: -64.0890,
    updatedAt: Date.now() - 1 * 60000
  },
  {
    id: '3',
    nombre: 'Parada Norte',
    distancia_min: 12,
    estado: 'medio',
    espera_min: 15,
    referencia: 'Terminal de Ómnibus',
    calle: 'Ruta 9',
    lat: -30.9733,
    lng: -64.0885,
    updatedAt: Date.now() - 3 * 60000
  }
]

export const getParadasOrdenadas = (paradas: ParadaTransporte[]) => {
  return [...paradas].sort((a, b) => {
    const scoreA = calcularScore(a.distancia_min, a.espera_min, a.estado)
    const scoreB = calcularScore(b.distancia_min, b.espera_min, b.estado)
    return scoreA - scoreB
  })
}

export const getModoTransporte = (paradas: ParadaTransporte[]): 'sin_solucion' | 'guiar' | 'asistir' | 'informar' => {
  const paradasOrdenadas = getParadasOrdenadas(paradas)
  const items = paradasOrdenadas.map(p => ({
    estado: p.estado,
    score: calcularScore(p.distancia_min, p.espera_min, p.estado)
  }))

  const horaActual = getHoraEvento()
  const umbral = getUmbralContexto(horaActual)

  return getModo(items, umbral)
}

export const todasColapsadas = (paradas: ParadaTransporte[]) =>
  paradas.every(p => p.estado === 'colapsado')
