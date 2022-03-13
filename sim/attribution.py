#!/usr/bin/env python3
"""attribute trading performance to individual indicators"""

import statistics


def calculate_attribution(trades, indicators):
    """calculate how much each indicator contributed to returns."""
    results = {}
    for name in indicators:
        matching = [t for t in trades if name in t.get("signals", [])]
        if not matching:
            results[name] = {"trades": 0, "avg_return": 0, "contribution": 0}
            continue
        returns = [t.get("pnl_pct", 0) for t in matching]
        results[name] = {
            "trades": len(matching),
            "avg_return": round(statistics.mean(returns), 4),
            "total_return": round(sum(returns), 4),
            "win_rate": round(
                sum(1 for r in returns if r > 0) / len(returns) * 100, 1
            ),
            "contribution": round(sum(returns) / max(len(trades), 1), 4),
        }
    return results


def rank_indicators(attribution):
    """rank indicators by contribution."""
    ranked = sorted(
        attribution.items(),
        key=lambda x: x[1].get("contribution", 0),
        reverse=True,
    )
    return [(name, data) for name, data in ranked]


def find_best_pairs(attribution, trades):
    """find indicator pairs that work best together."""
    names = list(attribution.keys())
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            matching = [
                t for t in trades
                if a in t.get("signals", []) and b in t.get("signals", [])
            ]
            if len(matching) < 3:
                continue
            returns = [t.get("pnl_pct", 0) for t in matching]
            pairs.append({
                "pair": (a, b),
                "trades": len(matching),
                "avg_return": round(statistics.mean(returns), 4),
                "combined_contribution": round(sum(returns) / len(trades), 4),
            })
    pairs.sort(key=lambda x: x["combined_contribution"], reverse=True)
    return pairs


def remove_weakest(attribution, trades, threshold=0.0):
    """identify indicators below contribution threshold."""
    weak = [
        name for name, data in attribution.items()
        if data.get("contribution", 0) < threshold
    ]
    return weak


if __name__ == "__main__":
    sample_trades = [
        {"pnl_pct": 2.5, "signals": ["rsi", "macd"]},
        {"pnl_pct": -1.0, "signals": ["rsi"]},
        {"pnl_pct": 3.0, "signals": ["macd", "volume"]},
        {"pnl_pct": -0.5, "signals": ["rsi", "volume"]},
    ]
    indicators = ["rsi", "macd", "volume"]
    attr = calculate_attribution(sample_trades, indicators)
    for name, data in attr.items():
        print(f"{name}: {data}")
    ranked = rank_indicators(attr)
    print(f"\nranked: {[r[0] for r in ranked]}")
