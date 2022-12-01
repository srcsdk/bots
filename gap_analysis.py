#!/usr/bin/env python3
"""gap analysis with fill probability estimation"""


def detect_gaps(opens, closes, min_gap_pct=0.5):
    """detect price gaps between sessions.

    a gap occurs when today's open differs significantly from
    yesterday's close.
    """
    if len(opens) < 2 or len(closes) < 2:
        return []
    gaps = []
    for i in range(1, len(opens)):
        gap = opens[i] - closes[i - 1]
        gap_pct = gap / closes[i - 1] * 100
        if abs(gap_pct) >= min_gap_pct:
            gaps.append({
                "idx": i,
                "direction": "up" if gap > 0 else "down",
                "gap_size": round(abs(gap), 2),
                "gap_pct": round(gap_pct, 2),
                "prev_close": closes[i - 1],
                "open": opens[i],
            })
    return gaps


def gap_fill_check(gaps, closes):
    """check if gaps were filled in subsequent sessions."""
    for gap in gaps:
        idx = gap["idx"]
        gap["filled"] = False
        gap["fill_bars"] = None
        target = gap["prev_close"]
        for j in range(idx, min(idx + 20, len(closes))):
            if gap["direction"] == "up" and closes[j] <= target:
                gap["filled"] = True
                gap["fill_bars"] = j - idx
                break
            elif gap["direction"] == "down" and closes[j] >= target:
                gap["filled"] = True
                gap["fill_bars"] = j - idx
                break
    return gaps


def fill_probability(gaps):
    """estimate gap fill probability from historical gaps."""
    if not gaps:
        return {"up": 0, "down": 0, "overall": 0}
    up_gaps = [g for g in gaps if g["direction"] == "up"]
    down_gaps = [g for g in gaps if g["direction"] == "down"]
    up_filled = sum(1 for g in up_gaps if g.get("filled"))
    down_filled = sum(1 for g in down_gaps if g.get("filled"))
    total_filled = up_filled + down_filled
    return {
        "up_fill_rate": round(up_filled / len(up_gaps) * 100, 1) if up_gaps else 0,
        "down_fill_rate": round(down_filled / len(down_gaps) * 100, 1) if down_gaps else 0,
        "overall_fill_rate": round(total_filled / len(gaps) * 100, 1),
        "avg_fill_time": round(
            sum(g["fill_bars"] for g in gaps if g.get("fill_bars") is not None)
            / max(1, total_filled), 1
        ),
    }


if __name__ == "__main__":
    import random
    closes = [100]
    opens = [100]
    for _ in range(200):
        gap = random.gauss(0, 0.8)
        opens.append(closes[-1] * (1 + gap / 100))
        closes.append(opens[-1] * (1 + random.gauss(0, 0.5) / 100))
    gaps = detect_gaps(opens, closes, min_gap_pct=0.3)
    gaps = gap_fill_check(gaps, closes)
    prob = fill_probability(gaps)
    print(f"gaps found: {len(gaps)}")
    for k, v in prob.items():
        print(f"  {k}: {v}")
