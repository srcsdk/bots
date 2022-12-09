#!/usr/bin/env python3
# updated: percentile-based confidence intervals
"""monte carlo simulation for strategy risk analysis"""

import math
import random


def geometric_brownian_motion(s0, mu, sigma, dt, n_steps):
    """simulate a single price path using gbm."""
    path = [s0]
    for _ in range(n_steps):
        z = random.gauss(0, 1)
        s_next = path[-1] * math.exp((mu - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z)
        path.append(s_next)
    return path


def simulate_paths(s0, mu, sigma, days=252, n_paths=1000):
    """generate multiple simulated price paths."""
    dt = 1 / 252
    paths = []
    for _ in range(n_paths):
        path = geometric_brownian_motion(s0, mu, sigma, dt, days)
        paths.append(path)
    return paths


def path_statistics(paths):
    """calculate statistics across all simulated paths."""
    final_prices = [p[-1] for p in paths]
    returns = [(p[-1] - p[0]) / p[0] for p in paths]
    drawdowns = []
    for path in paths:
        peak = path[0]
        max_dd = 0
        for price in path:
            peak = max(peak, price)
            dd = (peak - price) / peak
            max_dd = max(max_dd, dd)
        drawdowns.append(max_dd)
    final_prices.sort()
    n = len(final_prices)
    return {
        "mean_return": round(sum(returns) / n * 100, 2),
        "median_final": round(final_prices[n // 2], 2),
        "percentile_5": round(final_prices[int(n * 0.05)], 2),
        "percentile_95": round(final_prices[int(n * 0.95)], 2),
        "prob_profit": round(sum(1 for r in returns if r > 0) / n * 100, 1),
        "avg_max_drawdown": round(sum(drawdowns) / n * 100, 2),
        "worst_drawdown": round(max(drawdowns) * 100, 2),
    }


def var_from_simulation(paths, confidence=0.95):
    """value at risk from simulated paths."""
    returns = sorted([(p[-1] - p[0]) / p[0] for p in paths])
    idx = int(len(returns) * (1 - confidence))
    return round(returns[idx] * 100, 2)


if __name__ == "__main__":
    s0 = 100
    mu = 0.08
    sigma = 0.20
    paths = simulate_paths(s0, mu, sigma, days=252, n_paths=500)
    stats = path_statistics(paths)
    print("monte carlo simulation (500 paths, 1 year):")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    var = var_from_simulation(paths)
    print(f"  var_95: {var}%")
