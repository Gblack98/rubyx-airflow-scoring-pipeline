import random

import pytest

from scoring.stability import (
    ScoreDriftError,
    enforce_stability,
    population_stability_index,
)


def sample(mean: int, n: int = 5000, seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    return [max(300, min(850, round(rng.gauss(mean, 60)))) for _ in range(n)]


def test_identical_distributions_have_near_zero_psi():
    scores = sample(mean=650)
    assert population_stability_index(scores, scores) == pytest.approx(0.0, abs=1e-9)


def test_small_shift_stays_under_threshold():
    psi = population_stability_index(sample(650), sample(655, seed=2))
    assert psi < 0.10


def test_large_shift_is_detected():
    psi = population_stability_index(sample(650), sample(520, seed=2))
    assert psi > 0.25


def test_enforce_raises_on_drift():
    with pytest.raises(ScoreDriftError, match="PSI"):
        enforce_stability(sample(650), sample(500, seed=2))


def test_first_run_with_empty_baseline_passes():
    assert enforce_stability([], sample(650)) == 0.0
