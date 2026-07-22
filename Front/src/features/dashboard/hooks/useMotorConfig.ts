import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/core/api/client';
import { endpoints } from '@/core/api/endpoints';
import type {
  RecommendationConfigDTO,
  RecommendationConfigUpdatePayload,
  Stage4ConfigDTO,
  Stage4ConfigUpdatePayload,
} from '../types';

export function useRecommendationConfig() {
  const [config, setConfig] = useState<RecommendationConfigDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<RecommendationConfigDTO>(
        endpoints.motorConfig.recommendationConfig
      );
      setConfig(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar configuración');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { config, loading, error, refresh: fetch };
}

export function useStage4Config() {
  const [config, setConfig] = useState<Stage4ConfigDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<Stage4ConfigDTO>(
        endpoints.motorConfig.stage4Config
      );
      setConfig(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar configuración');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  return { config, loading, error, refresh: fetch };
}

export function useMotorConfigMutations() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateRecommendation = useCallback(
    async (payload: RecommendationConfigUpdatePayload): Promise<RecommendationConfigDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<RecommendationConfigDTO>(
          endpoints.motorConfig.recommendationConfig,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al guardar configuración');
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const updateStage4 = useCallback(
    async (payload: Stage4ConfigUpdatePayload): Promise<Stage4ConfigDTO | null> => {
      setSaving(true);
      setError(null);
      try {
        const { data } = await apiClient.put<Stage4ConfigDTO>(
          endpoints.motorConfig.stage4Config,
          payload
        );
        return data;
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (err instanceof Error ? err.message : 'Error al guardar configuración');
        setError(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  return { updateRecommendation, updateStage4, saving, error };
}
