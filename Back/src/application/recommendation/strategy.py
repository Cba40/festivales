from __future__ import annotations

import logging
import math
from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from src.application.recommendation.config import RecommendationConfig
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState

PARKING_TYPE = "estacionamiento"

logger = logging.getLogger(__name__)


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
        zone_coordinates: Mapping[UUID, tuple[float, float]] | None = None,
    ) -> list[ZoneRecommendation]:
        zone_states = prediction.zone_states

        viable = self._filter_viable_zones(
            zone_states, requested_action, mobility_context, config
        )

        if requested_action.type == PARKING_TYPE:
            return self._select_three_options(
                viable, user_context, mobility_context, config, zone_coordinates
            )

        scored = self._calculate_scores(
            viable, user_context, mobility_context, config
        )

        with_reasoning = self._generate_reasoning(
            scored, mobility_context, config
        )

        return self._mark_nearest(
            self._sort_recommendations(with_reasoning),
            mobility_context,
            zone_coordinates,
        )

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
    def _select_three_options(
        viable_zones: list[ZoneState],
        user_context: UserContext,
        mobility_context: MobilityContext,
        config: RecommendationConfig,
        zone_coordinates: Mapping[UUID, tuple[float, float]] | None,
    ) -> list[ZoneRecommendation]:
        candidates: list[tuple[ZoneState, float]] = []
        for zone in viable_zones:
            if zone.saturation_level is None:
                logger.warning(
                    "Zona de estacionamiento %s excluida: saturation_level ausente",
                    zone.zone_id,
                )
                continue
            free_ratio = 1.0 - zone.saturation_level
            candidates.append((zone, free_ratio))

        available = [
            (zone, free_ratio)
            for zone, free_ratio in candidates
            if free_ratio > config.min_availability_threshold
        ]
        available.sort(key=lambda t: (-t[1], str(t[0].zone_id)))

        option1 = available[0] if len(available) >= 1 else None
        option2 = available[1] if len(available) >= 2 else None

        chosen_ids = {option1[0].zone_id} if option1 is not None else set()
        if option2 is not None:
            chosen_ids.add(option2[0].zone_id)

        option3: tuple[ZoneState, float] | None = None
        if (
            zone_coordinates is not None
            and mobility_context.latitude is not None
            and mobility_context.longitude is not None
        ):
            candidates_with_distance: list[tuple[ZoneState, float]] = []
            for zone, _free_ratio in available:
                if zone.zone_id in chosen_ids:
                    continue
                coords = zone_coordinates.get(zone.zone_id)
                if coords is None:
                    continue
                distance = WeightedScoringStrategy._calculate_distance(
                    mobility_context.latitude,
                    mobility_context.longitude,
                    coords[0],
                    coords[1],
                )
                candidates_with_distance.append((zone, distance))
            candidates_with_distance.sort(
                key=lambda t: (t[1], str(t[0].zone_id))
            )
            if candidates_with_distance:
                option3 = candidates_with_distance[0]

        recommendations: list[ZoneRecommendation] = []

        if option1 is not None:
            zone, _free_ratio = option1
            score = WeightedScoringStrategy._calculate_scores(
                [zone], user_context, mobility_context, config
            )[0][1]
            contextual_reasoning = WeightedScoringStrategy._generate_reasoning(
                [(zone, score)], mobility_context, config
            )[0][2]
            recommendations.append(
                ZoneRecommendation(
                    zone_id=zone.zone_id,
                    score=score,
                    reasoning=["Más lugares libres"] + contextual_reasoning,
                    is_nearest=False,
                )
            )

        if option2 is not None:
            zone, _free_ratio = option2
            score = WeightedScoringStrategy._calculate_scores(
                [zone], user_context, mobility_context, config
            )[0][1]
            contextual_reasoning = WeightedScoringStrategy._generate_reasoning(
                [(zone, score)], mobility_context, config
            )[0][2]
            recommendations.append(
                ZoneRecommendation(
                    zone_id=zone.zone_id,
                    score=score,
                    reasoning=["Segunda opción con más lugares"] + contextual_reasoning,
                    is_nearest=False,
                )
            )

        if option3 is not None:
            zone, _distance = option3
            score = WeightedScoringStrategy._calculate_scores(
                [zone], user_context, mobility_context, config
            )[0][1]
            contextual_reasoning = WeightedScoringStrategy._generate_reasoning(
                [(zone, score)], mobility_context, config
            )[0][2]
            recommendations.append(
                ZoneRecommendation(
                    zone_id=zone.zone_id,
                    score=score,
                    reasoning=["Más cerca de vos"] + contextual_reasoning,
                    is_nearest=True,
                )
            )

        return recommendations

    @staticmethod
    def _calculate_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(d_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return 6_371_000.0 * c

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

    @staticmethod
    def _mark_nearest(
        recommendations: list[ZoneRecommendation],
        mobility_context: MobilityContext,
        zone_coordinates: Mapping[UUID, tuple[float, float]] | None,
    ) -> list[ZoneRecommendation]:
        """Marca `is_nearest=True` en la zona más cercana al usuario.

        Mismo patrón que Parking V1 (opción 3): la distancia real se calcula
        con Haversine entre las coordenadas del usuario y las de cada zona
        recomendada. Sin lat/lng del usuario o sin coordenadas de zona,
        ninguna zona se marca (`is_nearest=False`).
        """
        if (
            zone_coordinates is None
            or mobility_context.latitude is None
            or mobility_context.longitude is None
        ):
            return recommendations

        nearest_id: UUID | None = None
        nearest_distance = float("inf")
        for rec in recommendations:
            coords = zone_coordinates.get(rec.zone_id)
            if coords is None:
                continue
            distance = WeightedScoringStrategy._calculate_distance(
                mobility_context.latitude,
                mobility_context.longitude,
                coords[0],
                coords[1],
            )
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_id = rec.zone_id

        if nearest_id is None:
            return recommendations

        return [
            ZoneRecommendation(
                zone_id=rec.zone_id,
                score=rec.score,
                reasoning=rec.reasoning,
                is_nearest=(rec.zone_id == nearest_id),
            )
            for rec in recommendations
        ]
