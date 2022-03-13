#!/usr/bin/env python3
"""generate weekly performance summaries from simulation data"""

import statistics
from collections import defaultdict


def weekly_summary(trades, equity_curve):
    """generate weekly performance summary."""
    weekly = defaultdict(list)
    for trade in trades:
        week = trade.get("date", "")[:10]
        if len(week) >= 7:
            week_key = week[:7]
        else:
            week_key = "unknown"
        weekly[week_key].append(trade.get("pnl_pct", 0))
    summaries = []
    for week, returns in sorted(weekly.items()):
        total = sum(returns)
        wins = sum(1 for r in returns if r > 0)
        summaries.append({
            "week": week,
            "trades": len(returns),
            "total_return": round(total, 4),
            "avg_return": round(statistics.mean(returns), 4) if returns else 0,
            "win_rate": round(wins / len(returns) * 100, 1) if returns else 0,
            "best": round(max(returns), 4) if returns else 0,
            "worst": round(min(returns), 4) if returns else 0,
        })
    return summaries


def consistency_score(weekly_returns):
    """score how consistent weekly returns are."""
    if len(weekly_returns) < 4:
        return 0
    positive_weeks = sum(1 for r in weekly_returns if r > 0)
    consistency = positive_weeks / len(weekly_returns)
    if len(weekly_returns) >= 2:
        std = statistics.pstdev(weekly_returns)
        mean = statistics.mean(weekly_returns)
        cv = std / abs(mean) if mean != 0 else float("inf")
        stability = max(0, 1 - cv)
    else:
        stability = 0
    return round((consistency * 0.6 + stability * 0.4) * 100, 1)


def target_check(weekly_returns, target_pct=14):
    """check if strategy meets weekly return target."""
    if not weekly_returns:
        return {"met": False, "avg": 0, "weeks_above": 0}
    above = sum(1 for r in weekly_returns if r >= target_pct)
    return {
        "target": target_pct,
        "avg_weekly": round(statistics.mean(weekly_returns), 2),
        "weeks_above": above,
        "total_weeks": len(weekly_returns),
        "hit_rate": round(above / len(weekly_returns) * 100, 1),
        "met": statistics.mean(weekly_returns) >= target_pct,
    }


def compare_strategies(strategy_results):
    """compare multiple strategies on weekly performance."""
    comparison = []
    for name, results in strategy_results.items():
        weekly = [r.get("total_return", 0) for r in results]
        comparison.append({
            "strategy": name,
            "avg_weekly": round(statistics.mean(weekly), 4) if weekly else 0,
            "consistency": consistency_score(weekly),
            "weeks": len(weekly),
        })
    comparison.sort(key=lambda x: x["avg_weekly"], reverse=True)
    return comparison


if __name__ == "__main__":
    sample_returns = [12.5, 15.3, 8.2, 14.7, 11.0, 16.8, 13.5]
    score = consistency_score(sample_returns)
    print(f"consistency score: {score}")
    check = target_check(sample_returns, target_pct=14)
    for key, val in check.items():
        print(f"  {key}: {val}")
