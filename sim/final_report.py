#!/usr/bin/env python3
"""comprehensive year-end strategy evaluation report"""

import json
import os
import statistics


def annual_report(strategy_name, trades, equity_curve, config=None):
    """generate comprehensive annual strategy report."""
    if not trades:
        return {"strategy": strategy_name, "status": "no trades"}
    returns = [t.get("pnl_pct", 0) for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    monthly = _group_monthly(trades)
    report = {
        "strategy": strategy_name,
        "config": config or {},
        "period": {
            "start": trades[0].get("date", ""),
            "end": trades[-1].get("date", ""),
            "total_days": len(set(t.get("date", "")[:10] for t in trades)),
        },
        "performance": {
            "total_trades": len(trades),
            "total_return_pct": round(sum(returns), 2),
            "avg_return_pct": round(statistics.mean(returns), 4),
            "median_return_pct": round(statistics.median(returns), 4),
            "win_rate": round(len(wins) / len(returns) * 100, 1),
            "avg_win": round(statistics.mean(wins), 4) if wins else 0,
            "avg_loss": round(statistics.mean(losses), 4) if losses else 0,
            "best_trade": round(max(returns), 4),
            "worst_trade": round(min(returns), 4),
            "profit_factor": round(
                abs(sum(wins) / sum(losses)), 2
            ) if losses and sum(losses) != 0 else 0,
        },
        "risk": {
            "volatility": round(statistics.pstdev(returns), 4),
            "max_drawdown_pct": _max_drawdown(equity_curve),
            "max_consecutive_losses": _max_consecutive(returns, False),
            "max_consecutive_wins": _max_consecutive(returns, True),
        },
        "monthly": monthly,
    }
    return report


def _max_drawdown(equity_curve):
    """calculate max drawdown percentage."""
    if not equity_curve:
        return 0
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def _max_consecutive(returns, winning):
    """find max consecutive wins or losses."""
    max_streak = 0
    current = 0
    for r in returns:
        if (r > 0) == winning:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _group_monthly(trades):
    """group trade results by month."""
    monthly = {}
    for trade in trades:
        month = trade.get("date", "")[:7]
        if month not in monthly:
            monthly[month] = []
        monthly[month].append(trade.get("pnl_pct", 0))
    results = {}
    for month, returns in sorted(monthly.items()):
        results[month] = {
            "trades": len(returns),
            "return_pct": round(sum(returns), 2),
            "win_rate": round(
                sum(1 for r in returns if r > 0) / len(returns) * 100, 1
            ),
        }
    return results


def compare_annual(reports):
    """compare multiple strategy annual reports."""
    comparison = []
    for report in reports:
        perf = report.get("performance", {})
        risk = report.get("risk", {})
        comparison.append({
            "strategy": report.get("strategy"),
            "return_pct": perf.get("total_return_pct", 0),
            "win_rate": perf.get("win_rate", 0),
            "profit_factor": perf.get("profit_factor", 0),
            "max_drawdown": risk.get("max_drawdown_pct", 0),
            "trades": perf.get("total_trades", 0),
        })
    comparison.sort(key=lambda x: x["return_pct"], reverse=True)
    return comparison


def save_report(report, output_dir="reports"):
    """save report to json file."""
    os.makedirs(output_dir, exist_ok=True)
    name = report.get("strategy", "unnamed")
    filepath = os.path.join(output_dir, f"{name}_annual.json")
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    return filepath


if __name__ == "__main__":
    sample_trades = [
        {"date": "2022-01-05", "pnl_pct": 2.5},
        {"date": "2022-02-10", "pnl_pct": -1.0},
        {"date": "2022-03-15", "pnl_pct": 3.2},
    ]
    equity = [10000, 10250, 10148, 10473]
    report = annual_report("test_strategy", sample_trades, equity)
    print(f"strategy: {report['strategy']}")
    for section in ["performance", "risk"]:
        print(f"\n{section}:")
        for key, val in report[section].items():
            print(f"  {key}: {val}")
