# backend/app/models/recommendation_audit_entry.py

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RecommendationAuditEntry(Base):
    __tablename__ = "recommendation_audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    recommendation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    operator_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    input_data_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    km_version: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    algorithm_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "action IN ('generated', 'notified', 'review_started', 'resolved')",
            name="valid_action",
        ),
    )