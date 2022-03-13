#!/usr/bin/env python3
"""detect recurring patterns in trading results"""

import statistics
from collections import defaultdict


def detect_time_patterns(trades, field="entry_time"):
    """find time-of-day patterns in successful trades."""
    hourly = defaultdict(list)
    for trade in trades:
        if field not in trade:
            continue
        hour = int(trade[field].split(":")[0]) if isinstance(
            trade[field], str
        ) else trade[field] % 24
        hourly[hour].append(trade.get("pnl_pct", 0))
    results = {}
    for hour, returns in hourly.items():
        results[hour] = {
            "trades": len(returns),
            "avg_return": round(statistics.mean(returns), 4),
            "win_rate": round(
                sum(1 for r in returns if r > 0) / len(returns) * 100, 1
            ),
        }
    return dict(sorted(results.items()))


def detect_day_patterns(trades):
    """find day-of-week patterns."""
    daily = defaultdict(list)
    for trade in trades:
        day = trade.get("day_of_week", 0)
        daily[day].append(trade.get("pnl_pct", 0))
    days = ["mon", "tue", "wed", "thu", "fri"]
    results = {}
    for day_num, returns in daily.items():
        if day_num < len(days):
            name = days[day_num]
        else:
            name = f"day_{day_num}"
        results[name] = {
            "trades": len(returns),
            "avg_return": round(statistics.mean(returns), 4),
        }
    return results


def detect_streak_patterns(returns, min_streak=3):
    """find winning and losing streaks."""
    streaks = []
    current = {"type": None, "length": 0, "total": 0}
    for ret in returns:
        streak_type = "win" if ret > 0 else "loss"
        if streak_type == current["type"]:
            current["length"] += 1
            current["total"] += ret
        else:
            if current["length"] >= min_streak:
                streaks.append(dict(current))
            current = {"type": streak_type, "length": 1, "total": ret}
    if current["length"] >= min_streak:
        streaks.append(current)
    return streaks


def detect_correlation(series_a, series_b):
    """calculate correlation between two return series."""
    n = min(len(series_a), len(series_b))
    if n < 3:
        return 0
    a = series_a[:n]
    b = series_b[:n]
    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
    std_a = statistics.pstdev(a)
    std_b = statistics.pstdev(b)
    if std_a == 0 or std_b == 0:
        return 0
    return round(cov / (std_a * std_b), 4)


def find_regime_shifts(returns, window=20):
    """detect shifts in market regime from return patterns."""
    if len(returns) < window * 2:
        return []
    shifts = []
    for i in range(window, len(returns) - window):
        before = statistics.mean(returns[i - window:i])
        after = statistics.mean(returns[i:i + window])
        vol_before = statistics.pstdev(returns[i - window:i])
        vol_after = statistics.pstdev(returns[i:i + window])
        if abs(after - before) > 2 * max(vol_before, vol_after, 0.001):
            shifts.append({
                "index": i,
                "before_mean": round(before, 4),
                "after_mean": round(after, 4),
                "magnitude": round(after - before, 4),
            })
    return shifts


if __name__ == "__main__":
    sample = [1.2, -0.5, 0.8, 1.5, -0.3, 2.1, -1.0, 0.4, 1.8, -0.2]
    streaks = detect_streak_patterns(sample, min_streak=2)
    print(f"streaks found: {len(streaks)}")
    corr = detect_correlation(sample, list(reversed(sample)))
    print(f"correlation: {corr}")
