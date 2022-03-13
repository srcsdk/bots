#!/usr/bin/env python3
"""sharpe ratio optimization for strategy parameter tuning"""

import math
import random


def sharpe_ratio(returns, risk_free_rate=0.02):
    """calculate annualized sharpe ratio."""
    if len(returns) < 2:
        return 0
    daily_rf = risk_free_rate / 252
    excess = [r - daily_rf for r in returns]
    mean = sum(excess) / len(excess)
    var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(var) if var > 0 else 0
    if std == 0:
        return 0
    return round(mean / std * math.sqrt(252), 4)


def optimize_params(strategy_fn, data, param_ranges, n_trials=100):
    """random search for parameters maximizing sharpe ratio."""
    best_sharpe = float("-inf")
    best_params = {}
    for _ in range(n_trials):
        params = {}
        for name, (low, high) in param_ranges.items():
            if isinstance(low, int) and isinstance(high, int):
                params[name] = random.randint(low, high)
            else:
                params[name] = round(random.uniform(low, high), 4)
        returns = strategy_fn(data, **params)
        sr = sharpe_ratio(returns)
        if sr > best_sharpe:
            best_sharpe = sr
            best_params = dict(params)
    return {"sharpe": best_sharpe, "params": best_params}


def walk_forward_optimize(strategy_fn, data, param_ranges,
                          train_pct=0.7, n_trials=50):
    """optimize on training data, validate on test data."""
    split = int(len(data) * train_pct)
    train_data = data[:split]
    test_data = data[split:]
    train_result = optimize_params(
        strategy_fn, train_data, param_ranges, n_trials
    )
    test_returns = strategy_fn(test_data, **train_result["params"])
    test_sharpe = sharpe_ratio(test_returns)
    return {
        "train_sharpe": train_result["sharpe"],
        "test_sharpe": test_sharpe,
        "params": train_result["params"],
        "overfit_ratio": round(
            test_sharpe / train_result["sharpe"], 4
        ) if train_result["sharpe"] != 0 else 0,
    }


def _sample_strategy(data, fast_period=10, slow_period=30):
    """sample ma crossover strategy returning daily returns."""
    returns = []
    position = 0
    for i in range(slow_period, len(data)):
        fast_ma = sum(data[i - fast_period:i]) / fast_period
        slow_ma = sum(data[i - slow_period:i]) / slow_period
        if fast_ma > slow_ma:
            new_pos = 1
        else:
            new_pos = 0
        daily_ret = (data[i] - data[i - 1]) / data[i - 1] if data[i - 1] > 0 else 0
        returns.append(daily_ret * position)
        position = new_pos
    return returns


if __name__ == "__main__":
    random.seed(42)
    prices = [100]
    for _ in range(500):
        prices.append(prices[-1] * (1 + random.gauss(0.0003, 0.015)))
    result = optimize_params(
        _sample_strategy, prices,
        {"fast_period": (5, 30), "slow_period": (20, 100)},
        n_trials=200,
    )
    print(f"best sharpe: {result['sharpe']}")
    print(f"best params: {result['params']}")
    wf = walk_forward_optimize(
        _sample_strategy, prices,
        {"fast_period": (5, 30), "slow_period": (20, 100)},
    )
    print(f"walk-forward: train={wf['train_sharpe']}, "
          f"test={wf['test_sharpe']}, overfit={wf['overfit_ratio']}")
