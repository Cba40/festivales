from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


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
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
