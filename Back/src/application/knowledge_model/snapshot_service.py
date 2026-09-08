from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.motor_config import RecommendationConfigModel, Stage4ConfigModel
from app.models.zone_behavior import ZoneBehavior
from src.domain.entities.knowledge_model_version import KnowledgeModelVersion
from src.domain.ports.knowledge_model_version_repository import KnowledgeModelVersionRepository


class KnowledgeModelSnapshotService:
    """Captura la configuración efectiva del modelo de conocimiento.

    El snapshot es inmutable por hash: versiones nuevas solo se crean cuando
    la configuración cambia (idempotencia). La versión activa alimenta el
    `knowledge_model_version_id` de las predicciones nuevas.
    """

    def __init__(self, repository: KnowledgeModelVersionRepository) -> None:
        self._repository = repository

    async def capture_current_snapshot(self, db: AsyncSession) -> dict:
        recommendation = (
            await db.execute(select(RecommendationConfigModel))
        ).scalars().first()
        if recommendation is None:
            raise ValueError("recommendation_config is not configured")

        stage4 = (
            await db.execute(select(Stage4ConfigModel))
        ).scalars().first()
        if stage4 is None:
            raise ValueError("stage4_config is not configured")

        zone_behaviors = (await db.execute(select(ZoneBehavior))).scalars().all()

        return {
            "recommendation_config": {
                "low_density_saturation_threshold": (
                    recommendation.low_density_saturation_threshold
                ),
                "low_density_reasoning_threshold": (
                    recommendation.low_density_reasoning_threshold
                ),
                "regulated_penalty": recommendation.regulated_penalty,
                "vip_bonus": recommendation.vip_bonus,
                "staff_bonus": recommendation.staff_bonus,
                "mobility_penalty": recommendation.mobility_penalty,
                "density_deviation_threshold": (
                    recommendation.density_deviation_threshold
                ),
            },
            "stage4_config": {
                "saturation_high_threshold": stage4.saturation_high_threshold,
                "saturation_moderate_threshold": (
                    stage4.saturation_moderate_threshold
                ),
                "confidence_no_events": stage4.confidence_no_events,
                "confidence_planned_events": stage4.confidence_planned_events,
                "confidence_incident": stage4.confidence_incident,
                "wait_time_mapping": stage4.wait_time_mapping,
            },
            "zone_behaviors": [
                {
                    "zone_type_id": str(b.zone_type_id),
                    "operational_phase_id": str(b.operational_phase_id),
                    "saturation_factor": float(b.saturation_factor),
                    "availability_factor": float(b.availability_factor),
                    "resource_factor": float(b.resource_factor),
                    "priority_weight": float(b.priority_weight),
                    "density_factor": b.density_factor,
                    "flow_restriction": b.flow_restriction,
                }
                for b in sorted(
                    zone_behaviors,
                    key=lambda b: (str(b.zone_type_id), str(b.operational_phase_id)),
                )
            ],
        }

    @staticmethod
    def calculate_snapshot_hash(snapshot: dict) -> str:
        payload = json.dumps(
            snapshot,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def get_or_create_version(
        self,
        db: AsyncSession,
        snapshot: dict,
        created_by: str | None = None,
    ) -> KnowledgeModelVersion:
        snapshot_hash = self.calculate_snapshot_hash(snapshot)

        existing = await self._repository.find_by_snapshot_hash(snapshot_hash)
        if existing is not None:
            return existing

        version = KnowledgeModelVersion(
            id=uuid4(),
            version_number=None,
            snapshot_data=snapshot,
            created_at=datetime.now(),
            created_by=created_by,
            snapshot_hash=snapshot_hash,
        )

        try:
            version = await self._repository.save(version)
        except IntegrityError:
            await db.rollback()
            existing = await self._repository.find_by_snapshot_hash(snapshot_hash)
            if existing is not None:
                return existing
            raise

        await db.commit()
        return version