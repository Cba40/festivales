import { calcularScore, getModo, getUmbralContexto } from '../utils/decisionEngine'
import { getHoraEvento } from '@/utils/contextoEvento'

export interface PuntoComida {
  id: string
  nombre: string
  tipo: 'rapido' | 'comida' | 'bebida'
  distancia_min: number
  espera_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  referencia: string
  lat: number
  lng: number
  updatedAt: number
}

export const puntosComida: PuntoComida[] = [
  {
    id: 'c1',
    nombre: 'Puesto Norte',
    tipo: 'rapido',
    distancia_min: 6,
    espera_min: 10,
    estado: 'bajo',
    referencia: 'Frente a la plaza secundaria',
    lat: -30.9733,
    lng: -64.0885,
    updatedAt: Date.now() - 2 * 60000
  },
  {
    id: 'c2',
    nombre: 'Zona Gastronómica Central',
    tipo: 'comida',
    distancia_min: 3,
    espera_min: 25,
    estado: 'alto',
    referencia: 'Predio principal',
    lat: -30.9781,
    lng: -64.0947,
    updatedAt: Date.now() - 1 * 60000
  },
  {
    id: 'c3',
    nombre: 'Puesto Oeste',
    tipo: 'rapido',
    distancia_min: 8,
    espera_min: 12,
    estado: 'medio',
    referencia: 'Parque Autódromo',
    lat: -30.9812,
    lng: -64.0993,
    updatedAt: Date.now() - 3 * 60000
  }
]

export const getComidaOrdenada = (puntos: PuntoComida[]) => {
  return [...puntos].sort((a, b) => {
    const scoreA = calcularScore(a.distancia_min, a.espera_min, a.estado)
    const scoreB = calcularScore(b.distancia_min, b.espera_min, b.estado)
    return scoreA - scoreB
  })
}

export const getModoComer = (puntos: PuntoComida[]): 'sin_solucion' | 'guiar' | 'asistir' | 'informar' => {
  const puntosOrdenados = getComidaOrdenada(puntos)
  const items = puntosOrdenados.map(p => ({
    estado: p.estado,
    score: calcularScore(p.distancia_min, p.espera_min, p.estado)
  }))

  const horaActual = getHoraEvento()
  const umbral = getUmbralContexto(horaActual)

  return getModo(items, umbral + 10)
}

export const todasColapsadas = (puntos: PuntoComida[]) =>
  puntos.every(p => p.estado === 'colapsado')

export const todasSaturadas = (puntos: PuntoComida[]) =>
  puntos.every(p => p.estado === 'alto' || p.estado === 'colapsado')
