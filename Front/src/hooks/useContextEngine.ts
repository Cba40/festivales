import { useState, useCallback, useEffect, useRef } from 'react';
import { apiClient } from '../core/api/client';

const EVENT_ID = import.meta.env.VITE_EVENT_ID || 'default-event-id';
const BASE = (eid: string) => `/events/${eid}/context-engine`;

export interface EventStateDTO {
  id: string;
  event_id: string | null;
  name: string;
  slug: string;
  sort_order: number;
  color: string;
  description: string;
  is_initial: boolean;
  is_final: boolean;
  rules: Record<string, unknown>;
  created_at: string;
}

export interface StateOverrideDTO {
  id: string;
  event_day_id: string;
  event_state_id: string;
  zone_type_id: string | null;
  start_time: string;
  end_time: string;
  reason: string;
  created_by: string;
  is_active: boolean;
  created_at: string;
}

export interface ZonePredictionDTO {
  id: string;
  name: string;
  type: string;
  factores: {
    saturation: number;
    attendance: number;
    resource: number;
    priority: number;
  };
  prediccion: {
    saturation_predicha: number;
    attendance_predicha: number;
    recurso_requerido: number;
    priority_score: number;
  };
}

export interface CurrentStateResponseDTO {
  estado_actual: EventStateDTO | null;
  override_activo: StateOverrideDTO | null;
}

export interface ContextEngineResponseDTO {
  estado_actual: EventStateDTO | null;
  override_activo: StateOverrideDTO | null;
  zonas: ZonePredictionDTO[];
}

export interface ZoneTypeDTO {
  id: string;
  name: string;
  slug: string;
  icon: string;
  description: string;
  default_factors: Record<string, { saturation: number; attendance: number; resource: number }>;
  created_at: string;
}

export interface EventDayZoneFactorDTO {
  id: string;
  event_day_id: string;
  zone_type_id: string;
  event_state_id: string;
  saturation_factor: number;
  attendance_factor: number;
  resource_factor: number;
  priority_weight: number;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface StateOverrideCreatePayload {
  event_day_id: string;
  event_state_id: string;
  zone_type_id?: string | null;
  start_time: string;
  end_time: string;
  reason: string;
  created_by: string;
}

export interface EventDayZoneFactorCreatePayload {
  event_day_id: string;
  zone_type_id: string;
  event_state_id: string;
  saturation_factor: number;
  attendance_factor: number;
  resource_factor: number;
  priority_weight: number;
  description?: string | null;
}

export interface EventDayZoneFactorUpdatePayload {
  saturation_factor?: number;
  attendance_factor?: number;
  resource_factor?: number;
  priority_weight?: number;
  description?: string | null;
}

export function useCurrentState(eventId: string = EVENT_ID) {
  const [state, setState] = useState<EventStateDTO | null>(null);
  const [override, setOverride] = useState<StateOverrideDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (datetimeActual?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (datetimeActual) params.datetime_actual = datetimeActual;
      const { data } = await apiClient.get<CurrentStateResponseDTO>(
        `${BASE(eventId)}/state`, { params }
      );
      setState(data.estado_actual);
      setOverride(data.override_activo);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener estado actual');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  return { state, override, loading, error, refresh };
}

export function usePredictions(eventId: string = EVENT_ID) {
  const [data, setData] = useState<ContextEngineResponseDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (datetimeActual?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (datetimeActual) params.datetime_actual = datetimeActual;
      const { data: res } = await apiClient.get<ContextEngineResponseDTO>(
        `${BASE(eventId)}/predictions`, { params }
      );
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al obtener predicciones');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  return { data, loading, error, refresh };
}

export function useOverrides(eventId: string = EVENT_ID) {
  const [overrides, setOverrides] = useState<StateOverrideDTO[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createOverride = useCallback(async (payload: StateOverrideCreatePayload) => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await apiClient.post<StateOverrideDTO>(
        `${BASE(eventId)}/overrides`, payload
      );
      setOverrides(prev => [...prev, data]);
      return data;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al crear override');
      return null;
    } finally {
      setSaving(false);
    }
  }, [eventId]);

  const cancelOverride = useCallback(async (overrideId: string) => {
    setError(null);
    try {
      const { data } = await apiClient.delete<StateOverrideDTO>(
        `${BASE(eventId)}/overrides/${overrideId}`
      );
      setOverrides(prev => prev.map(o => o.id === overrideId ? data : o));
      return data;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al cancelar override');
      return null;
    }
  }, [eventId]);

  return { overrides, saving, error, createOverride, cancelOverride, setOverrides };
}

export function useEventDayZoneFactors(eventId: string = EVENT_ID) {
  const [factors, setFactors] = useState<EventDayZoneFactorDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFactors = useCallback(async (eventDayId: string) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<EventDayZoneFactorDTO[]>(
        `${BASE(eventId)}/event-day-zone-factors`,
        { params: { event_day_id: eventDayId } }
      );
      setFactors(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al cargar factores');
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  const createFactor = useCallback(async (payload: EventDayZoneFactorCreatePayload) => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await apiClient.post<EventDayZoneFactorDTO>(
        `${BASE(eventId)}/event-day-zone-factors`, payload
      );
      setFactors(prev => [...prev, data]);
      return data;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al crear factor');
      return null;
    } finally {
      setSaving(false);
    }
  }, [eventId]);

  const updateFactor = useCallback(async (factorId: string, payload: EventDayZoneFactorUpdatePayload) => {
    setError(null);
    try {
      const { data } = await apiClient.put<EventDayZoneFactorDTO>(
        `${BASE(eventId)}/event-day-zone-factors/${factorId}`, payload
      );
      setFactors(prev => prev.map(f => f.id === factorId ? data : f));
      return data;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al actualizar factor');
      return null;
    }
  }, [eventId]);

  const deleteFactor = useCallback(async (factorId: string) => {
    setError(null);
    try {
      await apiClient.delete(`${BASE(eventId)}/event-day-zone-factors/${factorId}`);
      setFactors(prev => prev.filter(f => f.id !== factorId));
      return true;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al eliminar factor');
      return false;
    }
  }, [eventId]);

  return {
    factors, loading, saving, error,
    fetchFactors, createFactor, updateFactor, deleteFactor,
  };
}

export function useEventStates(eventId?: string) {
  const [states, setStates] = useState<EventStateDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (eid?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (eid) params.event_id = eid;
      const { data } = await apiClient.get<EventStateDTO[]>(
        '/context-engine/event-states', { params }
      );
      setStates(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al cargar estados');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(eventId); }, [refresh, eventId]);

  return { states, loading, error, refresh };
}

export function useZoneTypes() {
  const [types, setTypes] = useState<ZoneTypeDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<ZoneTypeDTO[]>(
        '/context-engine/zone-types'
      );
      setTypes(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Error al cargar tipos de zona');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { types, loading, error, refresh };
}

export function useAutoRefresh(fn: () => void, intervalMs: number, active: boolean) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => fnRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs]);
}
