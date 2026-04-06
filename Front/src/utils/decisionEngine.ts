type Estado = 'bajo' | 'medio' | 'alto' | 'colapsado'

const penalizacionEstado: Record<Estado, number> = {
  bajo: 0,
  medio: 5,
  alto: 15,
  colapsado: 30
}

export const calcularScore = (
  distancia: number,
  espera: number,
  estado: Estado
): number => {
  return distancia * 1.5 + espera * 2.5 + penalizacionEstado[estado]
}

export const getModo = (
  items: { estado: Estado; score: number }[],
  umbral: number
): 'sin_solucion' | 'guiar' | 'asistir' | 'informar' => {

  if (!items.length) return 'sin_solucion'

  const colapsadas = items.filter(i => i.estado === 'colapsado')
  const saturados = items.filter(i => i.estado === 'alto' || i.estado === 'colapsado')

  const mejor = items[0]

  if (mejor.score > umbral) return 'sin_solucion'
  if (colapsadas.length === items.length) return 'sin_solucion'
  if (saturados.length === items.length) return 'guiar'
  if (saturados.length > items.length / 2) return 'asistir'

  return 'informar'
}

export const getUmbralContexto = (hora: number): number => {
  if (hora >= 0 && hora <= 2) return 100
  if (hora >= 21 && hora <= 23) return 90
  return 80
}
