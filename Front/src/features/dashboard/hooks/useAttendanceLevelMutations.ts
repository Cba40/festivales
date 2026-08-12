import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { AttendanceLevelDTO } from '../types';

export interface AttendanceLevelCreatePayload {
  name: string;
  min_people: number;
  max_people?: number | null;
}

export interface AttendanceLevelUpdatePayload {
  name?: string;
  min_people?: number;
  max_people?: number | null;
}

export function useAttendanceLevelMutations(eventId: string, eventDayId?: string) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: AttendanceLevelCreatePayload): Promise<AttendanceLevelDTO | null> => {
      if (!eventId || !eventDayId) {
        setError('Debe seleccionar un día del evento antes de crear un nivel');
        return null;
      }

      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<AttendanceLevelDTO>(
          `/events/${eventId}/days/${eventDayId}/attendance-levels`,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al crear nivel de asistencia';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [eventId, eventDayId]
  );

  const update = useCallback(
    async (id: string, payload: AttendanceLevelUpdatePayload): Promise<AttendanceLevelDTO | null> => {
      if (!eventId || !eventDayId) {
        setError('Debe seleccionar un día del evento antes de actualizar un nivel');
        return null;
      }

      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<AttendanceLevelDTO>(
          `/events/${eventId}/days/${eventDayId}/attendance-levels/${id}`,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al actualizar nivel de asistencia';
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [eventId, eventDayId]
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      if (!eventId || !eventDayId) {
        setError('Debe seleccionar un día del evento antes de eliminar un nivel');
        return false;
      }

      setSaving(true);
      setError(null);
      try {
        await apiClient.delete(`/events/${eventId}/days/${eventDayId}/attendance-levels/${id}`);
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al eliminar nivel de asistencia';
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId, eventDayId]
  );

  return { create, update, remove, saving, error };
}
