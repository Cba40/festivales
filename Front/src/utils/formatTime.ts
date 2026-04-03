export const formatUpdatedAt = (ts: number): string => {
  const diffMin = Math.floor((Date.now() - ts) / 60000)
  if (diffMin < 1) return 'Actualizado recién'
  if (diffMin < 60) return `Hace ${diffMin} min`
  return 'Datos estimados'
}
