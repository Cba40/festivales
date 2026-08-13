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

export function useAttendanceLevelMutations(eventId: string) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: AttendanceLevelCreatePayload): Promise<AttendanceLevelDTO | null> => {
      if (!eventId) {
        setError('Evento no disponible');
        return null;
      }

      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<AttendanceLevelDTO>(
          `/events/${eventId}/attendance-levels`,
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
    [eventId]
  );

  const update = useCallback(
    async (id: string, payload: AttendanceLevelUpdatePayload): Promise<AttendanceLevelDTO | null> => {
      if (!eventId) {
        setError('Evento no disponible');
        return null;
      }

      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<AttendanceLevelDTO>(
          `/events/${eventId}/attendance-levels/${id}`,
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
    [eventId]
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      if (!eventId) {
        setError('Evento no disponible');
        return false;
      }

      setSaving(true);
      setError(null);
      try {
        await apiClient.delete(`/events/${eventId}/attendance-levels/${id}`);
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al eliminar nivel de asistencia';
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    [eventId]
  );

  return { create, update, remove, saving, error };
}
