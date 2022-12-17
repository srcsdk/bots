#!/usr/bin/env python3
# improved: handles pre-market and after-hours moves
"""post-earnings announcement drift (pead) detector.

detects probable earnings dates from volume spikes + price gaps.
measures drift direction and magnitude over 1/5/10/20 days post-event.
scores drift persistence for trade planning.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma


def detect_earnings_events(rows, vol_threshold=2.5, gap_threshold=2.0):
    """detect probable earnings dates from volume spikes and price gaps.

    earnings typically cause: volume > 2.5x average, gap > 2%
    """
    if len(rows) < 30:
        return []

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    vol_avg = sma(volumes, 20)

    events = []
    for i in range(1, len(rows)):
        if vol_avg[i] is None or vol_avg[i] == 0:
            continue

        vol_ratio = volumes[i] / vol_avg[i]
        gap_pct = abs(rows[i]["open"] - closes[i - 1]) / closes[i - 1] * 100
        day_move = (closes[i] - closes[i - 1]) / closes[i - 1] * 100

        if vol_ratio >= vol_threshold and gap_pct >= gap_threshold:
            direction = "positive" if day_move > 0 else "negative"
            events.append({
                "index": i,
                "date": rows[i]["date"],
                "price": closes[i],
                "prev_close": closes[i - 1],
                "gap_pct": round(gap_pct, 2),
                "day_move_pct": round(day_move, 2),
                "vol_ratio": round(vol_ratio, 1),
                "direction": direction,
            })

    return events


def measure_drift(rows, event_index, windows=(1, 5, 10, 20)):
    """measure price drift after an earnings event over multiple windows"""
    closes = [r["close"] for r in rows]
    base_price = closes[event_index]
    drifts = {}

    for w in windows:
        end_idx = event_index + w
        if end_idx >= len(closes):
            drifts[f"{w}d"] = None
            continue
        drift = (closes[end_idx] - base_price) / base_price * 100
        drifts[f"{w}d"] = round(drift, 2)

    return drifts


def score_persistence(drifts, direction):
    """score how persistent the drift is in the earnings direction.

    higher score = drift continues in same direction as initial move.
    range: -100 to 100
    """
    sign = 1 if direction == "positive" else -1
    score = 0
    weights = {"1d": 10, "5d": 25, "10d": 30, "20d": 35}

    for key, weight in weights.items():
        val = drifts.get(key)
        if val is None:
            continue
        if (val * sign) > 0:
            score += weight
        elif (val * sign) < 0:
            score -= weight

    return score


def analyze(ticker, period="1y"):
    """analyze post-earnings drift for a ticker.

    returns detected earnings events with drift measurements and persistence scores.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return None

    events = detect_earnings_events(rows)
    if not events:
        return {"ticker": ticker, "events": [], "summary": "no earnings events detected"}

    results = []
    for event in events:
        drifts = measure_drift(rows, event["index"])
        persistence = score_persistence(drifts, event["direction"])

        results.append({
            "date": event["date"],
            "direction": event["direction"],
            "gap_pct": event["gap_pct"],
            "day_move_pct": event["day_move_pct"],
            "vol_ratio": event["vol_ratio"],
            "drift": drifts,
            "persistence_score": persistence,
        })

    positive_events = [r for r in results if r["direction"] == "positive"]
    negative_events = [r for r in results if r["direction"] == "negative"]

    avg_pos_persistence = 0
    avg_neg_persistence = 0
    if positive_events:
        avg_pos_persistence = round(sum(r["persistence_score"] for r in positive_events) / len(positive_events), 1)
    if negative_events:
        avg_neg_persistence = round(sum(r["persistence_score"] for r in negative_events) / len(negative_events), 1)

    return {
        "ticker": ticker,
        "events": results,
        "total_events": len(results),
        "positive_events": len(positive_events),
        "negative_events": len(negative_events),
        "avg_pos_persistence": avg_pos_persistence,
        "avg_neg_persistence": avg_neg_persistence,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python earnings.py <ticker> [period]")
        print("  detects earnings events and measures post-announcement drift")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"pead analysis: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result or not result["events"]:
        print("no earnings events detected")
        sys.exit(0)

    print(f"\n  detected events: {result['total_events']}")
    print(f"  positive: {result['positive_events']}  negative: {result['negative_events']}")
    print(f"  avg persistence (pos): {result['avg_pos_persistence']}")
    print(f"  avg persistence (neg): {result['avg_neg_persistence']}")

    print("\nevents:")
    for e in result["events"]:
        drift_str = "  ".join(
            f"{k}={v:+.2f}%" if v is not None else f"{k}=n/a"
            for k, v in e["drift"].items()
        )
        print(f"  {e['date']}  {e['direction']:>8}  gap={e['gap_pct']:+.1f}%  "
              f"vol={e['vol_ratio']:.1f}x  persist={e['persistence_score']:+d}")
        print(f"    drift: {drift_str}")
