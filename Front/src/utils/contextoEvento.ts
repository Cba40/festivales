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
    attendance: cachedEventDay.estimated_attendance,
  };
};
