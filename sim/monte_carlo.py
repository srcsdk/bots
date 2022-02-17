#!/usr/bin/env python3
"""monte carlo simulation for strategy confidence intervals"""

import math
import random


def resample_returns(returns, n_simulations=1000, n_periods=252):
    """bootstrap resample returns to generate simulated paths."""
    simulations = []
    for _ in range(n_simulations):
        path = [1.0]
        for _ in range(n_periods):
            r = random.choice(returns)
            path.append(path[-1] * (1 + r))
        simulations.append(path)
    return simulations


def confidence_intervals(simulations, percentiles=None):
    """calculate confidence intervals from simulated paths."""
    if percentiles is None:
        percentiles = [5, 25, 50, 75, 95]
    n_periods = len(simulations[0])
    intervals = {p: [] for p in percentiles}
    for t in range(n_periods):
        values = sorted(sim[t] for sim in simulations)
        n = len(values)
        for p in percentiles:
            idx = int(n * p / 100)
            idx = min(idx, n - 1)
            intervals[p].append(round(values[idx], 4))
    return intervals


def probability_of_profit(simulations):
    """calculate probability that strategy is profitable."""
    final_values = [sim[-1] for sim in simulations]
    profitable = sum(1 for v in final_values if v > 1.0)
    return round(profitable / len(simulations) * 100, 1)


def value_at_risk(simulations, confidence=95):
    """calculate value at risk at given confidence level."""
    final_returns = [(sim[-1] - 1) for sim in simulations]
    sorted_returns = sorted(final_returns)
    idx = int(len(sorted_returns) * (1 - confidence / 100))
    return round(sorted_returns[idx] * 100, 2)


def expected_shortfall(simulations, confidence=95):
    """calculate conditional var (expected shortfall)."""
    final_returns = [(sim[-1] - 1) for sim in simulations]
    sorted_returns = sorted(final_returns)
    cutoff = int(len(sorted_returns) * (1 - confidence / 100))
    tail = sorted_returns[:cutoff]
    if not tail:
        return 0.0
    return round(sum(tail) / len(tail) * 100, 2)


def summary_stats(simulations):
    """compute summary statistics from monte carlo results."""
    final_values = [sim[-1] for sim in simulations]
    returns = [(v - 1) * 100 for v in final_values]
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    return {
        "mean_return_pct": round(mean, 2),
        "median_return_pct": round(sorted(returns)[len(returns) // 2], 2),
        "std_dev": round(math.sqrt(var), 2),
        "best_case": round(max(returns), 2),
        "worst_case": round(min(returns), 2),
        "prob_profit": probability_of_profit(simulations),
        "var_95": value_at_risk(simulations, 95),
    }


if __name__ == "__main__":
    returns = [random.gauss(0.0004, 0.015) for _ in range(252)]
    sims = resample_returns(returns, n_simulations=500, n_periods=252)
    stats = summary_stats(sims)
    print("monte carlo results (500 sims):")
    for k, v in stats.items():
        print(f"  {k}: {v}")
