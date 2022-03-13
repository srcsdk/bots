#!/usr/bin/env python3
"""generate detailed strategy comparison reports"""


def compare_strategies(results, benchmark_returns=None):
    """compare multiple strategy results side by side."""
    comparison = []
    for name, result in results.items():
        entry = {
            "strategy": name,
            "total_return": result.get("total_return_pct", 0),
            "sharpe": result.get("sharpe_ratio", 0),
            "max_drawdown": result.get("max_drawdown_pct", 0),
            "win_rate": result.get("win_rate", 0),
            "trades": result.get("total_trades", 0),
        }
        if benchmark_returns is not None:
            entry["alpha"] = round(
                entry["total_return"] - benchmark_returns, 2
            )
        comparison.append(entry)
    comparison.sort(key=lambda x: x["sharpe"], reverse=True)
    return comparison


def rank_strategies(comparison, weights=None):
    """rank strategies using weighted scoring."""
    if weights is None:
        weights = {
            "sharpe": 0.3,
            "total_return": 0.25,
            "max_drawdown": -0.2,
            "win_rate": 0.15,
            "trades": 0.1,
        }
    for entry in comparison:
        score = 0
        for metric, weight in weights.items():
            val = entry.get(metric, 0)
            score += val * weight
        entry["composite_score"] = round(score, 4)
    return sorted(comparison, key=lambda x: x["composite_score"],
                  reverse=True)


def format_comparison(comparison):
    """format comparison table for display."""
    lines = [
        f"{'strategy':<20} {'return':>8} {'sharpe':>8} "
        f"{'max dd':>8} {'win%':>6} {'trades':>7}",
        "-" * 65,
    ]
    for entry in comparison:
        lines.append(
            f"{entry['strategy']:<20} "
            f"{entry['total_return']:>7.1f}% "
            f"{entry['sharpe']:>8.2f} "
            f"{entry['max_drawdown']:>7.1f}% "
            f"{entry['win_rate']:>5.1f}% "
            f"{entry['trades']:>7d}"
        )
    return "\n".join(lines)


def strategy_correlation(results_a, results_b):
    """calculate return correlation between two strategies."""
    returns_a = results_a.get("daily_returns", [])
    returns_b = results_b.get("daily_returns", [])
    min_len = min(len(returns_a), len(returns_b))
    if min_len < 2:
        return 0
    a = returns_a[:min_len]
    b = returns_b[:min_len]
    mean_a = sum(a) / min_len
    mean_b = sum(b) / min_len
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(min_len))
    std_a = sum((x - mean_a) ** 2 for x in a) ** 0.5
    std_b = sum((x - mean_b) ** 2 for x in b) ** 0.5
    if std_a == 0 or std_b == 0:
        return 0
    return round(cov / (std_a * std_b), 4)


if __name__ == "__main__":
    results = {
        "ma_crossover": {
            "total_return_pct": 15.2, "sharpe_ratio": 1.1,
            "max_drawdown_pct": 8.5, "win_rate": 55.0,
            "total_trades": 24,
        },
        "rsi_mean_revert": {
            "total_return_pct": 12.8, "sharpe_ratio": 1.4,
            "max_drawdown_pct": 5.2, "win_rate": 62.0,
            "total_trades": 45,
        },
        "breakout": {
            "total_return_pct": 22.1, "sharpe_ratio": 0.9,
            "max_drawdown_pct": 15.3, "win_rate": 42.0,
            "total_trades": 18,
        },
    }
    comparison = compare_strategies(results, benchmark_returns=10.0)
    ranked = rank_strategies(comparison)
    print(format_comparison(ranked))
    print()
    for entry in ranked:
        print(f"  {entry['strategy']}: score={entry['composite_score']}")
