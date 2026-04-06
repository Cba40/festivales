export const getHoraEvento = (): number => {
  // TEMP: fallback a hora del sistema
  // TODO: integrar con ResolverAhora (contexto real del evento)
  return new Date().getHours()
}
