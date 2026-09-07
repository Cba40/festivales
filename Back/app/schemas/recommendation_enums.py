from __future__ import annotations

from enum import StrEnum


class RecommendationType(StrEnum):
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    NEW_CONFIGURATION = "new_configuration"
    CONFIGURATION_REMOVAL = "configuration_removal"
    DATA_QUALITY_IMPROVEMENT = "data_quality_improvement"
    COVERAGE_IMPROVEMENT = "coverage_improvement"


class RecommendationStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"