#!/usr/bin/env python3
# improved: handles market holidays and half days
"""calendar spread evaluator.

analyzes term structure by comparing short-term vs long-term volatility.
identifies periods where calendar spreads are favorable based on
volatility differential between time horizons.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma


def realized_volatility(closes, period):
    """calculate annualized realized volatility over a rolling window.

    uses log returns approximation: (close/prev - 1) for daily returns.
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    returns = [None]
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            returns.append((closes[i] / closes[i - 1]) - 1)
        else:
            returns.append(None)

    result = [None] * period
    for i in range(period, len(returns)):
        window = [r for r in returns[i - period + 1:i + 1] if r is not None]
        if len(window) < period // 2:
            result.append(None)
            continue
        mean = sum(window) / len(window)
        variance = sum((r - mean) ** 2 for r in window) / len(window)
        daily_vol = variance ** 0.5
        annual_vol = daily_vol * (252 ** 0.5)
        result.append(round(annual_vol * 100, 2))

    return result


def vol_term_structure(closes):
    """calculate volatility term structure across multiple windows.

    returns short (10d), medium (30d), and long (60d) realized vol.
    """
    short_vol = realized_volatility(closes, 10)
    med_vol = realized_volatility(closes, 30)
    long_vol = realized_volatility(closes, 60)
    return short_vol, med_vol, long_vol


def calendar_spread_score(short_vol, long_vol):
    """score calendar spread opportunity.

    favorable when short vol >> long vol (sell near, buy far)
    or when long vol >> short vol (buy near, sell far).
    """
    if short_vol is None or long_vol is None or long_vol == 0:
        return None, None

    ratio = short_vol / long_vol

    if ratio > 1.3:
        signal = "sell_calendar"
        score = min(100, int((ratio - 1) * 100))
    elif ratio < 0.7:
        signal = "buy_calendar"
        score = min(100, int((1 - ratio) * 100))
    else:
        signal = "neutral"
        score = 0

    return signal, score


def analyze(ticker, period="1y"):
    """analyze calendar spread opportunities based on vol term structure.

    returns daily term structure data and spread signals.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 80:
        return None

    closes = [r["close"] for r in rows]
    short_vol, med_vol, long_vol = vol_term_structure(closes)
    price_trend = sma(closes, 50)

    signals = []
    daily_data = []

    for i in range(60, len(rows)):
        if short_vol[i] is None or long_vol[i] is None:
            continue

        signal, score = calendar_spread_score(short_vol[i], long_vol[i])
        med = med_vol[i] if med_vol[i] is not None else 0
        trend = "up" if price_trend[i] and closes[i] > price_trend[i] else "down"

        entry = {
            "date": rows[i]["date"],
            "price": closes[i],
            "trend": trend,
            "short_vol": short_vol[i],
            "med_vol": round(med, 2),
            "long_vol": long_vol[i],
            "ratio": round(short_vol[i] / long_vol[i], 2) if long_vol[i] > 0 else None,
            "signal": signal,
            "score": score,
        }
        daily_data.append(entry)

        if signal != "neutral" and score >= 30:
            signals.append(entry)

    if not daily_data:
        return {"ticker": ticker, "signals": [], "summary": "insufficient vol data"}

    latest = daily_data[-1]
    avg_short = round(sum(d["short_vol"] for d in daily_data) / len(daily_data), 2)
    avg_long = round(sum(d["long_vol"] for d in daily_data) / len(daily_data), 2)

    contango_days = sum(1 for d in daily_data if d["ratio"] and d["ratio"] < 1)
    backwardation_days = sum(1 for d in daily_data if d["ratio"] and d["ratio"] > 1)

    return {
        "ticker": ticker,
        "latest": latest,
        "avg_short_vol": avg_short,
        "avg_long_vol": avg_long,
        "contango_pct": round(contango_days / len(daily_data) * 100, 1),
        "backwardation_pct": round(backwardation_days / len(daily_data) * 100, 1),
        "signals": signals,
        "total_signals": len(signals),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python calendar_strat.py <ticker> [period]")
        print("  evaluates calendar spread opportunities via vol term structure")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"calendar spread analysis: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    latest = result["latest"]
    print("\n  current vol structure:")
    print(f"    short (10d): {latest['short_vol']:.1f}%")
    print(f"    medium (30d): {latest['med_vol']:.1f}%")
    print(f"    long (60d): {latest['long_vol']:.1f}%")
    print(f"    ratio (s/l): {latest['ratio']:.2f}")
    print(f"    signal: {latest['signal']} (score: {latest['score']})")

    print(f"\n  avg short vol: {result['avg_short_vol']:.1f}%")
    print(f"  avg long vol: {result['avg_long_vol']:.1f}%")
    print(f"  contango: {result['contango_pct']:.1f}%  backwardation: {result['backwardation_pct']:.1f}%")

    if result["signals"]:
        print(f"\nrecent signals ({result['total_signals']} total):")
        for s in result["signals"][-10:]:
            print(f"  {s['date']}  ${s['price']:>8.2f}  {s['signal']:<15}  "
                  f"score={s['score']}  ratio={s['ratio']:.2f}")
    else:
        print("\nno strong calendar signals")
