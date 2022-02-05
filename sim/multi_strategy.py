#!/usr/bin/env python3
"""run multiple strategies concurrently on same data"""

from sim.backtest_runner import BacktestRunner


def run_strategies(data, strategies, initial_capital=100000):
    """run multiple strategies on same data.

    strategies: dict of name -> strategy_fn.
    returns dict of name -> results.
    """
    results = {}
    for name, strategy_fn in strategies.items():
        runner = BacktestRunner(data, strategy_fn, initial_capital)
        summary = runner.run()
        summary["strategy_name"] = name
        summary["equity_curve"] = runner.equity_curve
        results[name] = summary
    return results


def rank_strategies(results, metric="total_return_pct"):
    """rank strategies by performance metric."""
    ranked = sorted(
        results.items(),
        key=lambda x: x[1].get(metric, 0),
        reverse=True
    )
    return [
        {"rank": i + 1, "name": name, metric: data.get(metric, 0)}
        for i, (name, data) in enumerate(ranked)
    ]


def ensemble_signal(strategies_signals):
    """combine signals from multiple strategies (majority vote).

    strategies_signals: dict of strategy_name -> signal (buy/sell/hold).
    """
    votes = {"buy": 0, "sell": 0, "hold": 0}
    for signal in strategies_signals.values():
        action = signal.get("action", "hold") if signal else "hold"
        votes[action] = votes.get(action, 0) + 1
    if votes["buy"] > votes["sell"] and votes["buy"] > votes["hold"]:
        return {"action": "buy", "confidence": votes["buy"] / len(strategies_signals)}
    elif votes["sell"] > votes["buy"] and votes["sell"] > votes["hold"]:
        return {"action": "sell", "confidence": votes["sell"] / len(strategies_signals)}
    return {"action": "hold", "confidence": votes["hold"] / len(strategies_signals)}


def correlation_between_strategies(results_a, results_b):
    """measure return correlation between two strategies."""
    curve_a = [e["equity"] for e in results_a.get("equity_curve", [])]
    curve_b = [e["equity"] for e in results_b.get("equity_curve", [])]
    n = min(len(curve_a), len(curve_b))
    if n < 10:
        return 0.0
    returns_a = [(curve_a[i] - curve_a[i-1]) / curve_a[i-1] for i in range(1, n)]
    returns_b = [(curve_b[i] - curve_b[i-1]) / curve_b[i-1] for i in range(1, n)]
    mean_a = sum(returns_a) / len(returns_a)
    mean_b = sum(returns_b) / len(returns_b)
    import math
    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b)) / len(returns_a)
    std_a = math.sqrt(sum((a - mean_a) ** 2 for a in returns_a) / len(returns_a))
    std_b = math.sqrt(sum((b - mean_b) ** 2 for b in returns_b) / len(returns_b))
    if std_a == 0 or std_b == 0:
        return 0.0
    return round(cov / (std_a * std_b), 4)


if __name__ == "__main__":
    from sim.backtest_runner import simple_ma_strategy
    strategies = {
        "ma_20": simple_ma_strategy,
    }
    print(f"strategies loaded: {list(strategies.keys())}")
    signal = ensemble_signal({"a": {"action": "buy"}, "b": {"action": "buy"}, "c": {"action": "sell"}})
    print(f"ensemble: {signal}")
