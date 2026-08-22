export const ZONE_TYPES = [
  { value: 'estacionamiento', label: 'Estacionamiento' },
  { value: 'transporte', label: 'Transporte' },
  { value: 'comida', label: 'Comida' },
  { value: 'servicios', label: 'Servicios' },
  { value: 'emergencia', label: 'Emergencia' },
  { value: 'salida', label: 'Salida' },
  { value: 'hospedaje', label: 'Hospedaje' },
] as const;

// Permanencias sugeridas por subtipo (minutos) para precargar el campo
// "Permanencia (min)" cuando aún no existe una fila en service_configs.
export const DEFAULTS_POR_SUBTIPO: Record<string, number> = {
  banos: 5,
  hidratacion: 3,
  descanso: 15,
  salud: 10,
  foodtruck: 20,
  comida_al_paso: 15,
  penas: 45,
  patio_de_comidas: 30,
  restaurante: 60,
};
