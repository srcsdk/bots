#!/usr/bin/env python3
"""strategy comparison and ranking across tickers"""

import sys
import time
from backtest import run_backtest
from performance import generate_report


STRATEGIES = {
    "gapup": ("gapup", "scan"),
    "bcross": ("bcross", "scan"),
    "movo": ("movo", "scan_movo"),
    "nobr": ("movo", "scan_nobr"),
    "mobr": ("movo", "scan_mobr"),
    "meanrev": ("meanrev", "scan"),
}


def load_scan_fn(strategy_name):
    """dynamically load a strategy scan function"""
    if strategy_name not in STRATEGIES:
        return None
    mod_name, func_name = STRATEGIES[strategy_name]
    try:
        mod = __import__(mod_name)
        return getattr(mod, func_name)
    except (ImportError, AttributeError):
        return None


def compare_on_ticker(ticker, strategy_names=None, period="2y"):
    """compare multiple strategies on a single ticker.

    returns sorted list of strategy results
    """
    if strategy_names is None:
        strategy_names = list(STRATEGIES.keys())

    results = []
    for name in strategy_names:
        scan_fn = load_scan_fn(name)
        if scan_fn is None:
            continue
        trades, curve, stats = run_backtest(ticker, scan_fn, period)
        if not trades:
            continue
        report = generate_report(trades, strategy_name=name)
        results.append({
            "strategy": name,
            "ticker": ticker,
            "return_pct": report["total_return_pct"],
            "win_rate": report["win_rate"],
            "trades": report["total_trades"],
            "sharpe": report["sharpe_ratio"],
            "max_dd": report["max_drawdown_pct"],
            "sortino": report["sortino_ratio"],
        })

    results.sort(key=lambda r: r["return_pct"], reverse=True)
    return results


def compare_across_tickers(tickers, strategy_name, period="2y"):
    """compare a single strategy across multiple tickers"""
    scan_fn = load_scan_fn(strategy_name)
    if scan_fn is None:
        return []

    results = []
    for ticker in tickers:
        trades, curve, stats = run_backtest(ticker, scan_fn, period)
        if not trades:
            continue
        report = generate_report(trades, strategy_name=strategy_name)
        results.append({
            "ticker": ticker,
            "strategy": strategy_name,
            "return_pct": report["total_return_pct"],
            "win_rate": report["win_rate"],
            "trades": report["total_trades"],
            "sharpe": report["sharpe_ratio"],
            "max_dd": report["max_drawdown_pct"],
        })
        time.sleep(0.5)

    results.sort(key=lambda r: r["return_pct"], reverse=True)
    return results


def rank_strategies(tickers, period="2y"):
    """rank all strategies by average performance across tickers.

    returns aggregated strategy rankings
    """
    strategy_totals = {}
    for strategy_name in STRATEGIES:
        scan_fn = load_scan_fn(strategy_name)
        if scan_fn is None:
            continue
        returns = []
        win_rates = []
        for ticker in tickers:
            trades, _, _ = run_backtest(ticker, scan_fn, period)
            if trades:
                report = generate_report(trades)
                returns.append(report["total_return_pct"])
                win_rates.append(report["win_rate"])
            time.sleep(0.3)

        if returns:
            strategy_totals[strategy_name] = {
                "avg_return": round(sum(returns) / len(returns), 2),
                "avg_win_rate": round(sum(win_rates) / len(win_rates), 1),
                "tickers_tested": len(returns),
                "profitable": sum(1 for r in returns if r > 0),
            }

    ranked = sorted(strategy_totals.items(),
                    key=lambda x: x[1]["avg_return"], reverse=True)
    return ranked


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage:")
        print("  compare.py ticker <ticker>     - compare strategies on one ticker")
        print("  compare.py strategy <name>     - compare strategy across tickers")
        print("  compare.py rank                - rank all strategies")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "ticker":
        ticker = sys.argv[2].upper()
        print(f"comparing strategies on {ticker}...")
        results = compare_on_ticker(ticker)
        print(f"\n{'strategy':<10} {'return':>8} {'win%':>6} {'trades':>7} "
              f"{'sharpe':>7} {'max_dd':>7}")
        for r in results:
            sharpe = f"{r['sharpe']:.3f}" if r["sharpe"] else "n/a"
            print(f"{r['strategy']:<10} {r['return_pct']:>7.2f}% {r['win_rate']:>5.1f}% "
                  f"{r['trades']:>7} {sharpe:>7} {r['max_dd']:>6.2f}%")

    elif cmd == "strategy":
        strategy = sys.argv[2]
        from scanner import WATCHLIST_DEFAULT
        tickers = WATCHLIST_DEFAULT[:10]
        print(f"testing {strategy} across {len(tickers)} tickers...")
        results = compare_across_tickers(tickers, strategy)
        for r in results:
            print(f"  {r['ticker']:<6} {r['return_pct']:>7.2f}%  "
                  f"wr={r['win_rate']}%  trades={r['trades']}")

    elif cmd == "rank":
        from scanner import WATCHLIST_DEFAULT
        tickers = WATCHLIST_DEFAULT[:8]
        print(f"ranking strategies across {len(tickers)} tickers...")
        ranked = rank_strategies(tickers)
        print(f"\n{'rank':<5} {'strategy':<10} {'avg_ret':>8} {'avg_wr':>7} "
              f"{'tested':>7} {'profitable':>10}")
        for i, (name, stats) in enumerate(ranked, 1):
            print(f"{i:<5} {name:<10} {stats['avg_return']:>7.2f}% "
                  f"{stats['avg_win_rate']:>6.1f}% {stats['tickers_tested']:>7} "
                  f"{stats['profitable']:>10}")
