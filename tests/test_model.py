from scoring.model import (
    MODEL_VERSION,
    SCORE_MAX,
    SCORE_MIN,
    score_customer,
    to_band,
    to_score,
)


def features(**overrides):
    base = {
        "customer_id": "C000001",
        "days_since_last_tx": 5,
        "mobile_tx_ratio": 0.8,
        "monthly_spend_to_income_ratio": 0.3,
        "tx_count_30d": 20,
        "intl_tx_ratio": 0.02,
    }
    base.update(overrides)
    return base


def test_score_is_bounded_and_versioned():
    result = score_customer(features())
    assert SCORE_MIN <= result.score <= SCORE_MAX
    assert 0.0 < result.probability_of_default < 1.0
    assert result.model_version == MODEL_VERSION


def test_riskier_behavior_lowers_score():
    healthy = score_customer(features())
    risky = score_customer(
        features(days_since_last_tx=200, mobile_tx_ratio=0.1,
                 monthly_spend_to_income_ratio=2.5, tx_count_30d=0)
    )
    assert risky.score < healthy.score
    assert risky.probability_of_default > healthy.probability_of_default


def test_missing_features_default_to_zero():
    result = score_customer({"customer_id": "C000002"})
    assert SCORE_MIN <= result.score <= SCORE_MAX


def test_deterministic():
    assert score_customer(features()) == score_customer(features())


def test_band_mapping():
    assert to_band(800) == "A"
    assert to_band(700) == "B"
    assert to_band(600) == "C"
    assert to_band(400) == "D"


def test_pd_to_score_is_monotonic():
    assert to_score(0.05) > to_score(0.5) > to_score(0.95)
