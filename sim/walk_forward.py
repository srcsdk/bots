#!/usr/bin/env python3
"""walk-forward validation for strategy testing"""

from sim.backtest_runner import BacktestRunner


def walk_forward(data, strategy_fn, train_size=200, test_size=50, step=50):
    """run walk-forward validation.

    splits data into rolling train/test windows.
    returns list of test period results.
    """
    results = []
    i = 0
    while i + train_size + test_size <= len(data):
        train = data[i:i + train_size]
        test = data[i + train_size:i + train_size + test_size]
        runner = BacktestRunner(test, strategy_fn)
        summary = runner.run()
        summary["train_start"] = train[0]["date"]
        summary["train_end"] = train[-1]["date"]
        summary["test_start"] = test[0]["date"]
        summary["test_end"] = test[-1]["date"]
        results.append(summary)
        i += step
    return results


def aggregate_walk_forward(results):
    """aggregate walk-forward results into summary."""
    if not results:
        return {}
    returns = [r.get("total_return_pct", 0) for r in results]
    trades = [r.get("total_trades", 0) for r in results]
    profitable = sum(1 for r in returns if r > 0)
    return {
        "windows": len(results),
        "avg_return_pct": round(sum(returns) / len(returns), 2),
        "min_return_pct": round(min(returns), 2),
        "max_return_pct": round(max(returns), 2),
        "profitable_windows": profitable,
        "win_rate_pct": round(profitable / len(results) * 100, 1),
        "total_trades": sum(trades),
    }


def stability_ratio(results, metric="total_return_pct"):
    """measure strategy stability across walk-forward windows.

    returns ratio of positive windows to total windows.
    higher is better (more consistent strategy).
    """
    if not results:
        return 0.0
    values = [r.get(metric, 0) for r in results]
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    import math
    std = math.sqrt(variance)
    if std == 0:
        return float("inf")
    return round(mean / std, 4)


if __name__ == "__main__":
    import random
    data = []
    price = 100
    for i in range(500):
        price *= (1 + random.gauss(0.0003, 0.015))
        data.append({
            "date": f"2020-{(i // 22) + 1:02d}-{(i % 22) + 1:02d}",
            "close": round(price, 2), "open": round(price * 0.999, 2),
            "high": round(price * 1.01, 2), "low": round(price * 0.99, 2),
            "volume": random.randint(100000, 500000),
        })
    from sim.backtest_runner import simple_ma_strategy
    results = walk_forward(data, simple_ma_strategy, 200, 50, 50)
    summary = aggregate_walk_forward(results)
    print("walk-forward results:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"stability ratio: {stability_ratio(results)}")
