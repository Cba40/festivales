"""ObservationControlProtocol: reglas de cuándo registrar observaciones.

Cada fila es una regla que una municipalidad configura **por evento**: si se
cumple una condición sobre una métrica que el motor ya calcula para una zona,
debería haberse registrado una observación cada N minutos.

Por qué existe
--------------
`operational_observations` las carga hoy un operador a mano desde
``ObservationsScreen``. Nadie guarantee que se registren en el momento justo, y
sin eso la métrica ``density_deviation`` (que compara predicción contra
observación en una ventana de ±30 min) se queda sin dato. Estos protocolos
convierten "debería" en una regla explícita, auditable y editable por evento.

Anclaje en métricas reales
-------------------------
``trigger_metric`` NO es una lista libre: sus valores son exactamente las claves
numéricas que el Context Engine escribe en ``predictions.zone_states_data``
(ver ``src/infrastructure/persistence/mappers/prediction_mapper.py``). Si se
inventara una métrica que el motor no produce, la regla nunca podría evaluarse.

Scope
-----
- ``event_id`` obligatorio: la unidad de configuración que pide el operador.
- ``event_day_id`` opcional: acota la regla a una sola jornada. ``NULL`` significa
  "todas las jornadas del evento". ``ON DELETE SET NULL`` y no ``CASCADE`` por el
  mismo motivo que ``zone_type_id``: perder la configuracion del operador porque
  se re-siembro el calendario seria peor que un alcance demasiado amplio.
- ``zone_type_id`` opcional: acota la regla a un tipo de zona. ``NULL`` significa
  "todas las zonas". ``ON DELETE SET NULL`` y no ``CASCADE``: borrar un tipo de
  zona debe desactivar el filtro, no borrar la regla.

Es decir: las dos columnas de estrechamiento son ``SET NULL`` (se degradan a
"todo el evento") y solo ``event_id`` es ``CASCADE`` (sin evento, la regla no
tiene sentido).

Convención del repo
-------------------
Timestamps con ``server_default=func.now()``, ``active`` para el soft delete (no
``is_active``, igual que ``emergency_protocols``) y unicidad por clave natural
``(event_id, name)``, calcada de ``UNIQUE(context, title)``.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ObservationTriggerMetric(str, Enum):
    """Métricas numéricas que el motor ya publica por zona.

    Cada valor es una clave de ``predictions.zone_states_data``. No agregar
    valores sin agregar antes la métrica al Context Engine.
    """

    SATURATION_LEVEL = "saturation_level"
    AVAILABILITY = "availability"
    ESTIMATED_WAIT = "estimated_wait"
    CONFIDENCE = "confidence"
    PROJECTED_DENSITY = "projected_density"


class ObservationTriggerOperator(str, Enum):
    """Comparador del umbral.

    Existe para que el operador municipal pueda decir "supera 80%" en vez de
    tener que invertir el número y el signo.
    """

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


_VALUES_CALLABLE = lambda enum_cls: [m.value for m in enum_cls]  # noqa: E731


class ObservationControlProtocol(Base):
    """Regla de control de observaciones para un evento.

    Tabla ``observation_control_protocols``.
    """

    __tablename__ = "observation_control_protocols"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_day_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        # SET NULL y no CASCADE: si la jornada desaparece (se edita su ventana
        # operativa, se re-siembra el calendario), la regla debe SOBREVIVIR y
        # volver a ser transversal, no borrarse en silencio. Borrar una
        # configuracion del operador porque le cambiaron el calendario a una
        # jornada seria perder trabajo suyo sin aviso. Es el mismo criterio que
        # `zone_type_id` mas abajo, y el contrario de `event_id`, que si es
        # CASCADE porque sin evento la regla no significa nada.
        ForeignKey("event_days.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    trigger_metric: Mapped[ObservationTriggerMetric] = mapped_column(
        SAEnum(
            ObservationTriggerMetric,
            name="observation_trigger_metric",
            length=32,
            values_callable=_VALUES_CALLABLE,
        ),
        nullable=False,
    )
    trigger_operator: Mapped[ObservationTriggerOperator] = mapped_column(
        SAEnum(
            ObservationTriggerOperator,
            name="observation_trigger_operator",
            length=8,
            values_callable=_VALUES_CALLABLE,
        ),
        nullable=False,
        default=ObservationTriggerOperator.GT,
    )
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    action_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    zone_type_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("zone_types.id", ondelete="SET NULL"),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_observation_control_protocols_event_name"),
        CheckConstraint(
            "action_interval_minutes BETWEEN 1 AND 1440",
            name="ck_observation_control_protocols_interval",
        ),
        CheckConstraint('"order" >= 0', name="ck_observation_control_protocols_order"),
    )