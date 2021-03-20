#!/usr/bin/env python3
"""scanner: screen multiple tickers across strategies"""

import sys
import time


WATCHLIST_DEFAULT = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD",
    "NFLX", "DIS", "PYPL", "SQ", "SHOP", "ROKU", "PLTR", "NIO",
    "BABA", "JD", "COIN", "SOFI", "LCID", "RIVN", "GME", "AMC",
    "BB", "NOK", "WISH", "CLOV", "SPCE", "MARA",
]


def load_watchlist(filename=None):
    """load watchlist from file or return default"""
    if filename:
        try:
            with open(filename, "r") as f:
                return [line.strip().upper() for line in f if line.strip()]
        except FileNotFoundError:
            pass
    return WATCHLIST_DEFAULT


def custom_strategy_list(strategy_names):
    """validate and filter available strategies for scanning.

    returns list of valid strategy names from the input list.
    """
    available = {"gapup", "bcross", "movo", "nobr", "mobr"}
    valid = [s for s in strategy_names if s in available]
    return valid


def scan_all(tickers, strategy_name, period="1y"):
    """run a strategy across all tickers.

    returns list of (ticker, signals) tuples sorted by signal count
    """
    strategies = {
        "gapup": ("gapup", "scan"),
        "bcross": ("bcross", "scan"),
        "movo": ("movo", "scan_movo"),
        "nobr": ("movo", "scan_nobr"),
        "mobr": ("movo", "scan_mobr"),
    }

    if strategy_name not in strategies:
        print(f"unknown strategy: {strategy_name}")
        return []

    mod_name, func_name = strategies[strategy_name]
    mod = __import__(mod_name)
    scan_fn = getattr(mod, func_name)

    results = []
    for ticker in tickers:
        try:
            signals = scan_fn(ticker, period)
            if signals:
                latest = signals[-1]
                results.append({
                    "ticker": ticker,
                    "signals": len(signals),
                    "latest_date": latest["date"],
                    "latest_price": latest["price"],
                })
        except Exception as e:
            print(f"  error scanning {ticker}: {e}", file=sys.stderr)
        time.sleep(0.5)

    results.sort(key=lambda r: r["signals"], reverse=True)
    return results


def multi_scan(tickers, strategies, period="1y"):
    """run multiple strategies across tickers.

    returns dict of {strategy: results}
    """
    all_results = {}
    for strategy in strategies:
        print(f"\nrunning {strategy}...")
        all_results[strategy] = scan_all(tickers, strategy, period)
    return all_results


def consensus_picks(multi_results, min_strategies=2):
    """find tickers flagged by multiple strategies"""
    ticker_strategies = {}
    for strategy, results in multi_results.items():
        for r in results:
            ticker = r["ticker"]
            if ticker not in ticker_strategies:
                ticker_strategies[ticker] = []
            ticker_strategies[ticker].append(strategy)

    consensus = []
    for ticker, strats in ticker_strategies.items():
        if len(strats) >= min_strategies:
            consensus.append({
                "ticker": ticker,
                "strategies": strats,
                "count": len(strats),
            })

    consensus.sort(key=lambda c: c["count"], reverse=True)
    return consensus


if __name__ == "__main__":
    strategy = sys.argv[1] if len(sys.argv) > 1 else None
    period = "1y"

    watchlist = load_watchlist()

    if strategy == "--all":
        strategies = ["gapup", "bcross", "movo", "nobr", "mobr"]
        print(f"scanning {len(watchlist)} tickers with {len(strategies)} strategies...")
        results = multi_scan(watchlist, strategies, period)

        for name, hits in results.items():
            if hits:
                print(f"\n{name}: {len(hits)} hits")
                for h in hits[:5]:
                    print(f"  {h['ticker']:<6} {h['signals']:>3} signals  "
                          f"latest: {h['latest_date']}")

        picks = consensus_picks(results)
        if picks:
            print("\nconsensus picks (multiple strategies agree):")
            for p in picks:
                print(f"  {p['ticker']:<6} {p['count']} strategies: "
                      f"{', '.join(p['strategies'])}")
    elif strategy:
        print(f"scanning {len(watchlist)} tickers with {strategy}...")
        results = scan_all(watchlist, strategy, period)
        for r in results:
            print(f"  {r['ticker']:<6} {r['signals']:>3} signals  "
                  f"latest: {r['latest_date']} @ ${r['latest_price']:.2f}")
        print(f"\n{len(results)} tickers with signals")
    else:
        print("usage: python scanner.py <strategy|--all>")
        print("  strategies: gapup, bcross, movo, nobr, mobr")
        print("  --all: run all strategies and find consensus picks")
