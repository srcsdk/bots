#!/usr/bin/env python3
"""performance reporting with equity curve and strategy metrics"""

import json
import sys
from indicators import sharpe_ratio, max_drawdown


def equity_curve(trades, initial=10000):
    """build equity curve from trade results.

    trades: list of dicts with 'pnl_pct' and 'entry_date' keys
    """
    equity = initial
    curve = [{"date": "start", "equity": equity}]
    for trade in trades:
        pnl_dollar = equity * trade["pnl_pct"] / 100
        equity += pnl_dollar
        curve.append({
            "date": trade.get("exit_date", trade.get("entry_date", "")),
            "equity": round(equity, 2),
            "pnl": round(pnl_dollar, 2),
        })
    return curve


def rolling_sharpe(returns, window=63):
    """calculate rolling sharpe ratio over a window"""
    result = [None] * (window - 1)
    for i in range(window - 1, len(returns)):
        window_returns = returns[i - window + 1:i + 1]
        sr = sharpe_ratio(window_returns)
        result.append(sr)
    return result


def calmar_ratio(returns, equity_values):
    """calmar ratio: annualized return / max drawdown"""
    if not returns or not equity_values:
        return None
    ann_return = sum(returns) / len(returns) * 252 * 100
    mdd = max_drawdown(equity_values)
    if mdd == 0:
        return None
    return round(ann_return / mdd, 4)


def sortino_ratio(returns, risk_free_rate=0.02, periods=252):
    """sortino ratio: uses downside deviation instead of total std"""
    if not returns or len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    daily_rf = risk_free_rate / periods
    downside = [min(r - daily_rf, 0) ** 2 for r in returns]
    downside_dev = (sum(downside) / len(downside)) ** 0.5
    if downside_dev == 0:
        return None
    excess = mean - daily_rf
    return round(excess / downside_dev * (periods ** 0.5), 4)


def monthly_returns(curve):
    """aggregate equity curve into monthly returns"""
    months = {}
    for point in curve:
        if point["date"] == "start":
            continue
        month = point["date"][:7]
        if month not in months:
            months[month] = {"start": point["equity"] - point.get("pnl", 0),
                             "end": point["equity"]}
        else:
            months[month]["end"] = point["equity"]

    monthly = []
    for month, vals in months.items():
        if vals["start"] > 0:
            ret = (vals["end"] - vals["start"]) / vals["start"] * 100
            monthly.append({"month": month, "return_pct": round(ret, 2)})
    return monthly


def generate_report(trades, initial=10000, strategy_name=""):
    """generate comprehensive performance report"""
    if not trades:
        return {"error": "no trades"}

    curve = equity_curve(trades, initial)
    equity_vals = [c["equity"] for c in curve]
    returns = []
    for i in range(1, len(equity_vals)):
        if equity_vals[i - 1] > 0:
            returns.append((equity_vals[i] - equity_vals[i - 1]) / equity_vals[i - 1])

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    consecutive_wins = 0
    consecutive_losses = 0
    max_consec_w = 0
    max_consec_l = 0
    for t in trades:
        if t["pnl_pct"] > 0:
            consecutive_wins += 1
            consecutive_losses = 0
            max_consec_w = max(max_consec_w, consecutive_wins)
        else:
            consecutive_losses += 1
            consecutive_wins = 0
            max_consec_l = max(max_consec_l, consecutive_losses)

    total_return = (equity_vals[-1] - initial) / initial * 100

    report = {
        "strategy": strategy_name,
        "initial_capital": initial,
        "final_equity": equity_vals[-1],
        "total_return_pct": round(total_return, 2),
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "avg_win_pct": round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss_pct": round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0,
        "largest_win": max(t["pnl_pct"] for t in trades),
        "largest_loss": min(t["pnl_pct"] for t in trades),
        "max_consecutive_wins": max_consec_w,
        "max_consecutive_losses": max_consec_l,
        "sharpe_ratio": sharpe_ratio(returns),
        "sortino_ratio": sortino_ratio(returns),
        "calmar_ratio": calmar_ratio(returns, equity_vals),
        "max_drawdown_pct": max_drawdown(equity_vals),
    }

    return report


def format_report(report):
    """format report as readable text"""
    lines = []
    lines.append(f"performance report: {report.get('strategy', '')}")
    lines.append("")
    lines.append(f"  capital:        ${report['initial_capital']:,.2f} -> "
                 f"${report['final_equity']:,.2f}")
    lines.append(f"  total return:   {report['total_return_pct']:+.2f}%")
    lines.append(f"  trades:         {report['total_trades']} "
                 f"(W:{report['winning_trades']} L:{report['losing_trades']})")
    lines.append(f"  win rate:       {report['win_rate']}%")
    lines.append(f"  avg win/loss:   {report['avg_win_pct']:+.2f}% / "
                 f"{report['avg_loss_pct']:+.2f}%")
    lines.append(f"  best/worst:     {report['largest_win']:+.2f}% / "
                 f"{report['largest_loss']:+.2f}%")
    lines.append(f"  max consec W/L: {report['max_consecutive_wins']} / "
                 f"{report['max_consecutive_losses']}")
    lines.append(f"  sharpe:         {report['sharpe_ratio']}")
    lines.append(f"  sortino:        {report['sortino_ratio']}")
    lines.append(f"  calmar:         {report['calmar_ratio']}")
    lines.append(f"  max drawdown:   {report['max_drawdown_pct']}%")
    return "\n".join(lines)


def profit_factor(trades):
    """calculate profit factor: gross profits / gross losses.

    trades: list of dicts with 'pnl' or 'pnl_pct' key
    returns float, > 1.0 means profitable system
    """
    gross_profit = 0
    gross_loss = 0
    for t in trades:
        pnl = t.get("pnl", t.get("pnl_pct", 0))
        if pnl > 0:
            gross_profit += pnl
        elif pnl < 0:
            gross_loss += abs(pnl)
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0
    return round(gross_profit / gross_loss, 4)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python performance.py <journal_file>")
        print("  reads a trade journal json and generates performance report")
        sys.exit(1)

    journal_file = sys.argv[1]
    try:
        with open(journal_file, "r") as f:
            trades = json.load(f)
    except FileNotFoundError:
        print(f"file not found: {journal_file}")
        sys.exit(1)

    report = generate_report(trades, strategy_name=journal_file)
    print(format_report(report))
