import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type { EventDay } from '@/features/dashboard/types';

let cachedEventDay: EventDay | null = null;

export const getCachedEventDay = (): EventDay | null => cachedEventDay;

export const loadEventDayContext = async (eventId: string): Promise<EventDay | null> => {
  try {
    const { data } = await apiClient.get<EventDay | null>(
      endpoints.eventDays.today(eventId)
    );
    cachedEventDay = data;
    return data;
  } catch {
    cachedEventDay = null;
    return null;
  }
};

export const getHoraEvento = (): number => {
  if (cachedEventDay?.peak_hour_start != null) {
    return cachedEventDay.peak_hour_start;
  }
  return new Date().getHours();
};

export const getEventDayPeakRange = (): [number, number] | null => {
  if (cachedEventDay?.peak_hour_start != null && cachedEventDay?.peak_hour_end != null) {
    return [cachedEventDay.peak_hour_start, cachedEventDay.peak_hour_end];
  }
  return null;
};

export const getEventDaySchedule = () => {
  if (!cachedEventDay) return null;
  return {
    openingTime: cachedEventDay.opening_time,
    closingTime: cachedEventDay.closing_time,
    peakStart: cachedEventDay.peak_hour_start,
    peakEnd: cachedEventDay.peak_hour_end,
    weather: cachedEventDay.weather,
    artist: cachedEventDay.headliner_artist,
    attendance: cachedEventDay.expected_attendance,
  };
};
