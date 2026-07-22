from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _default_wait_mapping() -> list:
    return [
        [0.0, 0.3, 0],
        [0.3, 0.5, 5],
        [0.5, 0.7, 10],
        [0.7, 0.9, 15],
        [0.9, 1.01, 20],
    ]


class RecommendationConfigModel(Base):
    __tablename__ = "recommendation_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    low_density_saturation_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    low_density_reasoning_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    regulated_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    vip_bonus: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    staff_bonus: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    mobility_penalty: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Stage4ConfigModel(Base):
    __tablename__ = "stage4_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    saturation_high_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.9)
    saturation_moderate_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence_no_events: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence_planned_events: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    confidence_incident: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    wait_time_mapping: Mapped[list] = mapped_column(JSON, nullable=False, default=_default_wait_mapping)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
