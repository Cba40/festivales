from __future__ import annotations

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

        if requested_action.type == PARKING_TYPE or requested_action.type == "comida":
            return self._select_four_options(
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
    def _select_four_options(
        viable_zones: list[ZoneState],
        user_context: UserContext,
        mobility_context: MobilityContext,
        config: RecommendationConfig,
        zone_coordinates: Mapping[UUID, tuple[float, float]] | None,
    ) -> list[ZoneRecommendation]:
        candidates: list[tuple[ZoneState, float]] = []
        for zone in viable_zones:
            if zone.saturation_level is not None:
                free_ratio = 1.0 - zone.saturation_level
            else:
                # P3.0 §5.4: sin señal de saturación (modelo especializado), usar
                # projected_density como proxy de densidad. Genérico: vale para
                # comida, hidratación, descanso, etc. `capacity` no vive en
                # ZoneState, se intenta desde model_result; si no se puede
                # computar el proxy, se asume zona operativa (free_ratio=0.9).
                capacity = (
                    zone.model_result.get("capacity")
                    if zone.model_result is not None
                    else None
                )
                if (
                    zone.projected_density is not None
                    and capacity
                    and capacity > 0
                ):
                    free_ratio = 1.0 - min(zone.projected_density / capacity, 1.0)
                else:
                    free_ratio = 0.9
            candidates.append((zone, free_ratio))

        available = [
            (zone, free_ratio)
            for zone, free_ratio in candidates
            if free_ratio > config.min_availability_threshold
        ]

        has_user_gps = (
            zone_coordinates is not None
            and mobility_context.latitude is not None
            and mobility_context.longitude is not None
        )

        def _dist_to_user(zone: ZoneState) -> float | None:
            if not has_user_gps:
                return None
            coords = zone_coordinates.get(zone.zone_id)
            if coords is None:
                return None
            return WeightedScoringStrategy._calculate_distance(
                mobility_context.latitude,
                mobility_context.longitude,
                coords[0],
                coords[1],
            )

        def _dist_to_reference(zone: ZoneState) -> float | None:
            if zone.model_result is None:
                return None
            d = zone.model_result.get("distance")
            return float(d) if d is not None else None

        zd = ZoneRecommendation

        # Opción 1: mayor disponibilidad (free_ratio más alto)
        option1 = max(available, key=lambda t: (t[1], str(t[0].zone_id))) if available else None

        if option1 is not None:
            option2: tuple[ZoneState, float] | None
            chosen_ids = {option1[0].zone_id}
            rest = [t for t in available if t[0].zone_id not in chosen_ids]

            # Opción 2: mejor balance disponibilidad/distancia al usuario.
            # score = free_ratio * (1000 / max(dist_to_user, 100)) para normalizar.
            if has_user_gps:
                def _balance_key(t: tuple[ZoneState, float]) -> tuple[float, str]:
                    zone, fr = t
                    d = _dist_to_user(zone)
                    balance = fr * (1000.0 / (max(d, 100.0) if d is not None else 1000.0))
                    return (balance, str(zone.zone_id))
                option2 = max(rest, key=_balance_key) if rest else None
            else:
                # Sin GPS de usuario: segunda mayor disponibilidad como fallback.
                option2 = max(rest, key=lambda t: (t[1], str(t[0].zone_id))) if rest else None

            if option2 is not None:
                chosen_ids.add(option2[0].zone_id)
            rest2 = [t for t in available if t[0].zone_id not in chosen_ids]

            # Opción 3: más cercana al usuario con free_ratio > 0.20
            option3: tuple[ZoneState, float] | None = None
            if has_user_gps:
                candidates_3 = [
                    (z, fr) for z, fr in rest2
                    if fr > 0.20 and _dist_to_user(z) is not None
                ]
                if candidates_3:
                    option3 = min(
                        candidates_3, key=lambda t: (_dist_to_user(t[0]), str(t[0].zone_id))
                    )
                    chosen_ids.add(option3[0].zone_id)

            # Opción 4: más cercana al epicentro con free_ratio > 0.20
            option4: tuple[ZoneState, float] | None = None
            rest3 = [t for t in rest2 if t[0].zone_id not in chosen_ids]
            candidates_4 = [
                (z, fr) for z, fr in rest3
                if fr > 0.20 and _dist_to_reference(z) is not None
            ]
            if candidates_4:
                option4 = min(
                    candidates_4, key=lambda t: (_dist_to_reference(t[0]), str(t[0].zone_id))
                )

            selected = [option1, option2, option3, option4]
        else:
            selected = []

        selected = [s for s in selected if s is not None]

        recommendations: list[ZoneRecommendation] = []
        labels: list[str] = [
            "Mejor opción con más lugares libres",
            "Mejor balance de disponibilidad y cercanía",
            "Más cerca de vos",
            "Cerca del epicentro del evento",
        ]
        for i, (zone, _fr) in enumerate(selected):
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
                    reasoning=[labels[i]] + contextual_reasoning,
                    is_nearest=(i == 2),
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

            # Contexto operativo del Context Engine (RFC §10.2): los factores
            # de razonamiento ya incluyen el impacto de eventos imprevistos
            # ("Impacto de evento operativo: -N" e "Incidente activo en zona").
            # Se propagan a la razón de la recomendación para que el usuario
            # vea el contexto actualizado (densidad proyectada afectada).
            for factor in zone.reasoning_factors:
                if factor not in reasons:
                    reasons.append(factor)

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
