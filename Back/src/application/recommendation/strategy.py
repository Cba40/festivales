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

# Roles de la selección curada: (label, marca como "más cerca de vos").
# El orden es el de preferencia; el texto va atado al ROL y no a la posición,
# para que si un rol no produce opción (p. ej. sin GPS del usuario) los demás
# conserven su etiqueta y el truncado por `max_recommendations` no desalinee.
CURATED_ROLES: tuple[tuple[str, bool], ...] = (
    ("Mejor opción con más lugares libres", False),
    ("Mejor balance de disponibilidad y cercanía", False),
    ("Más cerca de vos", True),
    ("Cerca del epicentro del evento", False),
)

# Roles para cuando NINGUNA zona trae señal de ocupación (sin modelo
# especializado). No hay disponibilidad que comparar, así que decir "la que
# tiene más lugares libres" sería mentira y, con todos los `free_ratio` en el
# mismo valor sintético, la elección caería al desempate por `zone_id`. Se
# ordena por cercanía real, que es lo único que se sabe.
CURATED_ROLES_PROXIMITY: tuple[tuple[str, bool], ...] = (
    ("Más cerca de vos", True),
    ("Mejor balance de cercanía", False),
    ("Cerca del epicentro del evento", False),
    ("Opción alternativa", False),
)

# Sin GPS del usuario no se puede afirmar "más cerca de vos": se cae a un
# orden por cercanía al epicentro, con etiquetas que dicen eso.
CURATED_ROLES_PROXIMITY_NO_GPS: tuple[tuple[str, bool], ...] = (
    ("Cerca del epicentro del evento", False),
    ("Segunda más cercana al epicentro", False),
    ("Tercera más cercana al epicentro", False),
    ("Cuarta más cercana al epicentro", False),
)

# `free_ratio` sintético para zonas sin modelo y sin proxy computable. NO
# ordena nada por sí solo: dispara el modo de roles por cercanía.
FALLBACK_FREE_RATIO = 0.9

CURATED_MAX = len(CURATED_ROLES)

# Tipos de zona que usan la selección curada por rol en lugar del ranking por
# score global. `servicios` cubre baños, hidratación y descanso: comparten el
# mismo criterio de "disponibilidad + cercanía", así que la misma plantilla
# curada les aplica sin duplicar lógica.
CURATED_TYPES: frozenset[str] = frozenset({PARKING_TYPE, "comida", "servicios"})


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
        reference_point: tuple[float, float] | None = None,
    ) -> list[ZoneRecommendation]:
        zone_states = prediction.zone_states

        viable = self._filter_viable_zones(
            zone_states, requested_action, mobility_context, config
        )

        if requested_action.type in CURATED_TYPES:
            return self._select_curated_options(
                viable,
                user_context,
                mobility_context,
                config,
                zone_coordinates,
                max_recommendations=CURATED_MAX,
                reference_point=reference_point,
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

        # ── Cierre global (Opcion C) ─────────────────────────────────────────
        # `operational_events` es la unica autoridad de cierre por zona: un
        # incidente `cierre_total` produce el impacto canonico -100, que Stage3
        # traduce a FlowRestriction.CLOSED. Una zona cerrada no es candidata
        # para NINGUNA accion. Antes solo se excluia en SEEK_EXIT y en el caso
        # `accessibility_required and speed == 0.0`, de modo que una zona
        # cerrada podia reaparecer en las recomendaciones de descanso, comida,
        # hidratacion o estacionamiento, incluso marcada como `is_nearest`.
        #
        # Se evalua despues del filtro de clasificacion para no alterar el
        # orden de los filtros, y antes que cualquier puntuacion.
        if zone.active_restriction == FlowRestriction.CLOSED:
            return False

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
    def _select_curated_options(
        viable_zones: list[ZoneState],
        user_context: UserContext,
        mobility_context: MobilityContext,
        config: RecommendationConfig,
zone_coordinates: Mapping[UUID, tuple[float, float]] | None,
        max_recommendations: int = CURATED_MAX,
        reference_point: tuple[float, float] | None = None,
    ) -> list[ZoneRecommendation]:
        """Selecciona sugerencias curadas por rol, no por score global.

        Dos modos, elegidos por los DATOS y no por el tipo de zona:

        * Con señal de ocupación (Parking, Baños) se usan `CURATED_ROLES`: más
          lugares libres, balance disponibilidad/distancia, más cerca del
          usuario y cerca del epicentro.
        * Sin señal (Gastronomía, y lo que venga sin modelo) se usan los roles
          por cercanía. No es una preferencia: sin `saturation_level` ni proxy
          todos los `free_ratio` valen lo mismo, así que "la que tiene más
          lugares libres" no distinguiría nada y se resolvería por `zone_id`.
          Cuando exista un modelo para comida, el modo cambia solo.

        `max_recommendations` recorta el set curado. Si un rol no tiene
        candidato se omite y los demás conservan su etiqueta.
        """
        candidates: list[tuple[ZoneState, float, bool]] = []
        for zone in viable_zones:
            if zone.saturation_level is not None:
                candidates.append((zone, 1.0 - zone.saturation_level, True))
                continue
            # P3.0 §5.4: sin señal de saturación (modelo especializado), usar
            # projected_density como proxy de densidad. Genérico: vale para
            # comida, hidratación, descanso, etc. `capacity` no vive en
            # ZoneState, se intenta desde model_result.
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
                candidates.append(
                    (zone, 1.0 - min(zone.projected_density / capacity, 1.0), True)
                )
            else:
                candidates.append((zone, FALLBACK_FREE_RATIO, False))

        available = [
            (zone, free_ratio)
            for zone, free_ratio, _measured in candidates
            if free_ratio > config.min_availability_threshold
        ]

        # El modo depende de si ALGUNA zona trae disponibilidad medida. Si
        # ninguna, el ranking por disponibilidad no tiene información y se pasa
        # a cercanía.
        has_availability_signal = any(m for _z, _fr, m in candidates)

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
            if zone.model_result is not None:
                d = zone.model_result.get("distance")
                if d is not None:
                    return float(d)
            # Las zonas sin modelo no traen `model_result`, así que la distancia
            # al epicentro se calcula desde el punto de referencia del evento.
            if reference_point is None or zone_coordinates is None:
                return None
            coords = zone_coordinates.get(zone.zone_id)
            if coords is None:
                return None
            return WeightedScoringStrategy._calculate_distance(
                reference_point[0],
                reference_point[1],
                coords[0],
                coords[1],
            )

        if not has_availability_signal:
            roles = (
                CURATED_ROLES_PROXIMITY
                if has_user_gps
                else CURATED_ROLES_PROXIMITY_NO_GPS
            )
            selected = WeightedScoringStrategy._pick_by_proximity(
                available, roles, has_user_gps, _dist_to_user, _dist_to_reference
            )
        else:
            roles = CURATED_ROLES
            selected = WeightedScoringStrategy._pick_by_availability(
                available, has_user_gps, _dist_to_user, _dist_to_reference
            )

        # Empareja por rol, no por índice: si un rol no produjo opción, los
        # demás conservan su label correcto.
        curated: list[tuple[ZoneState, str, bool]] = []
        for option, (label, is_nearest) in zip(selected, roles):
            if option is not None:
                curated.append((option[0], label, is_nearest))

        capped = max(0, min(max_recommendations, CURATED_MAX))

        recommendations: list[ZoneRecommendation] = []
        for zone, label, is_nearest in curated[:capped]:
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
                    reasoning=[label] + contextual_reasoning,
                    is_nearest=is_nearest,
                )
            )

        return recommendations

    @staticmethod
    def _pick_by_availability(
        available: list[tuple[ZoneState, float]],
        has_user_gps: bool,
        _dist_to_user,
        _dist_to_reference,
    ) -> list[tuple[ZoneState, float] | None]:
        """Roles con señal de ocupación: disponibilidad primero, distancia después."""
        option1 = (
            max(available, key=lambda t: (t[1], str(t[0].zone_id)))
            if available
            else None
        )
        if option1 is None:
            return [None, None, None, None]

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
                (z, fr) for z, fr in rest2 if fr > 0.20 and _dist_to_user(z) is not None
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
            (z, fr) for z, fr in rest3 if fr > 0.20 and _dist_to_reference(z) is not None
        ]
        if candidates_4:
            option4 = min(
                candidates_4, key=lambda t: (_dist_to_reference(t[0]), str(t[0].zone_id))
            )

        return [option1, option2, option3, option4]

    @staticmethod
    def _pick_by_proximity(
        available: list[tuple[ZoneState, float]],
        roles: tuple[tuple[str, bool], ...],
        has_user_gps: bool,
        _dist_to_user,
        _dist_to_reference,
    ) -> list[tuple[ZoneState, float] | None]:
        """Roles sin señal de ocupación: todo se decide por cercanía real.

        Cada rol se resuelve por mínima distancia con su propia métrica y nunca
        repite una zona ya elegida.
        """
        if not available:
            return [None] * len(roles)

        chosen: set[UUID] = set()

        def _sum(*dists: float | None) -> float | None:
            """Suma de distancias, o None si falta alguna."""
            if any(d is None for d in dists):
                return None
            return sum(d for d in dists if d is not None)

        def take(minimise) -> tuple[ZoneState, float] | None:
            pool = [t for t in available if t[0].zone_id not in chosen]
            if not pool:
                return None
            usable = [(t, minimise(t[0])) for t in pool]
            usable = [(t, d) for t, d in usable if d is not None]
            if not usable:
                return None
            best = min(usable, key=lambda td: (td[1], str(td[0][0].zone_id)))[0]
            chosen.add(best[0].zone_id)
            return best

        def _d_user(zone: ZoneState) -> float | None:
            return _dist_to_user(zone) if has_user_gps else None

        def _d_ref(zone: ZoneState) -> float | None:
            return _dist_to_reference(zone)

        picked: list[tuple[ZoneState, float] | None] = []
        for index, (_label, _is_nearest) in enumerate(roles):
            if index == 0 and has_user_gps:
                picked.append(take(_d_user))
            elif index == 1 and has_user_gps:
                # "Mejor balance": minimiza la suma de las dos distancias, o sea
                # la más céntrica respecto del usuario y del evento.
                picked.append(take(lambda z: _sum(_d_user(z), _d_ref(z))))
            elif index == 2:
                picked.append(take(_d_ref))
            else:
                picked.append(take(_d_ref if not has_user_gps else _d_user))
        return picked

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
