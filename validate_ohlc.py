#!/usr/bin/env python3
"""validate ohlc data quality and detect anomalies"""


def validate_bar(bar):
    """check single ohlc bar for data integrity.

    returns list of issues found (empty if valid).
    """
    issues = []
    required = ("open", "high", "low", "close")
    for field in required:
        if field not in bar:
            issues.append(f"missing {field}")
            return issues
        val = bar[field]
        if not isinstance(val, (int, float)):
            issues.append(f"{field} not numeric: {type(val)}")
        elif val <= 0:
            issues.append(f"{field} non-positive: {val}")

    if not issues:
        if bar["high"] < bar["low"]:
            issues.append(f"high ({bar['high']}) < low ({bar['low']})")
        if bar["open"] > bar["high"] or bar["open"] < bar["low"]:
            issues.append("open outside high-low range")
        if bar["close"] > bar["high"] or bar["close"] < bar["low"]:
            issues.append("close outside high-low range")

    volume = bar.get("volume", 0)
    if isinstance(volume, (int, float)) and volume < 0:
        issues.append(f"negative volume: {volume}")

    return issues


def validate_series(bars, max_gap_pct=20.0):
    """validate a series of ohlc bars.

    checks for gaps, missing dates, and price anomalies.
    returns dict with summary and per-bar issues.
    """
    if not bars:
        return {"valid": False, "error": "empty series"}

    all_issues = {}
    gaps = []

    for i, bar in enumerate(bars):
        bar_issues = validate_bar(bar)
        if bar_issues:
            all_issues[i] = bar_issues

        if i > 0:
            prev_close = bars[i - 1]["close"]
            if prev_close > 0:
                gap_pct = abs(bar["open"] - prev_close) / prev_close * 100
                if gap_pct > max_gap_pct:
                    gaps.append({
                        "index": i,
                        "date": bar.get("date", ""),
                        "gap_pct": round(gap_pct, 2),
                        "prev_close": prev_close,
                        "open": bar["open"],
                    })

    return {
        "valid": len(all_issues) == 0,
        "total_bars": len(bars),
        "invalid_bars": len(all_issues),
        "large_gaps": len(gaps),
        "issues": all_issues,
        "gaps": gaps,
    }


def detect_gaps(bars, min_gap_pct=2.0):
    """find all price gaps in a series."""
    gaps = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1]["close"]
        if prev_close <= 0:
            continue
        gap = (bars[i]["open"] - prev_close) / prev_close * 100
        if abs(gap) >= min_gap_pct:
            gaps.append({
                "index": i,
                "date": bars[i].get("date", ""),
                "gap_pct": round(gap, 2),
                "direction": "up" if gap > 0 else "down",
            })
    return gaps


def fill_forward(bars):
    """fill missing values using last known good data."""
    if not bars:
        return bars
    cleaned = []
    last_good = None
    for bar in bars:
        issues = validate_bar(bar)
        if not issues:
            last_good = bar
            cleaned.append(dict(bar))
        elif last_good:
            filled = dict(last_good)
            filled["date"] = bar.get("date", last_good.get("date", ""))
            filled["volume"] = 0
            cleaned.append(filled)
    return cleaned


if __name__ == "__main__":
    bars = [
        {"date": "2022-01-03", "open": 100, "high": 105,
         "low": 98, "close": 103, "volume": 1000},
        {"date": "2022-01-04", "open": 103, "high": 107,
         "low": 101, "close": 106, "volume": 1200},
        {"date": "2022-01-05", "open": 130, "high": 135,
         "low": 128, "close": 132, "volume": 5000},
    ]
    result = validate_series(bars)
    print(f"valid: {result['valid']}, gaps: {result['large_gaps']}")
    gaps = detect_gaps(bars)
    for g in gaps:
        print(f"  {g['date']}: {g['direction']} gap {g['gap_pct']}%")
