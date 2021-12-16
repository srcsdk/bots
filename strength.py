#!/usr/bin/env python3
"""relative strength ranking across a watchlist"""

import sys
import time
from ohlc import fetch_ohlc
from indicators import rsi


def relative_strength(closes, benchmark_closes):
    """calculate relative strength vs benchmark.

    rs = stock_return / benchmark_return for each period
    """
    if len(closes) < 2 or len(benchmark_closes) < 2:
        return []
    n = min(len(closes), len(benchmark_closes))
    result = [1.0]
    for i in range(1, n):
        stock_ret = closes[i] / closes[0]
        bench_ret = benchmark_closes[i] / benchmark_closes[0]
        if bench_ret > 0:
            result.append(round(stock_ret / bench_ret, 4))
        else:
            result.append(result[-1])
    return result


def momentum_score(closes, periods=None):
    """calculate composite momentum score across multiple lookbacks.

    higher score = stronger upward momentum
    """
    if periods is None:
        periods = [21, 63, 126, 252]

    scores = []
    for p in periods:
        if len(closes) > p:
            ret = (closes[-1] - closes[-p - 1]) / closes[-p - 1]
            scores.append(ret)

    if not scores:
        return 0
    return round(sum(scores) / len(scores) * 100, 2)


def rank_watchlist(tickers, benchmark="SPY", period="1y"):
    """rank tickers by relative strength and momentum.

    returns sorted list of (ticker, score, details) tuples
    """
    bench_rows = fetch_ohlc(benchmark, period)
    if not bench_rows:
        return []
    bench_closes = [r["close"] for r in bench_rows]

    results = []
    for ticker in tickers:
        rows = fetch_ohlc(ticker, period)
        if not rows or len(rows) < 30:
            continue

        closes = [r["close"] for r in rows]
        rs = relative_strength(closes, bench_closes)
        mom = momentum_score(closes)
        rsi_vals = rsi(closes, 14)
        current_rsi = rsi_vals[-1] if rsi_vals[-1] is not None else 50

        rs_current = rs[-1] if rs else 1.0
        rs_trend = "up" if len(rs) > 20 and rs[-1] > rs[-20] else "down"

        composite = round(
            mom * 0.5 + (rs_current - 1) * 100 * 0.3 +
            (current_rsi - 50) * 0.2, 2)

        results.append({
            "ticker": ticker,
            "composite": composite,
            "momentum": mom,
            "rel_strength": rs_current,
            "rs_trend": rs_trend,
            "rsi": round(current_rsi, 1),
            "price": closes[-1],
            "return_1m": round((closes[-1] - closes[-22]) / closes[-22] * 100, 2)
            if len(closes) > 22 else 0,
        })

        time.sleep(0.3)

    results.sort(key=lambda r: r["composite"], reverse=True)
    return results


if __name__ == "__main__":
    from scanner import WATCHLIST_DEFAULT

    tickers = WATCHLIST_DEFAULT
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]

    print(f"ranking {len(tickers)} tickers by relative strength...")
    ranked = rank_watchlist(tickers)

    if not ranked:
        print("no data")
        sys.exit(1)

    print(f"\n{'rank':<5} {'ticker':<7} {'score':>7} {'mom':>7} {'rs':>6} "
          f"{'rsi':>5} {'1m%':>7} {'trend'}")
    for i, r in enumerate(ranked, 1):
        print(f"{i:<5} {r['ticker']:<7} {r['composite']:>7.2f} "
              f"{r['momentum']:>7.2f} {r['rel_strength']:>6.3f} "
              f"{r['rsi']:>5.1f} {r['return_1m']:>6.2f}% {r['rs_trend']}")

    top = [r for r in ranked[:10] if r["composite"] > 0 and r["rs_trend"] == "up"]
    if top:
        print("\ntop picks (positive score + uptrend):")
        for r in top:
            print(f"  {r['ticker']:<6} score={r['composite']:+.2f}  "
                  f"${r['price']:.2f}")
