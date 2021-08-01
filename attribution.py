#!/usr/bin/env python3
"""performance attribution by strategy and timeframe"""


def strategy_pnl(trades):
    """calculate pnl per strategy from tagged trades.

    trades: list of dicts with 'strategy', 'pnl', 'date' keys.
    """
    by_strategy = {}
    for t in trades:
        strat = t.get("strategy", "unknown")
        by_strategy.setdefault(strat, []).append(t)
    result = {}
    for strat, strat_trades in by_strategy.items():
        pnls = [t["pnl"] for t in strat_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        result[strat] = {
            "total_pnl": round(sum(pnls), 2),
            "trades": len(pnls),
            "win_rate": round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        }
    return result


def monthly_returns(trades):
    """group returns by month."""
    monthly = {}
    for t in trades:
        month = t.get("date", "")[:7]
        monthly.setdefault(month, 0)
        monthly[month] += t.get("pnl", 0)
    return {k: round(v, 2) for k, v in sorted(monthly.items())}


def contribution_pct(strategy_results, total_pnl):
    """calculate each strategy's contribution to total pnl."""
    if total_pnl == 0:
        return {}
    return {
        strat: round(data["total_pnl"] / total_pnl * 100, 1)
        for strat, data in strategy_results.items()
    }


def best_worst_periods(trades, period_length=20):
    """find best and worst trading periods by rolling pnl."""
    if len(trades) < period_length:
        return {}
    sorted_trades = sorted(trades, key=lambda t: t.get("date", ""))
    best_pnl = float("-inf")
    worst_pnl = float("inf")
    for i in range(len(sorted_trades) - period_length + 1):
        window = sorted_trades[i:i + period_length]
        pnl = sum(t["pnl"] for t in window)
        if pnl > best_pnl:
            best_pnl = pnl

        if pnl < worst_pnl:
            worst_pnl = pnl

    return {
        "best_period_pnl": round(best_pnl, 2),
        "worst_period_pnl": round(worst_pnl, 2),
    }


if __name__ == "__main__":
    import random
    strategies = ["momentum", "mean_rev", "breakout"]
    trades = []
    for i in range(100):
        trades.append({
            "strategy": random.choice(strategies),
            "pnl": random.gauss(50, 200),
            "date": f"2021-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        })
    results = strategy_pnl(trades)
    total = sum(r["total_pnl"] for r in results.values())
    print(f"total pnl: ${total:.2f}")
    for strat, data in results.items():
        print(f"  {strat}: ${data['total_pnl']:.2f} ({data['win_rate']}% wr)")
    contrib = contribution_pct(results, total)
    print(f"contribution: {contrib}")
