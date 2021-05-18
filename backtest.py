#!/usr/bin/env python3
"""backtesting engine with trade journal and equity curve"""

import json
import sys
from ohlc import fetch_ohlc
from risk import simulate_exit, fixed_stop, fixed_target
from indicators import sharpe_ratio, max_drawdown


def run_backtest(ticker, scan_fn, period="2y", capital=10000,
                 stop_pct=0.05, target_pct=0.10, max_hold=30):
    """run a full backtest with equity tracking.

    scan_fn: function(ticker, period) -> list of signal dicts
    returns (trades, equity_curve, stats)
    """
    rows = fetch_ohlc(ticker, period)
    if not rows:
        return [], [], {}

    signals = scan_fn(ticker, period)
    if not signals:
        return [], [], {}

    date_to_idx = {r["date"]: i for i, r in enumerate(rows)}
    trades = []
    equity = capital
    equity_curve = [(rows[0]["date"], equity)]
    in_trade = False
    position_shares = 0

    for sig in signals:
        if sig["date"] not in date_to_idx or in_trade:
            continue

        entry_idx = date_to_idx[sig["date"]]
        entry = sig["price"]
        stop = fixed_stop(entry, stop_pct)
        target = fixed_target(entry, target_pct)

        position_shares = int(equity * 0.95 / entry)
        if position_shares <= 0:
            continue

        exit_idx, exit_price, reason = simulate_exit(
            rows, entry_idx, stop, target, max_hold
        )

        pnl = (exit_price - entry) * position_shares
        equity += pnl
        equity_curve.append((rows[exit_idx]["date"], round(equity, 2)))

        trades.append({
            "entry_date": sig["date"],
            "exit_date": rows[exit_idx]["date"],
            "entry": entry,
            "exit": exit_price,
            "shares": position_shares,
            "pnl": round(pnl, 2),
            "pnl_pct": round((exit_price - entry) / entry * 100, 2),
            "reason": reason,
            "equity_after": round(equity, 2),
        })

        in_trade = False

    equity_values = [e[1] for e in equity_curve]
    returns = []
    for i in range(1, len(equity_values)):
        if equity_values[i - 1] > 0:
            returns.append((equity_values[i] - equity_values[i - 1]) / equity_values[i - 1])

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    stats = {
        "ticker": ticker,
        "period": period,
        "initial_capital": capital,
        "final_equity": round(equity, 2),
        "total_return_pct": round((equity - capital) / capital * 100, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "sharpe": sharpe_ratio(returns) if len(returns) > 1 else None,
        "max_drawdown": max_drawdown(equity_values),
        "profit_factor": round(
            sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)), 2
        ) if losses and sum(t["pnl"] for t in losses) != 0 else None,
    }

    return trades, equity_curve, stats


def sharpe_overlay(results):
    """add rolling sharpe ratio to backtest results.

    results: (trades, equity_curve, stats) tuple from run_backtest
    returns the stats dict with rolling_sharpe list appended
    """
    trades, equity_curve, stats = results
    if len(equity_curve) < 3:
        stats["rolling_sharpe"] = []
        return stats

    values = [e[1] for e in equity_curve]
    returns = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            returns.append((values[i] - values[i - 1]) / values[i - 1])

    window = min(20, len(returns))
    rolling = []
    for i in range(window - 1, len(returns)):
        chunk = returns[i - window + 1:i + 1]
        mean_r = sum(chunk) / len(chunk)
        var_r = sum((r - mean_r) ** 2 for r in chunk) / len(chunk)
        std_r = var_r ** 0.5
        if std_r > 0:
            rolling.append(round(mean_r / std_r * (252 ** 0.5), 4))
        else:
            rolling.append(0)

    stats["rolling_sharpe"] = rolling
    return stats


def save_journal(trades, filename):
    """save trade journal to json"""
    with open(filename, "w") as f:
        json.dump(trades, f, indent=2)


def compare_strategies(ticker, strategies, period="2y"):
    """compare multiple strategies on the same ticker.

    strategies: dict of {name: scan_function}
    returns dict of {name: stats}
    """
    results = {}
    for name, scan_fn in strategies.items():
        _, _, stats = run_backtest(ticker, scan_fn, period)
        results[name] = stats
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python backtest.py <ticker> <strategy>")
        print("  strategies: gapup, bcross, movo, nobr, mobr")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    strategy = sys.argv[2]

    strategy_map = {
        "gapup": ("gapup", "scan"),
        "bcross": ("bcross", "scan"),
        "movo": ("movo", "scan_movo"),
        "nobr": ("movo", "scan_nobr"),
        "mobr": ("movo", "scan_mobr"),
    }

    if strategy not in strategy_map:
        print(f"unknown strategy: {strategy}")
        sys.exit(1)

    mod_name, func_name = strategy_map[strategy]
    mod = __import__(mod_name)
    scan_fn = getattr(mod, func_name)

    print(f"backtesting {strategy} on {ticker}...")
    trades, curve, stats = run_backtest(ticker, scan_fn)

    print("\nresults:")
    print(f"  return:      {stats['total_return_pct']:+.2f}%")
    print(f"  trades:      {stats['trades']} (W:{stats['wins']} L:{stats['losses']})")
    print(f"  win rate:    {stats['win_rate']}%")
    print(f"  sharpe:      {stats['sharpe']}")
    print(f"  max dd:      {stats['max_drawdown']}%")
    print(f"  profit fac:  {stats['profit_factor']}")
    print(f"  final:       ${stats['final_equity']:,.2f}")

    journal_file = f"journal_{ticker}_{strategy}.json"
    save_journal(trades, journal_file)
    print(f"\ntrade journal saved to {journal_file}")
