"""Versioned logistic scoring model over the credit_features table.

Coefficients are code, not a pickle: every change is reviewed in a PR and
the model version lands next to each score for full auditability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MODEL_VERSION = "2026.07.0"

# Logistic regression coefficients (trained offline, reviewed in PR).
# Positive coefficient -> increases probability of default.
COEFFICIENTS = {
    "intercept": -1.8,
    "days_since_last_tx": 0.004,
    "mobile_tx_ratio": -0.9,
    "monthly_spend_to_income_ratio": 0.6,
    "tx_count_30d": -0.01,
    "intl_tx_ratio": 0.4,
}

SCORE_MIN, SCORE_MAX = 300, 850

RISK_BANDS = [  # (minimum score, band)
    (750, "A"),
    (650, "B"),
    (550, "C"),
    (SCORE_MIN, "D"),
]


@dataclass(frozen=True)
class ScoreResult:
    customer_id: str
    probability_of_default: float
    score: int
    risk_band: str
    model_version: str = MODEL_VERSION


def probability_of_default(features: dict) -> float:
    z = COEFFICIENTS["intercept"]
    for name, coefficient in COEFFICIENTS.items():
        if name != "intercept":
            z += coefficient * float(features.get(name) or 0.0)
    return 1.0 / (1.0 + math.exp(-z))


def to_score(pd_value: float) -> int:
    """Map probability of default to the 300-850 scale (lower PD = higher score)."""
    return round(SCORE_MIN + (SCORE_MAX - SCORE_MIN) * (1.0 - pd_value))


def to_band(score: int) -> str:
    for minimum, band in RISK_BANDS:
        if score >= minimum:
            return band
    return "D"


def score_customer(features: dict) -> ScoreResult:
    pd_value = probability_of_default(features)
    score = to_score(pd_value)
    return ScoreResult(
        customer_id=features["customer_id"],
        probability_of_default=round(pd_value, 6),
        score=score,
        risk_band=to_band(score),
    )
