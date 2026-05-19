/**
 * Mock data para servicios con posicionamiento 2D
 * Estructura preparada para futura integración con BD
 * 
 * x, y: valores 0-100 (escala relativa del evento)
 * distancia: minutos caminando
 */

export interface PuntoServicioMapa {
  id: string
  tipo: 'banos' | 'hidratacion' | 'descanso' | 'salud'
  nombre: string
  x: number        // 0-100 (posición horizontal)
  y: number        // 0-100 (posición vertical)
  distancia: number // minutos
  referencia: string
  updatedAt: number
}

const now = Date.now()

export const serviciosMapMock: PuntoServicioMapa[] = [
  // ===== BAÑOS =====
  {
    id: 'svc-b1',
    tipo: 'banos',
    nombre: 'Baños Norte',
    x: 25,
    y: 20,
    distancia: 2,
    referencia: 'Junto a entrada principal',
    updatedAt: now - 5 * 60000
  },
  {
    id: 'svc-b2',
    nombre: 'Baños Sur',
    tipo: 'banos',
    x: 65,
    y: 80,
    distancia: 5,
    referencia: 'Cerca de escenario',
    updatedAt: now - 3 * 60000
  },
  
  // ===== HIDRATACIÓN =====
  {
    id: 'svc-h1',
    tipo: 'hidratacion',
    nombre: 'Punto de Agua Central',
    x: 50,
    y: 40,
    distancia: 1,
    referencia: 'Plaza principal',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'svc-h2',
    tipo: 'hidratacion',
    nombre: 'Fuente Lateral',
    x: 35,
    y: 60,
    distancia: 3,
    referencia: 'Zona gastronómica',
    updatedAt: now - 4 * 60000
  },
  
  // ===== DESCANSO =====
  {
    id: 'svc-d1',
    tipo: 'descanso',
    nombre: 'Zona Sombría',
    x: 75,
    y: 55,
    distancia: 4,
    referencia: 'Área verde con bancos',
    updatedAt: now - 6 * 60000
  },
  {
    id: 'svc-d2',
    tipo: 'descanso',
    nombre: 'Plaza de Descanso',
    x: 40,
    y: 30,
    distancia: 6,
    referencia: 'Con sombra y mesas',
    updatedAt: now - 8 * 60000
  },
  
  // ===== SALUD =====
  {
    id: 'svc-s1',
    tipo: 'salud',
    nombre: 'Primeros Auxilios',
    x: 45,
    y: 65,
    distancia: 3,
    referencia: 'Módulo médico',
    updatedAt: now - 1 * 60000
  },
  {
    id: 'svc-s2',
    tipo: 'salud',
    nombre: 'Punto de Ayuda',
    x: 70,
    y: 25,
    distancia: 7,
    referencia: 'Asistencia básica',
    updatedAt: now - 2 * 60000
  }
]

export const getServiciosMapPorTipo = (tipo: 'banos' | 'hidratacion' | 'descanso' | 'salud'): PuntoServicioMapa[] => {
  return serviciosMapMock
    .filter(s => s.tipo === tipo)
    .sort((a, b) => a.distancia - b.distancia)
}

export const getServicioMapPorId = (id: string): PuntoServicioMapa | null => {
  return serviciosMapMock.find(s => s.id === id) || null
}
