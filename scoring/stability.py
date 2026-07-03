"""Population Stability Index between two score distributions.

A silent input-data change (broken upstream join, currency drift) shifts the
score distribution long before anyone reads a dashboard. The PSI gate fails
the DAG run instead of publishing scores nobody should trust.

Rule of thumb: PSI < 0.10 stable, 0.10-0.25 monitor, > 0.25 investigate.
"""

from __future__ import annotations

import math

DEFAULT_BINS = (300, 450, 550, 600, 650, 700, 750, 800, 851)
PSI_ALERT_THRESHOLD = 0.25
_EPSILON = 1e-4  # avoids log(0) on empty bins


class ScoreDriftError(Exception):
    """Score distribution drifted beyond the accepted threshold."""


def _bin_shares(scores: list[int], bins: tuple[int, ...]) -> list[float]:
    counts = [0] * (len(bins) - 1)
    for score in scores:
        for i in range(len(bins) - 1):
            if bins[i] <= score < bins[i + 1]:
                counts[i] += 1
                break
    total = max(len(scores), 1)
    return [max(count / total, _EPSILON) for count in counts]


def population_stability_index(
    baseline: list[int], current: list[int], bins: tuple[int, ...] = DEFAULT_BINS
) -> float:
    expected = _bin_shares(baseline, bins)
    actual = _bin_shares(current, bins)
    return sum(
        (a - e) * math.log(a / e) for e, a in zip(expected, actual)
    )


def enforce_stability(
    baseline: list[int],
    current: list[int],
    threshold: float = PSI_ALERT_THRESHOLD,
) -> float:
    """Return the PSI, raising ScoreDriftError above the threshold.

    An empty baseline (first ever run) passes: there is nothing to drift from.
    """
    if not baseline:
        return 0.0
    psi = population_stability_index(baseline, current)
    if psi > threshold:
        raise ScoreDriftError(
            f"score PSI {psi:.3f} exceeds {threshold} — "
            f"scores withheld, investigate upstream features"
        )
    return psi
