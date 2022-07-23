#!/usr/bin/env python3
"""side-by-side backtest comparison tools"""

import json
import os


def load_results(filepath):
    """load backtest results from json."""
    with open(filepath) as f:
        return json.load(f)


def compare_returns(results_a, results_b):
    """compare returns between two backtests."""
    return {
        "a_return": results_a.get("total_return_pct", 0),
        "b_return": results_b.get("total_return_pct", 0),
        "difference": round(
            results_a.get("total_return_pct", 0)
            - results_b.get("total_return_pct", 0), 2
        ),
    }


def compare_risk(results_a, results_b):
    """compare risk metrics between two backtests."""
    return {
        "a_sharpe": results_a.get("sharpe_ratio", 0),
        "b_sharpe": results_b.get("sharpe_ratio", 0),
        "a_drawdown": results_a.get("max_drawdown_pct", 0),
        "b_drawdown": results_b.get("max_drawdown_pct", 0),
    }


def rank_results(results_list, metric="sharpe_ratio"):
    """rank multiple backtest results by a metric."""
    ranked = sorted(
        results_list,
        key=lambda r: r.get(metric, 0),
        reverse=True,
    )
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return ranked


def equity_correlation(curve_a, curve_b):
    """calculate correlation between two equity curves."""
    min_len = min(len(curve_a), len(curve_b))
    if min_len < 2:
        return 0
    a = curve_a[:min_len]
    b = curve_b[:min_len]
    mean_a = sum(a) / min_len
    mean_b = sum(b) / min_len
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(min_len))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((x - mean_b) ** 2 for x in b)
    denom = (var_a * var_b) ** 0.5
    if denom == 0:
        return 0
    return round(cov / denom, 4)


def format_comparison(name_a, results_a, name_b, results_b):
    """format comparison table."""
    metrics = [
        "total_return_pct", "sharpe_ratio", "max_drawdown_pct",
        "win_rate", "total_trades",
    ]
    lines = [f"{'metric':<20} {name_a:>12} {name_b:>12}"]
    lines.append("-" * 46)
    for metric in metrics:
        val_a = results_a.get(metric, "n/a")
        val_b = results_b.get(metric, "n/a")
        lines.append(f"{metric:<20} {str(val_a):>12} {str(val_b):>12}")
    return "\n".join(lines)


def save_comparison(filepath, name_a, results_a, name_b, results_b):
    """save comparison to file."""
    data = {
        "strategies": {name_a: results_a, name_b: results_b},
        "returns": compare_returns(results_a, results_b),
        "risk": compare_risk(results_a, results_b),
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    a = {"total_return_pct": 15.2, "sharpe_ratio": 1.1,
         "max_drawdown_pct": 8.5, "win_rate": 55, "total_trades": 24}
    b = {"total_return_pct": 12.8, "sharpe_ratio": 1.4,
         "max_drawdown_pct": 5.2, "win_rate": 62, "total_trades": 45}
    print(format_comparison("ma_cross", a, "rsi_revert", b))
