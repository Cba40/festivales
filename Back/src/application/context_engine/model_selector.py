"""Selección determinista de modelos especializados.

El Context Engine no debe contener `if`/`else` específicos de ningún modelo
(p. ej. Parking). La selección se delega a un registro de modelos por dominio,
ordenado y estático, de modo que la misma entrada produzca siempre la misma
selección.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.domain.entities.zone import Zone
from src.domain.models.specialized_model import SpecializedModel


class ModelSelector:
    """Registro documental de modelos especializados con selección determinista.

    Los modelos se registran y se consultan en orden de inserción. Para una
    misma zona y registros invariables, `select` devuelve siempre el mismo
    modelo: no hay aleatoriedad ni estado oculto.
    """

    def __init__(self, models: Sequence[SpecializedModel] | None = None) -> None:
        self._models: dict[str, SpecializedModel] = {}
        if models is not None:
            for model in models:
                self.register(model)

    def register(self, model: SpecializedModel) -> None:
        self._models[model.model_id] = model

    def unregister(self, model_id: str) -> None:
        self._models.pop(model_id, None)

    def select(self, zone: Zone) -> SpecializedModel | None:
        for model in self._models.values():
            if model.supports(zone):
                return model
        return None

    @property
    def models(self) -> Mapping[str, SpecializedModel]:
        return dict(self._models)

    def __repr__(self) -> str:
        return (
            f"ModelSelector("
            f"models={[m for m in self._models]})"
        )