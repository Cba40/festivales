import { Zona } from '../types';

const now = Date.now()

export const mockZones: Zona[] = [
  {
    id: 'zona-actual',
    nombre: 'Zona Centro',
    tipo: 'estacionamiento',
    distancia_min: 0,
    estado: 'colapsado',
    capacidad_estimada: 0,
    tendencia: 'estable',
    timestamp: 'actualizado hace 2 min',
    lat: -30.978107,
    lng: -64.094779,
    referencia: 'Plaza Principal / Iglesia',
    updatedAt: now - 2 * 60000
  },
  {
    id: 'zona-norte',
    nombre: 'Zona Norte',
    tipo: 'estacionamiento',
    distancia_min: 6,
    estado: 'alto',
    capacidad_estimada: 15,
    tendencia: 'subiendo',
    timestamp: 'actualizado hace 3 min',
    lat: -30.973313,
    lng: -64.088529,
    referencia: 'Barrio Norte / Terminal',
    updatedAt: now - 3 * 60000
  },
  {
    id: 'zona-oeste',
    nombre: 'Zona Oeste',
    tipo: 'estacionamiento',
    distancia_min: 8,
    estado: 'medio',
    capacidad_estimada: 45,
    tendencia: 'estable',
    timestamp: 'actualizado hace 5 min',
    lat: -30.981249,
    lng: -64.099398,
    referencia: 'Parque Autódromo',
    updatedAt: now - 5 * 60000
  },
  {
    id: 'zona-sur',
    nombre: 'Zona Sur',
    tipo: 'estacionamiento',
    distancia_min: 10,
    estado: 'bajo',
    capacidad_estimada: 120,
    tendencia: 'bajando',
    timestamp: 'actualizado hace 1 min',
    lat: -30.985337,
    lng: -64.094209,
    referencia: 'Predio Ferial / Costanera',
    updatedAt: now - 1 * 60000
  }
];

export const calcularScore = (zona: Zona): number => {
  const disponibilidadScore = {
    bajo: 100,
    medio: 60,
    alto: 20,
    colapsado: 0
  }[zona.estado];

  const tendenciaScore = {
    bajando: 20,
    estable: 0,
    subiendo: -10
  }[zona.tendencia];

  return (zona.distancia_min * -1) + disponibilidadScore + tendenciaScore;
};

export const getZonasOrdenadas = (): Zona[] => {
  return [...mockZones]
    .filter(z => z.id !== 'zona-actual')
    .sort((a, b) => calcularScore(b) - calcularScore(a));
};

export const getModoGuiar = (): boolean => {
  const horaActual = new Date().getHours();
  const zonasDisponibles = mockZones.filter(z => z.estado !== 'colapsado');
  const zonaActual = mockZones.find(z => z.id === 'zona-actual');

  return (
    zonaActual?.estado === 'colapsado' ||
    (horaActual >= 21 && horaActual <= 23) ||
    zonasDisponibles.length <= 1
  );
};
