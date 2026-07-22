from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendationConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    low_density_saturation_threshold: float = Field(ge=0.0, le=1.0)
    low_density_reasoning_threshold: float = Field(ge=0.0, le=1.0)
    regulated_penalty: float = Field(ge=0.0, le=1.0)
    vip_bonus: float = Field(ge=0.0, le=1.0)
    staff_bonus: float = Field(ge=0.0, le=1.0)
    mobility_penalty: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime


class RecommendationConfigUpdate(BaseModel):
    low_density_saturation_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    low_density_reasoning_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    regulated_penalty: float | None = Field(default=None, ge=0.0, le=1.0)
    vip_bonus: float | None = Field(default=None, ge=0.0, le=1.0)
    staff_bonus: float | None = Field(default=None, ge=0.0, le=1.0)
    mobility_penalty: float | None = Field(default=None, ge=0.0, le=1.0)


class Stage4ConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    saturation_high_threshold: float = Field(ge=0.0, le=1.0)
    saturation_moderate_threshold: float = Field(ge=0.0, le=1.0)
    confidence_no_events: float = Field(ge=0.0, le=1.0)
    confidence_planned_events: float = Field(ge=0.0, le=1.0)
    confidence_incident: float = Field(ge=0.0, le=1.0)
    wait_time_mapping: list[list[float]] = Field(min_length=1)
    created_at: datetime
    updated_at: datetime

    @field_validator("wait_time_mapping")
    @classmethod
    def validate_wait_time_mapping(cls, v: list) -> list:
        _validate_wait_time_mapping_rows(v)
        return v


class Stage4ConfigUpdate(BaseModel):
    saturation_high_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    saturation_moderate_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_no_events: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_planned_events: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_incident: float | None = Field(default=None, ge=0.0, le=1.0)
    wait_time_mapping: list[list[float]] | None = Field(default=None, min_length=1)

    @field_validator("wait_time_mapping")
    @classmethod
    def validate_wait_time_mapping(cls, v: list | None) -> list | None:
        if v is not None:
            _validate_wait_time_mapping_rows(v)
        return v


def _validate_wait_time_mapping_rows(mapping: list) -> None:
    for i, row in enumerate(mapping):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(
                f"wait_time_mapping[{i}]: each row must be a list of exactly 3 elements "
                f"[low, high, minutes], got {row}"
            )
        low, high, minutes = row
        if not isinstance(low, (int, float)):
            raise ValueError(f"wait_time_mapping[{i}][0] (low) must be numeric, got {type(low).__name__}")
        if not isinstance(high, (int, float)):
            raise ValueError(f"wait_time_mapping[{i}][1] (high) must be numeric, got {type(high).__name__}")
        if not isinstance(minutes, (int, float)):
            raise ValueError(f"wait_time_mapping[{i}][2] (minutes) must be numeric, got {type(minutes).__name__}")
        if low < 0:
            raise ValueError(f"wait_time_mapping[{i}][0] (low) must be >= 0, got {low}")
        if high <= low:
            raise ValueError(f"wait_time_mapping[{i}][1] (high) must be > low ({low}), got {high}")
        if minutes < 0:
            raise ValueError(f"wait_time_mapping[{i}][2] (minutes) must be >= 0, got {minutes}")
