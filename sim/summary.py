#!/usr/bin/env python3
"""generate comprehensive performance summary from backtest"""

from sim.metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, win_rate, expectancy, calmar_ratio
)


def full_summary(equity_curve, trades, initial_capital=100000, periods=252):
    """compile all performance metrics into summary."""
    if not equity_curve:
        return {"error": "no data"}
    equity_values = [e["equity"] for e in equity_curve]
    returns = []
    for i in range(1, len(equity_values)):
        r = (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
        returns.append(r)
    final = equity_values[-1]
    total_return = (final - initial_capital) / initial_capital * 100
    days = len(equity_curve)
    annual_return = total_return * (periods / max(days, 1))
    mdd = max_drawdown(equity_values)
    return {
        "initial_capital": initial_capital,
        "final_equity": round(final, 2),
        "total_return_pct": round(total_return, 2),
        "annualized_return_pct": round(annual_return, 2),
        "sharpe_ratio": sharpe_ratio(returns, periods=periods),
        "sortino_ratio": sortino_ratio(returns, periods=periods),
        "max_drawdown_pct": mdd,
        "calmar_ratio": calmar_ratio(annual_return, mdd),
        "total_trades": len(trades),
        "win_rate_pct": win_rate(trades),
        "profit_factor": profit_factor(trades),
        "expectancy": expectancy(trades),
        "trading_days": days,
    }


def format_summary(summary):
    """format summary for console output."""
    lines = ["backtest performance summary", "=" * 35, ""]
    sections = {
        "returns": ["total_return_pct", "annualized_return_pct"],
        "risk": ["max_drawdown_pct", "sharpe_ratio", "sortino_ratio", "calmar_ratio"],
        "trading": ["total_trades", "win_rate_pct", "profit_factor", "expectancy"],
    }
    for section, keys in sections.items():
        lines.append(f"[{section}]")
        for key in keys:
            val = summary.get(key, "n/a")
            label = key.replace("_", " ")
            lines.append(f"  {label}: {val}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import random
    equity = [{"date": f"2021-{i:03d}", "equity": 100000} for i in range(1)]
    val = 100000
    for i in range(1, 252):
        val *= (1 + random.gauss(0.0004, 0.015))
        equity.append({"date": f"2021-{i:03d}", "equity": round(val, 2)})
    trades = [
        {"pnl": random.gauss(50, 200)} for _ in range(50)
    ]
    summary = full_summary(equity, trades)
    print(format_summary(summary))
