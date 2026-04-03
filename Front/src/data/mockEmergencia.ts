export interface PuntoSeguro {
  id: string
  nombre: string
  lat: number
  lng: number
  direccion: string
  referencia: string
  distancia_min: number
  horario: string
  telefono: string
  updatedAt: number
}

export interface PuestoSanitario {
  id: string
  nombre: string
  lat: number
  lng: number
  direccion: string
  referencia: string
  distancia_min: number
  horario: string
  telefono: string
  servicios: string[]
  updatedAt: number
}

const now = Date.now()

export const puntosSeguros: PuntoSeguro[] = [
  {
    id: 'punto-1',
    nombre: 'Destacamento Policial',
    lat: -30.9785,
    lng: -64.0950,
    direccion: 'Av. Vélez Sarsfield 1200',
    referencia: 'Frente a la Plaza Central',
    distancia_min: 2,
    horario: '24hs',
    telefono: '+543511234567',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'punto-2',
    nombre: 'Puesto de Salud Municipal',
    lat: -30.9801,
    lng: -64.0935,
    direccion: 'Córdoba 450',
    referencia: 'Al lado del Hospital Zonal',
    distancia_min: 4,
    horario: '24hs',
    telefono: '+543517654321',
    updatedAt: now - 4 * 60000
  },
  {
    id: 'punto-3',
    nombre: 'Oficina de Información',
    lat: -30.9770,
    lng: -64.0965,
    direccion: 'Av. Libertador 890',
    referencia: 'Entrada principal del predio ferial',
    distancia_min: 3,
    horario: '18:00 - 04:00',
    telefono: '+543519876543',
    updatedAt: now - 3 * 60000
  }
]

export const puestosSanitarios: PuestoSanitario[] = [
  {
    id: 'puesto-1',
    nombre: 'Puesto Sanitario Principal',
    lat: -30.9785,
    lng: -64.0955,
    direccion: 'Av. Vélez Sarsfield 1150',
    referencia: 'Costado este de la Plaza',
    distancia_min: 3,
    horario: '24hs durante el evento',
    telefono: '+543511234567',
    servicios: ['Primeros auxilios', 'Ambulatorio', 'Ambulancia'],
    updatedAt: now - 1 * 60000
  },
  {
    id: 'puesto-2',
    nombre: 'Posta Médica Norte',
    lat: -30.9740,
    lng: -64.0890,
    direccion: 'Terminal de Ómnibus',
    referencia: 'Planta baja',
    distancia_min: 5,
    horario: '24hs',
    telefono: '+543511234568',
    servicios: ['Primeros auxilios', 'Ambulatorio'],
    updatedAt: now - 5 * 60000
  }
]

export function getPuntoSeguroCercano(): PuntoSeguro {
  return puntosSeguros[0]
}

export function getPuestoCercano(): PuestoSanitario {
  return puestosSanitarios[0]
}

export interface ZonaReferencia {
  nombre: string
  salidaCercana: string
  distanciaSalida: number
  zonaTranquila: string
  distanciaTranquila: number
}

export const zonasReferencia: ZonaReferencia = {
  nombre: 'Zona Centro',
  salidaCercana: 'Av. Vélez Sarsfield',
  distanciaSalida: 3,
  zonaTranquila: 'Plaza Principal',
  distanciaTranquila: 5
}
