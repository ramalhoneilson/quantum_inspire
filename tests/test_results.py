"""Unit tests for statistical calculations and result formatting."""

import math
from qi_starter.results import (
    canonicalize_counts,
    compute_probabilities,
    format_ascii_histogram,
    hellinger_distance,
    wilson_interval,
)


def test_canonicalize_counts():
    raw = {"01": 100, "10": 200, "00": 300}
    reversed_counts = canonicalize_counts(raw, reverse_bits=True)
    assert reversed_counts == {"10": 100, "01": 200, "00": 300}

    unreversed = canonicalize_counts(raw, reverse_bits=False)
    assert unreversed == raw


def test_compute_probabilities():
    counts = {"00": 250, "11": 750}
    probs = compute_probabilities(counts)
    assert math.isclose(probs["00"], 0.25)
    assert math.isclose(probs["11"], 0.75)


def test_wilson_interval():
    lower, upper = wilson_interval(500, 1000, confidence=0.95)
    assert 0.0 <= lower <= 0.5 <= upper <= 1.0
    assert math.isclose((lower + upper) / 2.0, 0.5, abs_tol=0.01)

    # Edge cases
    zero_l, zero_u = wilson_interval(0, 100, confidence=0.95)
    assert zero_l == 0.0
    assert zero_u > 0.0

    one_l, one_u = wilson_interval(100, 100, confidence=0.95)
    assert one_l < 1.0
    assert one_u == 1.0


def test_hellinger_distance():
    # Identical distributions
    p1 = {"00": 0.5, "11": 0.5}
    p2 = {"00": 0.5, "11": 0.5}
    assert math.isclose(hellinger_distance(p1, p2), 0.0)

    # Orthogonal distributions
    q1 = {"00": 1.0}
    q2 = {"11": 1.0}
    assert math.isclose(hellinger_distance(q1, q2), 1.0)


def test_format_ascii_histogram():
    counts = {"00": 500, "11": 500}
    rendered = format_ascii_histogram(counts)
    assert "|00>" in rendered
    assert "|11>" in rendered
    assert "█" in rendered
