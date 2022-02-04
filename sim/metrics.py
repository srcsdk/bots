#!/usr/bin/env python3
"""performance metrics for backtest evaluation"""

import math


def sharpe_ratio(returns, risk_free=0.0, periods=252):
    """annualized sharpe ratio from daily returns."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free / periods for r in returns]
    mean = sum(excess) / len(excess)
    var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return round(mean / std * math.sqrt(periods), 4)


def sortino_ratio(returns, risk_free=0.0, periods=252):
    """annualized sortino ratio using downside deviation."""
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free / periods for r in returns]
    mean = sum(excess) / len(excess)
    downside = [min(0, r) ** 2 for r in excess]
    dd = math.sqrt(sum(downside) / len(downside))
    if dd == 0:
        return 0.0
    return round(mean / dd * math.sqrt(periods), 4)


def max_drawdown(equity_curve):
    """calculate maximum drawdown percentage."""
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return round(max_dd * 100, 2)


def profit_factor(trades):
    """ratio of gross profit to gross loss."""
    gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 2)


def win_rate(trades):
    """percentage of winning trades."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    return round(wins / len(trades) * 100, 1)


def expectancy(trades):
    """average expected profit per trade."""
    if not trades:
        return 0.0
    pnls = [t.get("pnl", 0) for t in trades]
    return round(sum(pnls) / len(pnls), 2)


def calmar_ratio(annual_return_pct, max_dd_pct):
    """calmar ratio: annual return / max drawdown."""
    if max_dd_pct == 0:
        return 0.0
    return round(annual_return_pct / max_dd_pct, 2)


if __name__ == "__main__":
    import random
    returns = [random.gauss(0.0005, 0.02) for _ in range(252)]
    print(f"sharpe: {sharpe_ratio(returns)}")
    print(f"sortino: {sortino_ratio(returns)}")
    equity = [10000]
    for r in returns:
        equity.append(equity[-1] * (1 + r))
    print(f"max dd: {max_drawdown(equity)}%")
