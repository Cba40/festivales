export const getConfianza = (
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
): 'alta' | 'media' | 'baja' => {
  if (estado === 'bajo') return 'alta'
  if (estado === 'medio') return 'media'
  return 'baja'
}

export const getConfianzaLabel = (
  confianza: 'alta' | 'media' | 'baja'
): string => {
  if (confianza === 'alta') return '✅ Alta probabilidad'
  if (confianza === 'media') return '⚠️ Últimos lugares'
  return '❗ Disponibilidad incierta'
}
