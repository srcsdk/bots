#!/usr/bin/env python3
"""correlation breakdown detector for regime shifts"""

import math


def rolling_correlation(x, y, window=60):
    """calculate rolling pearson correlation between two series."""
    if len(x) != len(y) or len(x) < window:
        return []
    result = [None] * (window - 1)
    for i in range(window - 1, len(x)):
        xs = x[i - window + 1:i + 1]
        ys = y[i - window + 1:i + 1]
        mx = sum(xs) / window
        my = sum(ys) / window
        cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / window
        sx = math.sqrt(sum((a - mx) ** 2 for a in xs) / window)
        sy = math.sqrt(sum((b - my) ** 2 for b in ys) / window)
        if sx > 0 and sy > 0:
            result.append(cov / (sx * sy))
        else:
            result.append(0.0)
    return result


def detect_breakdown(correlations, threshold=0.3, min_duration=5):
    """detect periods where correlation breaks down significantly.

    a breakdown is when correlation drops by more than threshold
    from its recent average.
    """
    if len(correlations) < 30:
        return []
    events = []
    valid = [c for c in correlations if c is not None]
    if not valid:
        return []
    baseline = sum(valid[:30]) / 30
    in_breakdown = False
    start_idx = 0
    for i, corr in enumerate(correlations):
        if corr is None:
            continue
        deviation = abs(corr - baseline)
        if deviation > threshold and not in_breakdown:
            in_breakdown = True
            start_idx = i
        elif deviation <= threshold and in_breakdown:
            duration = i - start_idx
            if duration >= min_duration:
                events.append({
                    "start_idx": start_idx,
                    "end_idx": i,
                    "duration": duration,
                    "min_corr": round(min(
                        c for c in correlations[start_idx:i] if c is not None
                    ), 4),
                    "baseline": round(baseline, 4),
                })
            in_breakdown = False
        if i >= 30:
            recent = [c for c in correlations[i - 29:i + 1] if c is not None]
            if recent:
                baseline = sum(recent) / len(recent)
    return events


def regime_label(correlation):
    """label correlation regime."""
    if correlation is None:
        return "unknown"
    if correlation > 0.7:
        return "high_positive"
    elif correlation > 0.3:
        return "moderate_positive"
    elif correlation > -0.3:
        return "uncorrelated"
    elif correlation > -0.7:
        return "moderate_negative"
    return "high_negative"


if __name__ == "__main__":
    import random
    n = 300
    x = [random.gauss(0, 1) for _ in range(n)]
    y = [xi * 0.8 + random.gauss(0, 0.5) for xi in x]
    for i in range(150, 180):
        y[i] = random.gauss(0, 1)
    corrs = rolling_correlation(x, y, 30)
    events = detect_breakdown(corrs)
    print(f"breakdown events: {len(events)}")
    for e in events:
        print(f"  bars {e['start_idx']}-{e['end_idx']} "
              f"duration={e['duration']} min_corr={e['min_corr']}")
