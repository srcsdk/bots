#!/usr/bin/env python3
"""benchmark comparison for strategy evaluation"""

import math


def buy_and_hold(data, initial_capital=100000):
    """calculate buy and hold baseline return."""
    if not data:
        return {}
    first_price = data[0]["close"]
    shares = int(initial_capital / first_price)
    remaining_cash = initial_capital - shares * first_price
    final_value = shares * data[-1]["close"] + remaining_cash
    total_return = (final_value - initial_capital) / initial_capital
    return {
        "strategy": "buy_and_hold",
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return * 100, 2),
        "shares": shares,
    }


def compare_to_benchmark(strategy_result, benchmark_result):
    """compare strategy performance to benchmark."""
    strat_ret = strategy_result.get("total_return_pct", 0)
    bench_ret = benchmark_result.get("total_return_pct", 0)
    alpha = strat_ret - bench_ret
    return {
        "strategy_return": strat_ret,
        "benchmark_return": bench_ret,
        "alpha": round(alpha, 2),
        "outperformed": alpha > 0,
    }


def annualized_return(total_return_pct, days):
    """convert total return to annualized return."""
    if days <= 0:
        return 0.0
    years = days / 252
    total = 1 + total_return_pct / 100
    if total <= 0:
        return -100.0
    annual = total ** (1 / years) - 1
    return round(annual * 100, 2)


def risk_adjusted_comparison(strategy_returns, benchmark_returns):
    """compare risk-adjusted returns (information ratio)."""
    if len(strategy_returns) != len(benchmark_returns):
        return {}
    active = [s - b for s, b in zip(strategy_returns, benchmark_returns)]
    if not active:
        return {}
    mean_active = sum(active) / len(active)
    var = sum((a - mean_active) ** 2 for a in active) / len(active)
    tracking_error = math.sqrt(var) if var > 0 else 0
    ir = mean_active / tracking_error if tracking_error > 0 else 0
    return {
        "mean_active_return": round(mean_active, 4),
        "tracking_error": round(tracking_error, 4),
        "information_ratio": round(ir, 4),
    }


if __name__ == "__main__":
    import random
    data = []
    price = 100
    for i in range(252):
        price *= (1 + random.gauss(0.0003, 0.015))
        data.append({"date": f"2021-{i:03d}", "close": round(price, 2)})
    bh = buy_and_hold(data)
    print(f"buy & hold: {bh['total_return_pct']}%")
    fake_strat = {"total_return_pct": 15.5}
    comp = compare_to_benchmark(fake_strat, bh)
    print(f"alpha: {comp['alpha']}%")
