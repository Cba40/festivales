import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import { readThroughCache, eventDayTodayCacheKey, EVENT_DAY_TTL_MS } from '@/core/cache/memoryCache';
import type { EventDay } from '@/features/dashboard/types';

let cachedEventDay: EventDay | null = null;

export const getCachedEventDay = (): EventDay | null => cachedEventDay;

export const loadEventDayContext = async (eventId: string, force = false): Promise<EventDay | null> => {
  try {
    const data = await readThroughCache<EventDay | null>(
      eventDayTodayCacheKey(eventId),
      EVENT_DAY_TTL_MS,
      async () => {
        const { data } = await apiClient.get<EventDay | null>(
          endpoints.eventDays.today(eventId)
        );
        return data;
      },
      force
    );
    cachedEventDay = data;
    return data;
  } catch {
    return cachedEventDay ?? null;
  }
};

export const getHoraEvento = (): number => {
  if (cachedEventDay?.operational_start_min != null) {
    return cachedEventDay.operational_start_min / 60;
  }
  return new Date().getHours();
};

export const getEventDayPeakRange = (): [number, number] | null => {
  if (cachedEventDay?.operational_start_min != null && cachedEventDay?.operational_end_min != null) {
    return [cachedEventDay.operational_start_min / 60, cachedEventDay.operational_end_min / 60];
  }
  return null;
};

export const getEventDaySchedule = () => {
  if (!cachedEventDay) return null;
  return {
    openingTime: cachedEventDay.operational_start_min,
    closingTime: cachedEventDay.operational_end_min,
    peakStart: cachedEventDay.operational_start_min / 60,
    peakEnd: cachedEventDay.operational_end_min / 60,
    weather: cachedEventDay.weather,
    artist: cachedEventDay.headliner_artist,
  };
};
