import { ZonaSalida } from '../data/mockSalidas'

export const getTipoRecomendado = (
  zonas: ZonaSalida[]
): 'auto' | 'transporte' | 'peatonal' => {
  const autoOk = zonas.filter(z => z.tipo === 'auto' && z.estado !== 'colapsado').length
  const transporteOk = zonas.filter(z => z.tipo === 'transporte' && z.estado !== 'colapsado').length
  const peatonalOk = zonas.filter(z => z.tipo === 'peatonal' && z.estado !== 'colapsado').length

  if (autoOk === 0) return 'peatonal'
  if (transporteOk === 0 && peatonalOk > 0) return 'peatonal'
  return 'auto'
}
