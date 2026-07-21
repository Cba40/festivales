import { useState, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import type { AttendanceLevelDTO } from '../types';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';

export interface AttendanceLevelCreatePayload {
  name: string;
  min_people: number;
  max_people?: number | null;
  global_multiplier: number;
}

export interface AttendanceLevelUpdatePayload {
  name?: string;
  min_people?: number;
  max_people?: number | null;
  global_multiplier?: number;
}

export function useAttendanceLevelMutations() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (payload: AttendanceLevelCreatePayload): Promise<AttendanceLevelDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.post<AttendanceLevelDTO>(
          `/events/${EVENT_ID}/attendance-levels`,
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
    []
  );

  const update = useCallback(
    async (id: string, payload: AttendanceLevelUpdatePayload): Promise<AttendanceLevelDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<AttendanceLevelDTO>(
          `/events/${EVENT_ID}/attendance-levels/${id}`,
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
    []
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      setSaving(true);
      setError(null);
      try {
        await apiClient.delete(`/events/${EVENT_ID}/attendance-levels/${id}`);
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Error al eliminar nivel de asistencia';
        setError(msg);
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  return { create, update, remove, saving, error };
}
