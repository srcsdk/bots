#!/usr/bin/env python3
"""market data validation and cleaning"""


def validate_ohlcv(bars):
    """validate ohlcv data integrity."""
    issues = []
    for i, bar in enumerate(bars):
        if bar.get("high", 0) < bar.get("low", 0):
            issues.append({"index": i, "issue": "high < low"})
        if bar.get("close", 0) > bar.get("high", 0):
            issues.append({"index": i, "issue": "close > high"})
        if bar.get("close", 0) < bar.get("low", 0):
            issues.append({"index": i, "issue": "close < low"})
        if bar.get("open", 0) > bar.get("high", 0):
            issues.append({"index": i, "issue": "open > high"})
        if bar.get("open", 0) < bar.get("low", 0):
            issues.append({"index": i, "issue": "open < low"})
        if bar.get("volume", 0) < 0:
            issues.append({"index": i, "issue": "negative volume"})
        if any(bar.get(f, 0) <= 0 for f in ["open", "high", "low", "close"]):
            issues.append({"index": i, "issue": "non-positive price"})
    return issues


def detect_gaps(bars, max_gap_pct=10.0):
    """detect price gaps between bars."""
    gaps = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1].get("close", 0)
        curr_open = bars[i].get("open", 0)
        if prev_close > 0:
            gap_pct = abs(curr_open - prev_close) / prev_close * 100
            if gap_pct > max_gap_pct:
                gaps.append({
                    "index": i,
                    "gap_pct": round(gap_pct, 2),
                    "prev_close": prev_close,
                    "open": curr_open,
                })
    return gaps


def detect_outliers(values, std_threshold=3):
    """detect statistical outliers in a series."""
    if len(values) < 10:
        return []
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    if std == 0:
        return []
    outliers = []
    for i, v in enumerate(values):
        z_score = abs(v - mean) / std
        if z_score > std_threshold:
            outliers.append({
                "index": i, "value": v,
                "z_score": round(z_score, 2),
            })
    return outliers


def fill_missing_bars(bars, date_field="date"):
    """forward-fill missing price data."""
    if not bars:
        return bars
    filled = [bars[0]]
    for bar in bars[1:]:
        for field in ["open", "high", "low", "close"]:
            if bar.get(field) is None or bar.get(field) == 0:
                bar[field] = filled[-1].get(field, 0)
        filled.append(bar)
    return filled


def data_quality_score(bars):
    """overall data quality score 0-100."""
    if not bars:
        return 0
    issues = validate_ohlcv(bars)
    gaps = detect_gaps(bars)
    closes = [b.get("close", 0) for b in bars]
    outliers = detect_outliers(closes)
    total_issues = len(issues) + len(gaps) + len(outliers)
    penalty = min(total_issues / len(bars) * 100, 100)
    return round(100 - penalty, 1)


if __name__ == "__main__":
    bars = [
        {"open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000},
        {"open": 103, "high": 107, "low": 101, "close": 106, "volume": 1200},
        {"open": 106, "high": 108, "low": 90, "close": 92, "volume": 5000},
        {"open": 92, "high": 95, "low": 91, "close": 94, "volume": 800},
    ]
    issues = validate_ohlcv(bars)
    print(f"validation issues: {len(issues)}")
    score = data_quality_score(bars)
    print(f"data quality: {score}%")
