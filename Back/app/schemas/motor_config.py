from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    created_at: datetime
    updated_at: datetime


class Stage4ConfigUpdate(BaseModel):
    saturation_high_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    saturation_moderate_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
