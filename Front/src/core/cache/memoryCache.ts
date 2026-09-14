type CacheEntry<T> = {
  data: T
  expiresAt: number
}

export const ZONES_TTL_MS = 60_000
export const EVENT_DAY_TTL_MS = 60_000
export const PREDICTION_TTL_MS = 15_000

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