#!/usr/bin/env python3
"""detailed backtest report generation"""


def generate_report(trades, equity_curve, initial_capital):
    """generate comprehensive backtest report."""
    if not trades or not equity_curve:
        return {}
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    winning = [t for t in trades if t.get("pnl", 0) > 0]
    losing = [t for t in trades if t.get("pnl", 0) < 0]
    win_rate = len(winning) / len(trades) if trades else 0
    avg_win = (
        sum(t["pnl"] for t in winning) / len(winning) if winning else 0
    )
    avg_loss = (
        sum(t["pnl"] for t in losing) / len(losing) if losing else 0
    )
    profit_factor = 0
    total_wins = sum(t["pnl"] for t in winning)
    total_losses = abs(sum(t["pnl"] for t in losing))
    if total_losses > 0:
        profit_factor = total_wins / total_losses
    max_dd = _max_drawdown(equity_curve)
    return {
        "total_return_pct": round(total_return * 100, 2),
        "total_trades": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round(win_rate * 100, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": max_dd,
        "final_equity": round(final_equity, 2),
        "initial_capital": initial_capital,
    }


def _max_drawdown(equity_curve):
    """calculate max drawdown percentage."""
    peak = equity_curve[0]
    max_dd = 0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return round(max_dd * 100, 2)


def monthly_returns(equity_curve, dates):
    """calculate monthly returns from equity curve."""
    if len(equity_curve) != len(dates):
        return {}
    monthly = {}
    for i in range(len(dates)):
        month = dates[i][:7]
        if month not in monthly:
            monthly[month] = {"start": equity_curve[i]}
        monthly[month]["end"] = equity_curve[i]
    returns = {}
    for month, vals in monthly.items():
        if vals["start"] > 0:
            ret = (vals["end"] - vals["start"]) / vals["start"]
            returns[month] = round(ret * 100, 2)
    return returns


def trade_analysis(trades):
    """analyze trade patterns."""
    if not trades:
        return {}
    durations = []
    for t in trades:
        if "entry_date" in t and "exit_date" in t:
            durations.append(1)
    consecutive_wins = 0
    consecutive_losses = 0
    max_wins = 0
    max_losses = 0
    for t in trades:
        if t.get("pnl", 0) > 0:
            consecutive_wins += 1
            consecutive_losses = 0
            max_wins = max(max_wins, consecutive_wins)
        elif t.get("pnl", 0) < 0:
            consecutive_losses += 1
            consecutive_wins = 0
            max_losses = max(max_losses, consecutive_losses)
    return {
        "max_consecutive_wins": max_wins,
        "max_consecutive_losses": max_losses,
        "avg_pnl": round(
            sum(t.get("pnl", 0) for t in trades) / len(trades), 2
        ),
        "largest_win": round(
            max(t.get("pnl", 0) for t in trades), 2
        ),
        "largest_loss": round(
            min(t.get("pnl", 0) for t in trades), 2
        ),
    }


def format_report(report):
    """format report for display."""
    lines = ["backtest report", "=" * 40]
    for key, value in report.items():
        label = key.replace("_", " ")
        if isinstance(value, float):
            if "pct" in key or "rate" in key:
                lines.append(f"  {label}: {value}%")
            else:
                lines.append(f"  {label}: {value}")
        else:
            lines.append(f"  {label}: {value}")
    return "\n".join(lines)


if __name__ == "__main__":
    import random
    random.seed(42)
    trades = []
    for i in range(50):
        pnl = random.gauss(50, 200)
        trades.append({"pnl": round(pnl, 2), "symbol": "TEST"})
    equity = [100000]
    for t in trades:
        equity.append(equity[-1] + t["pnl"])
    report = generate_report(trades, equity, 100000)
    print(format_report(report))
    analysis = trade_analysis(trades)
    print(f"\ntrade analysis: {analysis}")
