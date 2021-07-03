#!/usr/bin/env python3
"""wheel strategy evaluator: score tickers for cash-secured put / covered call cycling.

the wheel strategy:
1. sell cash-secured puts at support levels
2. if assigned, sell covered calls above cost basis
3. repeat, collecting premium at each step

evaluates suitability based on price stability, premium potential,
support levels, and mean-reversion tendency.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma, atr, rsi, bollinger_bands, fifty_two_week_high


def price_stability(closes, window=60):
    """measure price stability as inverse of normalized volatility.

    lower volatility = more stable = better for wheel.
    returns 0-100 score.
    """
    if len(closes) < window:
        return 50

    rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(len(closes) - window, len(closes))]
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    annual_vol = (variance ** 0.5) * (252 ** 0.5)

    if annual_vol < 0.15:
        return 90
    elif annual_vol < 0.25:
        return 70
    elif annual_vol < 0.35:
        return 50
    elif annual_vol < 0.50:
        return 30
    return 10


def premium_potential(closes, atr_val, price):
    """estimate relative premium potential from volatility.

    higher atr relative to price = more premium available.
    score 0-100.
    """
    if not atr_val or price <= 0:
        return 50
    atr_pct = atr_val / price * 100

    if atr_pct > 3.0:
        return 90
    elif atr_pct > 2.0:
        return 75
    elif atr_pct > 1.5:
        return 60
    elif atr_pct > 1.0:
        return 45
    return 30


def mean_reversion_score(closes, period=20):
    """score mean-reversion tendency (good for wheel).

    looks at how often price returns to its moving average.
    """
    ma = sma(closes, period)
    if len(closes) < period * 2:
        return 50

    crosses = 0
    above = closes[period] > ma[period] if ma[period] else True
    for i in range(period + 1, len(closes)):
        if ma[i] is None:
            continue
        now_above = closes[i] > ma[i]
        if now_above != above:
            crosses += 1
            above = now_above

    days = len(closes) - period
    cross_rate = crosses / days if days > 0 else 0

    if cross_rate > 0.08:
        return 90
    elif cross_rate > 0.05:
        return 70
    elif cross_rate > 0.03:
        return 50
    elif cross_rate > 0.01:
        return 30
    return 15


def find_put_strike(price, closes, atr_val):
    """suggest cash-secured put strike based on support and atr"""
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)

    candidates = []
    if sma_50[-1] and sma_50[-1] < price:
        candidates.append(sma_50[-1])
    if sma_200[-1] and sma_200[-1] < price:
        candidates.append(sma_200[-1])

    if atr_val:
        candidates.append(price - 1.5 * atr_val)
        candidates.append(price - 2.0 * atr_val)

    _, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    if bb_lower[-1]:
        candidates.append(bb_lower[-1])

    candidates = [c for c in candidates if c < price and c > price * 0.85]
    if not candidates:
        return round(price * 0.95, 2)

    best = max(candidates)
    increment = 5.0 if price > 200 else 2.5 if price > 50 else 1.0
    return round(round(best / increment) * increment, 2)


def find_call_strike(price, closes, atr_val):
    """suggest covered call strike above cost basis"""
    candidates = []

    if atr_val:
        candidates.append(price + 1.5 * atr_val)
        candidates.append(price + 2.0 * atr_val)

    _, bb_upper, _ = bollinger_bands(closes, 20, 2)
    if bb_upper[-1]:
        candidates.append(bb_upper[-1])

    high_52 = fifty_two_week_high(closes)
    if high_52[-1]:
        candidates.append(high_52[-1])

    candidates = [c for c in candidates if c > price]
    if not candidates:
        return round(price * 1.05, 2)

    best = min(candidates)
    increment = 5.0 if price > 200 else 2.5 if price > 50 else 1.0
    return round(round(best / increment) * increment, 2)


def evaluate(ticker, period="1y"):
    """evaluate a ticker for wheel strategy suitability"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return None

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]

    price = closes[-1]
    atr_vals = atr(highs, lows, closes, 14)
    current_atr = atr_vals[-1]
    rsi_vals = rsi(closes, 14)
    current_rsi = rsi_vals[-1]

    stability = price_stability(closes)
    premium = premium_potential(closes, current_atr, price)
    mean_rev = mean_reversion_score(closes)

    high_52 = max(closes[-min(252, len(closes)):])
    low_52 = min(closes[-min(252, len(closes)):])
    range_pct = (high_52 - low_52) / low_52 * 100
    range_score = 70 if range_pct < 40 else 50 if range_pct < 60 else 30

    uptrend = closes[-1] > closes[-60] if len(closes) >= 60 else True
    trend_score = 80 if uptrend else 40

    composite = int(
        stability * 0.25 +
        premium * 0.20 +
        mean_rev * 0.20 +
        range_score * 0.15 +
        trend_score * 0.20
    )

    put_strike = find_put_strike(price, closes, current_atr)
    call_strike = find_call_strike(price, closes, current_atr)

    cash_needed = put_strike * 100

    return {
        "ticker": ticker,
        "price": price,
        "scores": {
            "composite": composite,
            "stability": stability,
            "premium_potential": premium,
            "mean_reversion": mean_rev,
            "range": range_score,
            "trend": trend_score,
        },
        "metrics": {
            "atr_14": round(current_atr, 2) if current_atr else None,
            "rsi_14": round(current_rsi, 1) if current_rsi else None,
            "52w_high": round(high_52, 2),
            "52w_low": round(low_52, 2),
            "52w_range_pct": round(range_pct, 1),
        },
        "suggested_strikes": {
            "put_strike": put_strike,
            "call_strike": call_strike,
            "cash_for_put": round(cash_needed, 2),
        },
        "signal": "excellent" if composite >= 75 else
                  "good" if composite >= 60 else
                  "fair" if composite >= 45 else "poor",
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python wheel.py <ticker> [period]")
        print("  evaluate wheel strategy suitability (csp -> cc cycle)")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"wheel strategy evaluation: {ticker} ({period})")
    result = evaluate(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    sc = result["scores"]
    print(f"\nprice: ${result['price']:.2f}")
    print(f"wheel suitability: {sc['composite']}/100 -> {result['signal'].upper()}")

    print("\nscores:")
    print(f"  price stability:    {sc['stability']}/100")
    print(f"  premium potential:  {sc['premium_potential']}/100")
    print(f"  mean reversion:     {sc['mean_reversion']}/100")
    print(f"  range behavior:     {sc['range']}/100")
    print(f"  trend:              {sc['trend']}/100")

    m = result["metrics"]
    print("\nmetrics:")
    print(f"  atr(14): ${m['atr_14']}")
    print(f"  rsi(14): {m['rsi_14']}")
    print(f"  52w range: ${m['52w_low']:.2f} - ${m['52w_high']:.2f} ({m['52w_range_pct']:.1f}%)")

    s = result["suggested_strikes"]
    print("\nsuggested strikes:")
    print(f"  sell put at:   ${s['put_strike']:.2f}  (cash needed: ${s['cash_for_put']:,.2f})")
    print(f"  sell call at:  ${s['call_strike']:.2f}  (if assigned on put)")
