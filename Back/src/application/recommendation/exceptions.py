class RecommendationServiceError(Exception):
    pass


class RecommendationNotPossible(RecommendationServiceError):
    def __init__(
        self,
        message: str = "Recommendation cannot be generated: insufficient data or all zones filtered out",
    ) -> None:
        super().__init__(f"RECOMMENDATION_NOT_POSSIBLE: {message}")
