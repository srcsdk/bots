#!/usr/bin/env python3
"""combine signals from multiple strategies into consensus trades"""


def weighted_vote(signals, weights=None):
    """combine strategy signals using weighted voting.

    signals: list of signal dicts with 'direction' (-1, 0, 1)
    weights: optional list of weights per signal
    returns consensus direction and confidence.
    """
    if not signals:
        return {"direction": 0, "confidence": 0.0}

    n = len(signals)
    if weights is None:
        weights = [1.0] * n
    elif len(weights) != n:
        weights = [1.0] * n

    total_weight = sum(abs(w) for w in weights)
    if total_weight == 0:
        return {"direction": 0, "confidence": 0.0}

    weighted_sum = sum(
        s.get("direction", 0) * w
        for s, w in zip(signals, weights)
    )
    normalized = weighted_sum / total_weight
    direction = 1 if normalized > 0.1 else (-1 if normalized < -0.1 else 0)
    confidence = min(abs(normalized), 1.0)

    return {
        "direction": direction,
        "confidence": round(confidence, 4),
        "raw_score": round(normalized, 4),
        "agreement": _calc_agreement(signals),
    }


def _calc_agreement(signals):
    """measure how much strategies agree (0 to 1)."""
    if not signals:
        return 0.0
    directions = [s.get("direction", 0) for s in signals]
    non_zero = [d for d in directions if d != 0]
    if not non_zero:
        return 0.0
    positive = sum(1 for d in non_zero if d > 0)
    return round(max(positive, len(non_zero) - positive) / len(non_zero), 4)


def majority_vote(signals, threshold=0.6):
    """simple majority voting with configurable threshold."""
    if not signals:
        return 0
    directions = [s.get("direction", 0) for s in signals if s.get("direction", 0) != 0]
    if not directions:
        return 0
    buy_pct = sum(1 for d in directions if d > 0) / len(directions)
    if buy_pct >= threshold:
        return 1
    sell_pct = sum(1 for d in directions if d < 0) / len(directions)
    if sell_pct >= threshold:
        return -1
    return 0


def filter_by_confidence(signals, min_confidence=0.3):
    """only keep signals above confidence threshold."""
    return [s for s in signals if s.get("confidence", 0) >= min_confidence]


if __name__ == "__main__":
    signals = [
        {"direction": 1, "confidence": 0.8, "strategy": "momentum"},
        {"direction": 1, "confidence": 0.6, "strategy": "mean_rev"},
        {"direction": -1, "confidence": 0.4, "strategy": "sentiment"},
        {"direction": 1, "confidence": 0.9, "strategy": "trend"},
    ]
    result = weighted_vote(signals, [1.0, 0.8, 0.5, 1.2])
    print(f"consensus: dir={result['direction']} "
          f"conf={result['confidence']:.2f} "
          f"agree={result['agreement']:.2f}")
    print(f"majority: {majority_vote(signals)}")
