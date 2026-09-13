"""Statistical parsing, bit-endianness normalization, and presentation of quantum results."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


def canonicalize_counts(
    counts: Dict[str, int], reverse_bits: bool = True
) -> Dict[str, int]:
    """Normalize bitstring keys to the desired endianness.

    Qiskit and Quantum Inspire return measurement results in little-endian order,
    where qubit 0 is the RIGHTMOST character:
        Key '01' means qubit 1 is '0' and qubit 0 is '1'.
    Most textbooks and Quanifi's canonical convention use big-endian order,
    where qubit 0 is the LEFTMOST character:
        Key '10' means qubit 0 is '1' and qubit 1 is '0'.

    Args:
        counts: Dictionary of {bitstring: count}.
        reverse_bits: If True, reverses each bitstring key.

    Returns:
        Dictionary of counts with reversed bit order.
    """
    if not reverse_bits:
        return dict(counts)
    return {k[::-1]: v for k, v in counts.items()}


def compute_probabilities(counts: Dict[str, int]) -> Dict[str, float]:
    """Convert measurement shot counts into normalized empirical probabilities.

    Args:
        counts: Dictionary of {bitstring: count}.

    Returns:
        Dictionary of {bitstring: probability}, sorted by bitstring.
    """
    total = sum(counts.values())
    if total == 0:
        return {k: 0.0 for k in counts}
    return {k: round(v / total, 6) for k, v in sorted(counts.items())}


def wilson_interval(
    successes: int, total: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion.

    Used to place rigorous confidence bounds on quantum algorithm success probabilities
    without relying on the normal approximation (which breaks down near 0 and 1).

    Args:
        successes: Number of successful shots.
        total: Total number of shots executed.
        confidence: Confidence level (default: 0.95 for 95% confidence).

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    if total <= 0:
        return (0.0, 0.0)

    # Standard normal quantile z for common confidence levels
    # Defaulting to 1.95996 for 95% confidence
    z_values = {0.90: 1.64485, 0.95: 1.95996, 0.99: 2.57583}
    z = z_values.get(round(confidence, 2), 1.95996)

    p_hat = successes / total
    denominator = 1.0 + (z**2) / total
    center = (p_hat + (z**2) / (2 * total)) / denominator
    spread = (
        z
        * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z**2) / (4 * (total**2)))
        / denominator
    )

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return (round(lower, 5), round(upper, 5))


def hellinger_distance(p: Dict[str, float], q: Dict[str, float]) -> float:
    """Compute the Hellinger distance between two probability distributions.

    Hellinger distance is bounded in [0, 1], where 0 indicates identical distributions
    and 1 indicates orthogonal (completely disjoint) distributions.

    Args:
        p: Empirical or ideal probability distribution {state: prob}.
        q: Comparison probability distribution {state: prob}.

    Returns:
        float: Hellinger distance between p and q.
    """
    all_keys = set(p.keys()) | set(q.keys())
    sum_diff_sq = sum(
        (math.sqrt(p.get(k, 0.0)) - math.sqrt(q.get(k, 0.0))) ** 2 for k in all_keys
    )
    return float(math.sqrt(sum_diff_sq / 2.0))


def format_ascii_histogram(
    counts_or_probs: Dict[str, Any], max_width: int = 35
) -> str:
    """Generate a clean ASCII bar chart of measurement results for terminal display.

    Args:
        counts_or_probs: Dictionary of {bitstring: count} or {bitstring: prob}.
        max_width: Maximum character width of the rendered bars.

    Returns:
        Formatted multi-line string.
    """
    if not counts_or_probs:
        return "  (no measurements recorded)"

    total = sum(counts_or_probs.values())
    is_prob = math.isclose(total, 1.0, abs_tol=1e-3)

    probs = (
        counts_or_probs
        if is_prob
        else {k: v / total for k, v in counts_or_probs.items()}
    )
    max_p = max(probs.values()) if probs else 1.0
    if max_p <= 0.0:
        max_p = 1.0

    lines = []
    for state in sorted(probs.keys()):
        p = probs[state]
        bar_len = int(round((p / max_p) * max_width))
        bar = "█" * bar_len
        pct = p * 100.0

        if is_prob:
            lines.append(f"  |{state}> : {pct:6.2f}%  [{bar:<{max_width}}]")
        else:
            cnt = counts_or_probs[state]
            lines.append(f"  |{state}> : {cnt:5d} ({pct:6.2f}%) [{bar:<{max_width}}]")

    return "\n".join(lines)
