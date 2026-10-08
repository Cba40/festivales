/**
 * Clave de caché sensible a la posición del usuario.
 *
 * La posición del usuario ordena y puntúa las respuestas de todos los productos
 * (`/products/*` → `MobilityContext` en el backend). Por eso la clave de caché
 * tiene que incluir las coordenadas: con una clave por producto solamente, dos
 * requests del mismo evento desde lugares distintos comparten entrada y el
 * segundo muestra el ranking del primero.
 *
 * El redondeo a 4 decimales (~11 m) evita que el ruido del GPS genere una
 * entrada distinta en cada lectura. `'none'` distingue "sin coordenada" de una
 * coordenada 0 válida, que en Argentina es una latitud legítima.
 *
 * Nació duplicado en `parkingProduct.ts` y `emergencyProduct.ts`, que dejaban
 * escrito que el tercer consumidor lo movería acá. Ese momento fue este.
 */
export function coordCachePart(value?: number | null): string {
  return value == null ? 'none' : value.toFixed(4)
}

/**
 * Sufijo de clave con ambas coordenadas, listo para concatenar.
 *
 * Devuelve cadena vacía cuando no hay posición, para que las claves de quien
 * nunca dio GPS no cambien de forma respecto a las que ya existían.
 */
export function coordsCacheSuffix(
  lat?: number | null,
  lng?: number | null,
): string {
  if (lat == null || lng == null) return ''
  return `${coordCachePart(lat)}|${coordCachePart(lng)}`
}