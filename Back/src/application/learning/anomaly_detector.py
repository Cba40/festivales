from __future__ import annotations

from dataclasses import dataclass

from src.application.learning.metric_result import MetricResult

STATUS_ENABLED = "ENABLED"


@dataclass(frozen=True)
class Anomaly:
    metric_name: str
    severity: str
    description: str
    suggested_action: str
    value: float | None
    is_provisional: bool = True


class AnomalyDetector:
    """Detecta anomalías sobre cada ``MetricResult`` (Etapa 2).

    Umbrales simples y documentados. Solo las métricas con status ``ENABLED``
    y con valor no nulo son evaluadas:
      - ``density_deviation`` > 0.2 → severidad alta.
      - ``zone_behavior_adherence`` < 0.5 → severidad alta.
      - ``incident_frequency`` > 1.0 (incidentes por hora) → severidad alta.
    """

    SEVERITY_HIGH = "high"

    DENSITY_DEVIATION_THRESHOLD = 0.2
    ADHERENCE_THRESHOLD = 0.5
    INCIDENT_FREQUENCY_THRESHOLD = 1.0

    def __init__(
        self,
        density_deviation_threshold: float = DENSITY_DEVIATION_THRESHOLD,
        adherence_threshold: float = ADHERENCE_THRESHOLD,
        incident_frequency_threshold: float = INCIDENT_FREQUENCY_THRESHOLD,
    ) -> None:
        self._density_deviation_threshold = density_deviation_threshold
        self._adherence_threshold = adherence_threshold
        self._incident_frequency_threshold = incident_frequency_threshold

    def detect(self, result: MetricResult) -> Anomaly | None:
        if result.status != STATUS_ENABLED or result.value is None:
            return None

        value = result.value

        if result.name == "density_deviation" and value > self._density_deviation_threshold:
            return Anomaly(
                metric_name=result.name,
                severity=self.SEVERITY_HIGH,
                description=(
                    f"La cantidad de personas observada en las zonas es un {int(value * 100)}% mayor "
                    f"a lo que el sistema predijo. Esto indica que las zonas se están llenando más "
                    f"rápido de lo esperado."
                ),
                suggested_action=(
                    "Revisar la distribución de recursos (personal, señalización o accesos) en las "
                    "zonas afectadas para mejorar el flujo de personas en el próximo ciclo."
                ),
                value=value,
                is_provisional=True,
            )

        if result.name == "zone_behavior_adherence" and value < self._adherence_threshold:
            return Anomaly(
                metric_name=result.name,
                severity=self.SEVERITY_HIGH,
                description=(
                    f"La adherencia a zone_behaviors promedio ({value:.3f}) está por debajo "
                    f"del umbral de {self._adherence_threshold}."
                ),
                suggested_action=(
                    "Revisar los density_factor de los zone_behaviors de la fase activa "
                    "y su cobertura por zona."
                ),
                value=value,
                is_provisional=True,
            )

        if result.name == "incident_frequency" and value > self._incident_frequency_threshold:
            return Anomaly(
                metric_name=result.name,
                severity=self.SEVERITY_HIGH,
                description=(
                    f"La frecuencia de incidentes ({value:.3f} por hora) supera el umbral "
                    f"de {self._incident_frequency_threshold}."
                ),
                suggested_action=(
                    "Revisar los parámetros de control de flujo y los recursos de las "
                    "zonas con mayor concentración de incidentes."
                ),
                value=value,
                is_provisional=True,
            )

        return None

    def detect_all(self, results: list[MetricResult]) -> list[Anomaly]:
        anomalies: list[Anomaly] = []
        for result in results:
            anomaly = self.detect(result)
            if anomaly is not None:
                anomalies.append(anomaly)
        return anomalies