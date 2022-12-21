#!/usr/bin/env python3
# refactored: cleaner rebalance with threshold checks
"""sector rotation detector with relative strength ranking"""


SECTORS = [
    "XLK", "XLF", "XLV", "XLE", "XLI",
    "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC",
]


def relative_strength(prices, benchmark_prices, period=63):
    """calculate relative strength of asset vs benchmark over period.

    rs = (asset return / benchmark return) over rolling window.
    """
    if len(prices) < period or len(benchmark_prices) < period:
        return []
    rs = []
    for i in range(period, len(prices)):
        asset_ret = (prices[i] - prices[i - period]) / prices[i - period]
        bench_ret = (benchmark_prices[i] - benchmark_prices[i - period]) / benchmark_prices[i - period]
        if bench_ret == 0:
            rs.append(1.0)
        else:
            rs.append(asset_ret / bench_ret if bench_ret != 0 else 1.0)
    return rs


def momentum_score(prices, periods=None):
    """composite momentum score across multiple lookback periods."""
    if periods is None:
        periods = [21, 63, 126, 252]
    if len(prices) < max(periods):
        return 0.0
    scores = []
    for p in periods:
        if len(prices) >= p:
            ret = (prices[-1] - prices[-p]) / prices[-p]
            scores.append(ret)
    return sum(scores) / len(scores) if scores else 0.0


def rank_sectors(sector_data, benchmark_prices):
    """rank sectors by relative strength.

    sector_data: dict of {ticker: [prices]}
    returns sorted list of (ticker, rs_score, momentum) tuples.
    """
    rankings = []
    for ticker, prices in sector_data.items():
        rs_values = relative_strength(prices, benchmark_prices)
        rs_current = rs_values[-1] if rs_values else 0.0
        mom = momentum_score(prices)
        composite = rs_current * 0.6 + mom * 0.4
        rankings.append({
            "ticker": ticker,
            "relative_strength": round(rs_current, 4),
            "momentum": round(mom, 4),
            "composite": round(composite, 4),
        })
    rankings.sort(key=lambda x: x["composite"], reverse=True)
    for i, r in enumerate(rankings):
        r["rank"] = i + 1
    return rankings


def rotation_signal(rankings, top_n=3):
    """generate rotation signals: overweight top_n, underweight bottom."""
    if len(rankings) < top_n * 2:
        return {"overweight": rankings, "underweight": []}
    return {
        "overweight": rankings[:top_n],
        "underweight": rankings[-top_n:],
    }


if __name__ == "__main__":
    import random
    benchmark = [100]
    for _ in range(252):
        benchmark.append(benchmark[-1] * (1 + random.gauss(0.0003, 0.01)))
    sector_data = {}
    for s in SECTORS[:5]:
        prices = [100]
        for _ in range(252):
            prices.append(prices[-1] * (1 + random.gauss(0.0003, 0.012)))
        sector_data[s] = prices
    rankings = rank_sectors(sector_data, benchmark)
    for r in rankings:
        print(f"  {r['rank']}. {r['ticker']} rs={r['relative_strength']:.4f} mom={r['momentum']:.4f}")
    sig = rotation_signal(rankings)
    print(f"overweight: {[r['ticker'] for r in sig['overweight']]}")
    print(f"underweight: {[r['ticker'] for r in sig['underweight']]}")
