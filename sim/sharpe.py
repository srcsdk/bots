#!/usr/bin/env python3
"""risk-adjusted performance metrics for strategy evaluation"""

import statistics
import math


def sharpe_ratio(returns, risk_free_rate=0.02, periods=252):
    """calculate annualized sharpe ratio."""
    if len(returns) < 2:
        return 0
    excess = [r - risk_free_rate / periods for r in returns]
    mean_excess = statistics.mean(excess)
    std = statistics.pstdev(returns)
    if std == 0:
        return 0
    return round(mean_excess / std * math.sqrt(periods), 4)


def sortino_ratio(returns, risk_free_rate=0.02, periods=252):
    """calculate sortino ratio using downside deviation."""
    if len(returns) < 2:
        return 0
    threshold = risk_free_rate / periods
    excess = statistics.mean(returns) - threshold
    downside = [min(0, r - threshold) ** 2 for r in returns]
    downside_dev = math.sqrt(statistics.mean(downside))
    if downside_dev == 0:
        return 0
    return round(excess / downside_dev * math.sqrt(periods), 4)


def max_drawdown(equity_curve):
    """calculate maximum drawdown from equity curve."""
    if not equity_curve:
        return 0
    peak = equity_curve[0]
    max_dd = 0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


def calmar_ratio(returns, equity_curve, periods=252):
    """calculate calmar ratio (return / max drawdown)."""
    if not returns or not equity_curve:
        return 0
    annual_return = statistics.mean(returns) * periods
    dd = max_drawdown(equity_curve) / 100
    if dd == 0:
        return 0
    return round(annual_return / dd, 4)


def information_ratio(returns, benchmark_returns, periods=252):
    """calculate information ratio vs benchmark."""
    if len(returns) != len(benchmark_returns) or len(returns) < 2:
        return 0
    active = [r - b for r, b in zip(returns, benchmark_returns)]
    mean_active = statistics.mean(active)
    tracking_error = statistics.pstdev(active)
    if tracking_error == 0:
        return 0
    return round(mean_active / tracking_error * math.sqrt(periods), 4)


def risk_metrics(returns, equity_curve, risk_free_rate=0.02):
    """calculate comprehensive risk metrics."""
    return {
        "sharpe": sharpe_ratio(returns, risk_free_rate),
        "sortino": sortino_ratio(returns, risk_free_rate),
        "max_drawdown_pct": max_drawdown(equity_curve),
        "calmar": calmar_ratio(returns, equity_curve),
        "volatility": round(
            statistics.pstdev(returns) * math.sqrt(252) * 100, 2
        ) if len(returns) > 1 else 0,
        "total_return_pct": round(
            (equity_curve[-1] / equity_curve[0] - 1) * 100, 2
        ) if equity_curve and equity_curve[0] > 0 else 0,
    }


if __name__ == "__main__":
    sample_returns = [0.01, -0.005, 0.02, -0.01, 0.015, 0.008, -0.003]
    equity = [10000]
    for r in sample_returns:
        equity.append(equity[-1] * (1 + r))
    metrics = risk_metrics(sample_returns, equity)
    for key, val in metrics.items():
        print(f"  {key}: {val}")
