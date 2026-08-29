export const ZONE_TYPES = [
  { value: 'estacionamiento', label: 'Estacionamiento' },
  { value: 'transporte', label: 'Transporte' },
  { value: 'comida', label: 'Comida' },
  { value: 'servicios', label: 'Servicios' },
  { value: 'salida', label: 'Salida' },
] as const;

// Modos canónicos de salida (contrato V1, migración c9d3e7f1a5b8 y filtro
// Literal del endpoint /products/exit): invariantes, NO provienen del
// catálogo zone_subtypes.
export const TRANSPORTE_OPTIONS: { value: string; label: string }[] = [
  { value: 'peatonal', label: 'Peatonal' },
  { value: 'vehicular', label: 'Vehicular' },
  { value: 'transporte', label: 'Transporte público' },
];

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
