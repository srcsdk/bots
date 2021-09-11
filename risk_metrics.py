#!/usr/bin/env python3
"""risk-adjusted return metrics"""

import math


def sharpe_ratio(returns, risk_free_rate=0.0, periods=252):
    """calculate annualized sharpe ratio.

    returns: list of period returns (decimal).
    """
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free_rate / periods for r in returns]
    avg = sum(excess) / len(excess)
    variance = sum((r - avg) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return round(avg / std * math.sqrt(periods), 4)


def sortino_ratio(returns, risk_free_rate=0.0, periods=252):
    """calculate sortino ratio using downside deviation."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free_rate / periods for r in returns]
    avg = sum(excess) / len(excess)
    downside = [min(0, r) ** 2 for r in excess]
    downside_dev = math.sqrt(sum(downside) / len(downside))
    if downside_dev == 0:
        return 0.0
    return round(avg / downside_dev * math.sqrt(periods), 4)


def information_ratio(returns, benchmark_returns):
    """calculate information ratio vs benchmark."""
    if len(returns) != len(benchmark_returns) or len(returns) < 2:
        return 0.0
    active = [r - b for r, b in zip(returns, benchmark_returns)]
    avg_active = sum(active) / len(active)
    variance = sum((a - avg_active) ** 2 for a in active) / (len(active) - 1)
    tracking_error = math.sqrt(variance)
    if tracking_error == 0:
        return 0.0
    return round(avg_active / tracking_error, 4)


def omega_ratio(returns, threshold=0.0):
    """calculate omega ratio (probability weighted gains/losses)."""
    gains = sum(max(0, r - threshold) for r in returns)
    losses = sum(max(0, threshold - r) for r in returns)
    if losses == 0:
        return float("inf")
    return round(gains / losses, 4)


if __name__ == "__main__":
    import random
    rets = [random.gauss(0.0005, 0.02) for _ in range(252)]
    print(f"sharpe: {sharpe_ratio(rets)}")
    print(f"sortino: {sortino_ratio(rets)}")
    print(f"omega: {omega_ratio(rets)}")
