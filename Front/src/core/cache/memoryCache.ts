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

const COORDINATE_KEYS = new Set(['lat', 'lng', 'latitude', 'longitude'])

export function productCacheKey(
  eventId: string,
  productType: string,
  params: Record<string, unknown> = {}
): string {
  const normalizedId = normalizeEventId(eventId)
  const normalizedParams = Object.keys(params)
    .sort()
    .reduce<Record<string, unknown>>((acc, key) => {
      const value = params[key]
      if (value === undefined) return acc
      if (typeof value === 'number' && COORDINATE_KEYS.has(key)) {
        acc[key] = Number(value.toFixed(4))
      } else {
        acc[key] = value
      }
      return acc
    }, {})
  return `product:${normalizedId}:${productType}:${JSON.stringify(normalizedParams)}`
}

function getValid<T>(key: string): { hit: true; data: T } | { hit: false } {
  const entry = cache.get(key) as CacheEntry<T> | undefined
  if (entry && Date.now() < entry.expiresAt) {
    return { hit: true, data: entry.data }
  }
  return { hit: false }
}

function getStale<T>(key: string): T | undefined {
  const entry = cache.get(key) as CacheEntry<T> | undefined
  return entry?.data
}

export async function readThroughCache<T>(
  key: string,
  ttlMs: number,
  fetcher: () => Promise<T>,
  force = false
): Promise<T> {
  if (!force) {
    const valid = getValid<T>(key)
    if (valid.hit) return valid.data
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