export const getTipoLabel = (tipo: string): string => {
  switch (tipo) {
    case 'peñas': return 'Peñas'
    case 'comida_rapida': return 'Comida Rápida'
    case 'parrillas': return 'Parrillas'
    case 'food_trucks': return 'Food Trucks'
    case 'mixto': return 'Mixto'
    default: return tipo
  }
}

export const getSentarseLabel = (posibilidad: string): string => {
  switch (posibilidad) {
    case 'alta': return '🟢 Fácil encontrar lugar'
    case 'media': return '🟡 Moderadamente disponible'
    case 'baja': return '🔴 Muy concurrido'
    default: return posibilidad
  }
}
