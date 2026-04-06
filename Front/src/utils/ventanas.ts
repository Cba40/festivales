export const estaEnVentana = (
  hora: number,
  [inicio, fin]: [number, number]
): boolean => {
  if (inicio <= fin) return hora >= inicio && hora <= fin
  return hora >= inicio || hora <= fin
}
