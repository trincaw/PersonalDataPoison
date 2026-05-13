from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from identity.models import Identity

logger = logging.getLogger(__name__)


class IdentityScorer:

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or {
            "age_days": 0.3,
            "session_frequency": 0.25,
            "consistency": 0.25,
            "diversity": 0.2,
        }

    def score(self, identity: Identity) -> float:
        age_score = self._score_age(identity)
        freq_score = self._score_frequency(identity)
        consistency_score = self._score_consistency(identity)
        diversity_score = self._score_diversity(identity)

        total = (
            age_score * self._weights["age_days"]
            + freq_score * self._weights["session_frequency"]
            + consistency_score * self._weights["consistency"]
            + diversity_score * self._weights["diversity"]
        )

        clamped = max(0.0, min(1.0, total))
        logger.debug("Score for %s: %.3f (age=%.2f freq=%.2f cons=%.2f div=%.2f)",
                      identity.alias, clamped, age_score, freq_score, consistency_score, diversity_score)
        return clamped

    @staticmethod
    def _score_age(identity: Identity) -> float:
        age = (datetime.now(timezone.utc) - identity.created_at).days
        if age >= 90:
            return 1.0
        if age >= 30:
            return 0.7
        if age >= 7:
            return 0.4
        return 0.2

    @staticmethod
    def _score_frequency(identity: Identity) -> float:
        if identity.session_count == 0:
            return 0.1
        age_days = max((datetime.now(timezone.utc) - identity.created_at).days, 1)
        sessions_per_day = identity.session_count / age_days
        if 0.5 <= sessions_per_day <= 3.0:
            return 1.0
        if sessions_per_day < 0.5:
            return 0.5
        return 0.6  # too frequent looks bot-like

    @staticmethod
    def _score_consistency(identity: Identity) -> float:
        if not identity.last_seen:
            return 0.5
        gap = (datetime.now(timezone.utc) - identity.last_seen).days
        if gap <= 7:
            return 1.0
        if gap <= 30:
            return 0.6
        return 0.3

    @staticmethod
    def _score_diversity(identity: Identity) -> float:
        cats = len(identity.preferences.preferred_categories)
        if cats >= 4:
            return 1.0
        if cats >= 2:
            return 0.6
        return 0.3
