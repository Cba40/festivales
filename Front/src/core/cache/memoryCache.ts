type CacheEntry<T> = {
  data: T
  expiresAt: number
}

export const ZONES_TTL_MS = 60_000
export const EVENT_DAY_TTL_MS = 60_000
export const PREDICTION_TTL_MS = 15_000
export const PRODUCT_TTL_MS = 30_000

const cache = new Map<string, CacheEntry<unknown>>()

function normalizeEventId(eventId: string): string {
  return eventId || 'default-event-id'
}

export function zoneCacheKey(eventId: string): string {
  return `zones:${normalizeEventId(eventId)}`
}

export function eventDayTodayCacheKey(eventId: string): string {
  return `event-day-today:${normalizeEventId(eventId)}`
}

export function predictionCacheKey(eventId: string): string {
  return `predictions:${normalizeEventId(eventId)}`
}

export function productCacheKey(
  eventId: string,
  productType: string,
): string {
  return `product:${normalizeEventId(eventId)}:${productType}`
}

function getStale<T>(key: string): T | undefined {
  const entry = cache.get(key) as CacheEntry<T> | undefined
  return entry?.data
}

export async function readThroughCache<T>(
  key: string,
  ttlMs: number,
  fetcher: () => Promise<T>,
  force = false,
  staleWhileRevalidate = false
): Promise<T> {
  if (!force) {
    const entry = cache.get(key) as CacheEntry<T> | undefined
    if (entry) {
      const isExpired = Date.now() >= entry.expiresAt
      if (!isExpired) return entry.data
      if (staleWhileRevalidate) {
        fetcher()
          .then((fresh) => cache.set(key, { data: fresh, expiresAt: Date.now() + ttlMs }))
          .catch(() => {
            /* silenciar errores del refresco en background */
          })
        return entry.data
      }
    }
  }

  try {
    const fetched = await fetcher()
    cache.set(key, { data: fetched, expiresAt: Date.now() + ttlMs })
    return fetched
  } catch (err) {
    const stale = getStale<T>(key)
    if (stale !== undefined) {
      return stale
    }
    throw err
  }
}