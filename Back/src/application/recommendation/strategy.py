from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.application.recommendation.config import RecommendationConfig
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState


@runtime_checkable
class RecommendationStrategy(Protocol):
    def evaluate(
        self,
        *,
        prediction: TerritorialPrediction,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        config: RecommendationConfig,
    ) -> list[ZoneRecommendation]:
        ...


class WeightedScoringStrategy:
    def evaluate(
        self,
        *,
        prediction: TerritorialPrediction,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        config: RecommendationConfig,
    ) -> list[ZoneRecommendation]:
        zone_states = prediction.zone_states

        viable = self._filter_viable_zones(
            zone_states, requested_action, mobility_context, config
        )

        scored = self._calculate_scores(
            viable, user_context, mobility_context, config
        )

        with_reasoning = self._generate_reasoning(
            scored, mobility_context, config
        )

        return self._sort_recommendations(with_reasoning)

    @staticmethod
    def _is_zone_eligible(
        zone: ZoneState,
        requested_action: RequestedAction,
        mobility_context: MobilityContext,
        config: RecommendationConfig,
    ) -> bool:
        # ── Operational classification filter (P3.0 §11.5, RFC-005 §7 Etapa 1) ──
        # Zones of a different operational classification must never compete for
        # the same recommendation. Filtering happens BEFORE the RecommendationScore.
        requested_type = requested_action.type
        if requested_type is not None:
            if zone.type != requested_type:
                return False
            requested_subtipo = requested_action.subtipo
            if requested_subtipo is not None and zone.subtipo != requested_subtipo:
                return False

        # ── Behavioural filters ──────────────────────────────────────────────

        if requested_action.action_type == ActionType.SEEK_EXIT:
            if zone.active_restriction == FlowRestriction.CLOSED:
                return False

        if mobility_context.accessibility_required:
            if (
                mobility_context.speed == 0.0
                and zone.active_restriction == FlowRestriction.CLOSED
            ):
                return False

        if requested_action.action_type == ActionType.SEEK_LOW_DENSITY:
            # Solo se filtra por saturación cuando el modelo especializado la
            # produce. Sin ella no se fabrica comparación (contexto común).
            if (
                zone.saturation_level is not None
                and zone.saturation_level > config.low_density_saturation_threshold
            ):
                return False

        return True

    @staticmethod
    def _filter_viable_zones(
        zone_states: list[ZoneState],
        requested_action: RequestedAction,
        mobility_context: MobilityContext,
        config: RecommendationConfig,
    ) -> list[ZoneState]:
        return [
            z
            for z in zone_states
            if WeightedScoringStrategy._is_zone_eligible(
                z, requested_action, mobility_context, config
            )
        ]

    @staticmethod
    def _calculate_scores(
        viable_zones: list[ZoneState],
        user_context: UserContext,
        mobility_context: MobilityContext,
        config: RecommendationConfig,
    ) -> list[tuple[ZoneState, float]]:
        result: list[tuple[ZoneState, float]] = []
        for zone in viable_zones:
            # Término de densidad: solo cuando el modelo especializado la
            # produce. Sin `saturation_level` NO hay señal de saturación: no
            # se incorpora término de densidad (ni penalización ni bonus).
            score = 1.0
            if zone.saturation_level is not None:
                score -= zone.saturation_level

            if zone.active_restriction == FlowRestriction.REGULATED:
                score *= 1.0 - config.regulated_penalty

            if user_context.access_level == AccessLevel.VIP:
                score += config.vip_bonus
            elif user_context.access_level == AccessLevel.STAFF:
                score += config.staff_bonus

            if (
                mobility_context.current_zone_id is not None
                and mobility_context.current_zone_id != zone.zone_id
            ):
                score -= config.mobility_penalty

            if score < 0.0:
                score = 0.0
            if score > 1.0:
                score = 1.0

            score = round(score, 4)

            result.append((zone, score))
        return result

    @staticmethod
    def _generate_reasoning(
        scored_zones: list[tuple[ZoneState, float]],
        mobility_context: MobilityContext,
        config: RecommendationConfig,
    ) -> list[tuple[ZoneState, float, list[str]]]:
        result: list[tuple[ZoneState, float, list[str]]] = []
        for zone, score in scored_zones:
            reasons: list[str] = []

            if (
                zone.saturation_level is not None
                and zone.saturation_level < config.low_density_reasoning_threshold
            ):
                reasons.append("Baja densidad proyectada")

            if zone.active_restriction == FlowRestriction.REGULATED:
                reasons.append("Acceso regulado operativo")

            if (
                mobility_context.current_zone_id is not None
                and mobility_context.current_zone_id != zone.zone_id
            ):
                reasons.append("Requiere desplazamiento desde zona actual")

            result.append((zone, score, reasons))
        return result

    @staticmethod
    def _sort_recommendations(
        recommendations: list[tuple[ZoneState, float, list[str]]],
    ) -> list[ZoneRecommendation]:
        # Desempate: se usa `saturation_level` solo cuando el modelo lo
        # produce. Sin señal disponible no se fabrica un valor: se usa un
        # centinela de ordenamiento (`float("inf")`) para posicionar esas
        # zonas al final, y el identificador de zona queda como criterio
        # determinista final.
        sorted_recs = sorted(
            recommendations,
            key=lambda r: (-r[1],
                           r[0].saturation_level
                           if r[0].saturation_level is not None
                           else float("inf"),
                           str(r[0].zone_id)),
        )
        return [
            ZoneRecommendation(
                zone_id=zone.zone_id,
                score=score,
                reasoning=reasons,
            )
            for zone, score, reasons in sorted_recs
        ]
