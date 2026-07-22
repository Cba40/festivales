"""Tests unitarios de schemas P3.0 — validación Pydantic.

Cubre §13: validación cross-field, constraints > 0, Literal enforcement,
campos eliminados y completitud del schema TerritorialPrediction.
"""
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.event_day import EventDayCreate, EventDayUpdate
from app.schemas.operational_event import OperationalEventCreate
from app.schemas.operational_event_modifier import EVENT_TYPE_LITERAL
from app.schemas.operational_phase import OperationalPhaseCreate, OperationalPhaseUpdate
from app.schemas.territorial_prediction import TerritorialPrediction, ZonePrediction
from app.schemas.zone_behavior import ZoneBehaviorCreate


def test_operational_phase_create_end_min_gt_start_min():
    """§13: OperationalPhaseCreate rechaza end_min <= start_min."""
    with pytest.raises(ValidationError) as exc_info:
        OperationalPhaseCreate(
            operational_profile_id=uuid.uuid4(),
            name="Test",
            start_min=100,
            end_min=50,
            sort_order=1,
        )
    assert "end_min must be greater than start_min" in str(exc_info.value)


def test_operational_phase_update_partial_validation():
    """§13: OperationalPhaseUpdate permite solo start_min, pero rechaza end <= start cuando ambos se envían."""
    # Solo start_min — debe ser válido
    u = OperationalPhaseUpdate(start_min=100)
    assert u.start_min == 100
    assert u.end_min is None

    # Solo end_min — debe ser válido
    u = OperationalPhaseUpdate(end_min=200)
    assert u.end_min == 200

    # Ambos con end <= start — debe rechazar
    with pytest.raises(ValidationError) as exc_info:
        OperationalPhaseUpdate(start_min=200, end_min=100)
    assert "end_min must be greater than start_min" in str(exc_info.value)


def test_zone_behavior_factors_gt_zero():
    """§13: ZoneBehaviorCreate rechaza factor <= 0."""
    valid_id = str(uuid.uuid4())
    with pytest.raises(ValidationError) as exc_info:
        ZoneBehaviorCreate(
            operational_phase_id=uuid.uuid4(),
            zone_type_id=valid_id,
            saturation_factor=0,
            availability_factor=1.0,
            resource_factor=1.0,
            priority_weight=1.0,
        )
    msg = str(exc_info.value)
    assert "saturation_factor" in msg
    assert "gt" in msg.lower() or "greater than" in msg.lower()


def test_operational_event_literal_rejects_invalid():
    """§13: OperationalEventCreate rechaza event_type inválido."""
    with pytest.raises(ValidationError) as exc_info:
        OperationalEventCreate(
            event_day_id=str(uuid.uuid4()),
            event_type="tipo_invalido",
            description="test",
            start_min=0,
        )
    assert "event_type" in str(exc_info.value)


def test_operational_event_end_min_gt_start_min():
    """§13: OperationalEventCreate rechaza end_min <= start_min."""
    with pytest.raises(ValidationError) as exc_info:
        OperationalEventCreate(
            event_day_id=str(uuid.uuid4()),
            event_type="tormenta",
            description="test",
            start_min=100,
            end_min=50,
        )
    assert "end_min must be greater than start_min" in str(exc_info.value)


def test_event_day_create_operational_end_gt_start():
    """§13: EventDayCreate rechaza operational_end_min <= operational_start_min."""
    with pytest.raises(ValidationError) as exc_info:
        EventDayCreate(
            date="2026-07-10",
            day_of_week="jueves",
            operational_profile_id=uuid.uuid4(),
            operational_start_min=500,
            operational_end_min=400,
            estimated_attendance=1000,
            attendance_level_id=str(uuid.uuid4()),
        )
    assert "operational_end_min must be greater than" in str(exc_info.value)


def test_event_day_create_rejects_obsolete_fields():
    """§13: EventDayCreate no acepta campos obsoletos (entry_start_min no está en el schema)."""
    assert "entry_start_min" not in EventDayCreate.model_fields, \
        "entry_start_min no debe existir en el schema"
    assert "activity_peak_start_min" not in EventDayCreate.model_fields
    assert "activity_peak_end_min" not in EventDayCreate.model_fields
    assert "exit_start_min" not in EventDayCreate.model_fields
    assert "event_end_min" not in EventDayCreate.model_fields


def test_territorial_prediction_required_fields():
    """§13: TerritorialPrediction requiere zones, current_phase, attendance_level, active_events, timestamp."""
    # Sin zones — debe fallar (zones es list, default=None? No, es required)
    with pytest.raises(ValidationError):
        TerritorialPrediction(
            current_phase="Preparación",
            attendance_level="default",
            active_events=[],
            timestamp="2026-07-10T12:00:00Z",
        )

    # Sin current_phase — debe fallar
    with pytest.raises(ValidationError):
        TerritorialPrediction(
            zones=[],
            attendance_level="default",
            active_events=[],
            timestamp="2026-07-10T12:00:00Z",
        )

    # Sin timestamp — debe fallar
    with pytest.raises(ValidationError):
        TerritorialPrediction(
            zones=[],
            current_phase="Preparación",
            attendance_level="default",
            active_events=[],
        )

    # Con todos los campos requeridos — debe ser válido
    pred = TerritorialPrediction(
        zones=[],
        current_phase="Preparación",
        attendance_level="default",
        active_events=[],
        timestamp="2026-07-10T12:00:00Z",
    )
    assert pred.current_phase == "Preparación"

    # ZonePrediction requiere todos los campos obligatorios
    with pytest.raises(ValidationError):
        ZonePrediction(
            zone_id=str(uuid.uuid4()),
            # falta zone_type
            saturation_predicted=0.5,
            attendance_predicted=100.0,
            resource_required=5.0,
            priority_score=0.5,
            confidence=0.8,
        )

    # ZonePrediction válido
    zp = ZonePrediction(
        zone_id=str(uuid.uuid4()),
        zone_type="estacionamiento",
        saturation_predicted=0.5,
        attendance_predicted=100.0,
        resource_required=5.0,
        priority_score=0.5,
        confidence=0.8,
    )
    assert zp.zone_type == "estacionamiento"
    assert zp.priority_score == 0.5
    assert zp.confidence == 0.8
