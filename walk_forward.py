#!/usr/bin/env python3
"""walk-forward optimization for strategy parameters"""


def split_windows(n_bars, train_pct=0.7, n_windows=5):
    """split data into walk-forward train/test windows.

    returns list of (train_start, train_end, test_start, test_end) tuples.
    """
    window_size = n_bars // n_windows
    train_size = int(window_size * train_pct)
    windows = []
    for i in range(n_windows):
        start = i * window_size
        train_end = start + train_size
        test_end = min(start + window_size, n_bars)
        windows.append((start, train_end, train_end, test_end))
    return windows


def optimize_params(prices, param_grid, strategy_fn, metric="total_return"):
    """find best parameters on training data.

    strategy_fn(prices, **params) -> dict with performance metrics
    param_grid: list of param dicts to test
    """
    best_score = float("-inf")
    best_params = param_grid[0] if param_grid else {}
    for params in param_grid:
        result = strategy_fn(prices, **params)
        score = result.get(metric, 0)
        if score > best_score:
            best_score = score
            best_params = params
    return best_params, best_score


def walk_forward(prices, param_grid, strategy_fn, n_windows=5):
    """run walk-forward analysis.

    for each window: optimize on train, evaluate on test.
    returns aggregate out-of-sample performance.
    """
    windows = split_windows(len(prices), n_windows=n_windows)
    results = []
    for train_start, train_end, test_start, test_end in windows:
        train_prices = prices[train_start:train_end]
        test_prices = prices[test_start:test_end]
        best_params, train_score = optimize_params(
            train_prices, param_grid, strategy_fn
        )
        test_result = strategy_fn(test_prices, **best_params)
        results.append({
            "window": (train_start, test_end),
            "best_params": best_params,
            "train_score": round(train_score, 4),
            "test_score": round(test_result.get("total_return", 0), 4),
        })
    oos_scores = [r["test_score"] for r in results]
    return {
        "windows": results,
        "avg_oos_return": round(sum(oos_scores) / len(oos_scores), 4) if oos_scores else 0,
        "consistency": round(
            sum(1 for s in oos_scores if s > 0) / len(oos_scores) * 100, 1
        ) if oos_scores else 0,
    }


if __name__ == "__main__":
    import random

    def simple_ma_strategy(prices, fast=5, slow=20):
        if len(prices) < slow:
            return {"total_return": 0}
        fast_ma = sum(prices[-fast:]) / fast
        slow_ma = sum(prices[-slow:]) / slow
        ret = (prices[-1] - prices[0]) / prices[0]
        if fast_ma > slow_ma:
            return {"total_return": ret}
        return {"total_return": -ret * 0.5}

    prices = [100]
    for _ in range(500):
        prices.append(prices[-1] * (1 + random.gauss(0.0002, 0.015)))
    grid = [{"fast": f, "slow": s} for f in [3, 5, 10] for s in [15, 20, 30]]
    result = walk_forward(prices, grid, simple_ma_strategy)
    print(f"avg oos return: {result['avg_oos_return']:.4f}")
    print(f"consistency: {result['consistency']}%")
