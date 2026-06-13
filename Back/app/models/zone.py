# backend/app/models/zone.py

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

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
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[str | None] = mapped_column(Geometry("POLYGON"), nullable=True)
    disponibilidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    espera_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_culinario: Mapped[str | None] = mapped_column(String(100), nullable=True)
    x: Mapped[float | None] = mapped_column(Float, nullable=True)
    y: Mapped[float | None] = mapped_column(Float, nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    horario: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    web: Mapped[str | None] = mapped_column(String(255), nullable=True)
    servicios: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transporte: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capacidad_estimada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    es_embudo: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    geometry_type: Mapped[str | None] = mapped_column(String(10), nullable=True, default="point")
    coordinates: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
