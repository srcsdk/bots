#!/usr/bin/env python3
"""classify market regimes for strategy selection"""

import statistics


def classify_regime(returns, window=20):
    """classify current market regime from returns."""
    if len(returns) < window:
        return "unknown"
    recent = returns[-window:]
    mean_ret = statistics.mean(recent)
    volatility = statistics.pstdev(recent)
    if mean_ret > 0.005 and volatility < 0.02:
        return "bull_low_vol"
    elif mean_ret > 0.005 and volatility >= 0.02:
        return "bull_high_vol"
    elif mean_ret < -0.005 and volatility < 0.02:
        return "bear_low_vol"
    elif mean_ret < -0.005 and volatility >= 0.02:
        return "bear_high_vol"
    elif volatility < 0.01:
        return "sideways_quiet"
    else:
        return "sideways_choppy"


def regime_history(returns, window=20, step=5):
    """get regime history over time."""
    regimes = []
    for i in range(window, len(returns), step):
        regime = classify_regime(returns[:i], window)
        regimes.append({
            "index": i,
            "regime": regime,
        })
    return regimes


def regime_performance(trades, regimes):
    """analyze strategy performance per regime."""
    perf = {}
    for trade in trades:
        regime = trade.get("regime", "unknown")
        if regime not in perf:
            perf[regime] = {"returns": [], "count": 0}
        perf[regime]["returns"].append(trade.get("pnl_pct", 0))
        perf[regime]["count"] += 1
    results = {}
    for regime, data in perf.items():
        returns = data["returns"]
        results[regime] = {
            "trades": data["count"],
            "avg_return": round(statistics.mean(returns), 4) if returns else 0,
            "win_rate": round(
                sum(1 for r in returns if r > 0) / len(returns) * 100, 1
            ) if returns else 0,
            "total": round(sum(returns), 4),
        }
    return results


def best_strategy_per_regime(regime_results):
    """find best performing strategy for each regime."""
    best = {}
    for strategy_name, regime_perf in regime_results.items():
        for regime, perf in regime_perf.items():
            if regime not in best:
                best[regime] = (strategy_name, perf["avg_return"])
            elif perf["avg_return"] > best[regime][1]:
                best[regime] = (strategy_name, perf["avg_return"])
    return {
        regime: {"strategy": name, "avg_return": ret}
        for regime, (name, ret) in best.items()
    }


def transition_matrix(regimes):
    """build regime transition probability matrix."""
    transitions = {}
    for i in range(len(regimes) - 1):
        current = regimes[i]["regime"]
        next_regime = regimes[i + 1]["regime"]
        if current not in transitions:
            transitions[current] = {}
        transitions[current][next_regime] = (
            transitions[current].get(next_regime, 0) + 1
        )
    matrix = {}
    for regime, counts in transitions.items():
        total = sum(counts.values())
        matrix[regime] = {
            k: round(v / total, 3)
            for k, v in counts.items()
        }
    return matrix


if __name__ == "__main__":
    import random
    random.seed(42)
    returns = [random.gauss(0.001, 0.015) for _ in range(100)]
    regime = classify_regime(returns)
    print(f"current regime: {regime}")
    history = regime_history(returns)
    for r in history[-5:]:
        print(f"  idx {r['index']}: {r['regime']}")
