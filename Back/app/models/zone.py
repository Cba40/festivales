# backend/app/models/zone.py

import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    saturation: Mapped[str] = mapped_column(String(20), nullable=False, default="bajo")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geometry: Mapped[Optional[str]] = mapped_column(Geometry("POLYGON"), nullable=True)
    disponibilidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    espera_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tipo_culinario: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    horario: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    web: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    servicios: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    transporte: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    capacidad_estimada: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    es_embudo: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    geometry_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="point")
    coordinates: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event = relationship("Event", back_populates="zones")

    @staticmethod
    def calcular_saturation(capacity: int, available_capacity: int) -> str:
        if capacity <= 0:
            return "bajo"
        ratio = available_capacity / capacity
        if ratio > 0.75:
            return "bajo"
        if ratio > 0.50:
            return "medio"
        if ratio > 0.25:
            return "alto"
        return "colapsado"
