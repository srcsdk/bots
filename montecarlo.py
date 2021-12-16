#!/usr/bin/env python3
"""monte carlo simulation for portfolio risk and return estimation"""

import sys
import random
from ohlc import fetch_ohlc
from correlation import daily_returns


def simulate_paths(returns, days=252, n_sims=1000, initial=10000, seed=None):
    """simulate future price paths using bootstrapped historical returns.

    randomly samples from historical daily returns to generate
    possible future equity curves.
    """
    if seed is not None:
        random.seed(seed)

    if not returns:
        return []

    paths = []
    for _ in range(n_sims):
        equity = initial
        path = [equity]
        for _ in range(days):
            daily_ret = random.choice(returns)
            equity *= (1 + daily_ret)
            path.append(round(equity, 2))
        paths.append(path)

    return paths


def path_statistics(paths, confidence=0.95):
    """calculate statistics across simulated paths.

    returns percentile-based confidence intervals and summary stats
    """
    if not paths:
        return {}

    final_values = [p[-1] for p in paths]
    final_values.sort()
    n = len(final_values)

    lower_idx = int(n * (1 - confidence))
    upper_idx = int(n * confidence) - 1

    median_idx = n // 2
    mean_final = sum(final_values) / n

    returns_pct = [(v - paths[0][0]) / paths[0][0] * 100 for v in final_values]

    return {
        "n_simulations": n,
        "initial": paths[0][0],
        "mean_final": round(mean_final, 2),
        "median_final": round(final_values[median_idx], 2),
        "best_case": round(final_values[-1], 2),
        "worst_case": round(final_values[0], 2),
        "ci_lower": round(final_values[lower_idx], 2),
        "ci_upper": round(final_values[upper_idx], 2),
        "prob_profit": round(sum(1 for v in final_values if v > paths[0][0]) / n * 100, 1),
        "prob_loss_10pct": round(
            sum(1 for v in final_values if v < paths[0][0] * 0.9) / n * 100, 1
        ),
        "mean_return_pct": round(sum(returns_pct) / n, 2),
        "median_return_pct": round(returns_pct[median_idx], 2),
    }


def drawdown_distribution(paths):
    """analyze maximum drawdown across simulated paths"""
    drawdowns = []
    for path in paths:
        peak = path[0]
        max_dd = 0
        for val in path:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        drawdowns.append(round(max_dd * 100, 2))

    drawdowns.sort()
    n = len(drawdowns)
    return {
        "mean_dd": round(sum(drawdowns) / n, 2),
        "median_dd": drawdowns[n // 2],
        "worst_dd": drawdowns[-1],
        "dd_95th": drawdowns[int(n * 0.95)],
        "prob_dd_gt_20": round(sum(1 for d in drawdowns if d > 20) / n * 100, 1),
    }


def run_simulation(ticker, period="2y", days=252, n_sims=1000, capital=10000):
    """run full monte carlo simulation for a ticker"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    closes = [r["close"] for r in rows]
    returns = daily_returns(closes)

    paths = simulate_paths(returns, days, n_sims, capital)
    stats = path_statistics(paths)
    dd_stats = drawdown_distribution(paths)

    return {
        "ticker": ticker,
        "historical_days": len(returns),
        "simulation_days": days,
        "n_simulations": n_sims,
        "stats": stats,
        "drawdown": dd_stats,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python montecarlo.py <ticker> [sims] [days]")
        print("  defaults: 1000 simulations, 252 days (1 year)")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    n_sims = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 252

    print(f"monte carlo: {ticker} ({n_sims} sims, {days} days)")
    result = run_simulation(ticker, n_sims=n_sims, days=days)

    if result is None:
        print("insufficient data")
        sys.exit(1)

    s = result["stats"]
    print(f"\nresults ({result['historical_days']} historical observations):")
    print(f"  mean final:     ${s['mean_final']:,.2f} ({s['mean_return_pct']:+.2f}%)")
    print(f"  median final:   ${s['median_final']:,.2f} ({s['median_return_pct']:+.2f}%)")
    print(f"  95% ci:         ${s['ci_lower']:,.2f} - ${s['ci_upper']:,.2f}")
    print(f"  best/worst:     ${s['best_case']:,.2f} / ${s['worst_case']:,.2f}")
    print(f"  prob profit:    {s['prob_profit']}%")
    print(f"  prob >10% loss: {s['prob_loss_10pct']}%")

    d = result["drawdown"]
    print("\ndrawdown analysis:")
    print(f"  mean dd:        {d['mean_dd']}%")
    print(f"  median dd:      {d['median_dd']}%")
    print(f"  95th pctl dd:   {d['dd_95th']}%")
    print(f"  worst dd:       {d['worst_dd']}%")
    print(f"  prob dd >20%:   {d['prob_dd_gt_20']}%")
