#!/usr/bin/env python3
"""calculate advanced risk metrics for strategy evaluation"""

import math


def sortino_ratio(returns, risk_free_rate=0.02, periods=252):
    """calculate sortino ratio using downside deviation.

    only penalizes negative returns, unlike sharpe which penalizes all volatility.
    """
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / periods
    excess = [r - daily_rf for r in returns]
    mean_excess = sum(excess) / len(excess)
    downside = [min(r, 0) ** 2 for r in excess]
    downside_dev = math.sqrt(sum(downside) / len(downside))
    if downside_dev == 0:
        return 0.0
    return round(mean_excess / downside_dev * math.sqrt(periods), 4)


def calmar_ratio(returns, max_drawdown_pct):
    """calculate calmar ratio: annualized return / max drawdown.

    higher is better. measures return per unit of drawdown risk.
    """
    if max_drawdown_pct <= 0 or len(returns) < 2:
        return 0.0
    total_return = 1.0
    for r in returns:
        total_return *= (1 + r)
    years = len(returns) / 252
    if years <= 0:
        return 0.0
    annual_return = (total_return ** (1 / years) - 1) * 100
    return round(annual_return / max_drawdown_pct, 4)


def information_ratio(returns, benchmark_returns):
    """calculate information ratio: excess return / tracking error."""
    if len(returns) != len(benchmark_returns) or len(returns) < 2:
        return 0.0
    excess = [r - b for r, b in zip(returns, benchmark_returns)]
    mean_excess = sum(excess) / len(excess)
    variance = sum((e - mean_excess) ** 2 for e in excess) / len(excess)
    tracking_error = math.sqrt(variance)
    if tracking_error == 0:
        return 0.0
    return round(mean_excess / tracking_error * math.sqrt(252), 4)


def max_consecutive_losses(trades):
    """find longest streak of consecutive losing trades."""
    max_streak = 0
    current = 0
    for t in trades:
        pnl = t.get("pnl", 0)
        if pnl < 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def profit_factor(trades):
    """ratio of gross profits to gross losses."""
    gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def expectancy(trades):
    """average expected profit per trade."""
    if not trades:
        return 0.0
    pnls = [t.get("pnl", 0) for t in trades]
    return round(sum(pnls) / len(pnls), 2)


if __name__ == "__main__":
    import random
    random.seed(42)
    returns = [random.gauss(0.001, 0.02) for _ in range(252)]
    print(f"sortino: {sortino_ratio(returns)}")
    print(f"calmar: {calmar_ratio(returns, 15.0)}")
    trades = [{"pnl": random.gauss(50, 200)} for _ in range(100)]
    print(f"profit factor: {profit_factor(trades)}")
    print(f"expectancy: ${expectancy(trades)}")
    print(f"max consecutive losses: {max_consecutive_losses(trades)}")
