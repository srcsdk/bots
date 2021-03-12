#!/usr/bin/env python3
"""market regime detection: classify market conditions using volatility, trend, and distribution.

uses rolling volatility, trend strength (adx-like directional movement), and
return distribution characteristics to classify the market into regimes:
bull, bear, sideways/choppy, high volatility.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma, rsi


def rolling_volatility(closes, window=20):
    """annualized rolling volatility from close prices"""
    result = [None] * window
    for i in range(window, len(closes)):
        rets = [(closes[j] - closes[j - 1]) / closes[j - 1] for j in range(i - window + 1, i + 1)]
        mean = sum(rets) / len(rets)
        variance = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        annual = (variance ** 0.5) * (252 ** 0.5)
        result.append(round(annual, 4))
    return result


def trend_strength(highs, lows, closes, period=14):
    """calculate trend strength similar to adx.

    uses directional movement to measure trend vs chop.
    returns values 0-100 where > 25 indicates trending.
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    plus_dm = []
    minus_dm = []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

    tr = []
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        ))

    result = [None] * period
    smooth_plus = sum(plus_dm[:period])
    smooth_minus = sum(minus_dm[:period])
    smooth_tr = sum(tr[:period])

    for i in range(period, len(tr)):
        smooth_plus = smooth_plus - smooth_plus / period + plus_dm[i]
        smooth_minus = smooth_minus - smooth_minus / period + minus_dm[i]
        smooth_tr = smooth_tr - smooth_tr / period + tr[i]

        if smooth_tr == 0:
            result.append(0)
            continue

        di_plus = 100 * smooth_plus / smooth_tr
        di_minus = 100 * smooth_minus / smooth_tr
        di_sum = di_plus + di_minus

        if di_sum == 0:
            result.append(0)
        else:
            dx = abs(di_plus - di_minus) / di_sum * 100
            result.append(round(dx, 2))

    adx_values = [None] * (period * 2 - 1)
    valid_dx = [v for v in result if v is not None]
    if len(valid_dx) >= period:
        adx = sum(valid_dx[:period]) / period
        adx_values.append(round(adx, 2))
        for i in range(period, len(valid_dx)):
            adx = (adx * (period - 1) + valid_dx[i]) / period
            adx_values.append(round(adx, 2))

    while len(adx_values) < len(closes):
        adx_values.append(None)

    return adx_values[:len(closes)]


def return_skewness(closes, window=60):
    """rolling return distribution skewness"""
    result = [None] * window
    for i in range(window, len(closes)):
        rets = [(closes[j] - closes[j - 1]) / closes[j - 1] for j in range(i - window + 1, i + 1)]
        mean = sum(rets) / len(rets)
        variance = sum((r - mean) ** 2 for r in rets) / len(rets)
        std = variance ** 0.5
        if std == 0:
            result.append(0)
        else:
            skew = sum((r - mean) ** 3 for r in rets) / (len(rets) * std ** 3)
            result.append(round(skew, 4))
    return result


def classify_regime(vol, vol_median, trend, slope, skew):
    """classify market regime from indicators"""
    high_vol = vol > vol_median * 1.3 if vol and vol_median else False
    strong_trend = trend > 25 if trend else False

    if strong_trend and slope > 0 and not high_vol:
        return "bull"
    elif strong_trend and slope < 0:
        return "bear"
    elif high_vol and not strong_trend:
        return "volatile_chop"
    elif high_vol and strong_trend and slope < 0:
        return "crash"
    elif not strong_trend and not high_vol:
        return "sideways"
    elif not strong_trend and high_vol:
        return "volatile_chop"
    else:
        return "transitional"


def analyze(ticker, period="1y"):
    """detect market regimes over the analysis period"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return None

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]
    dates = [r["date"] for r in rows]

    vol = rolling_volatility(closes, 20)
    trend = trend_strength(highs, lows, closes, 14)
    skew = return_skewness(closes, 60)
    sma_50 = sma(closes, 50)
    rsi_vals = rsi(closes, 14)
    valid_vol = [v for v in vol if v is not None]
    vol_median = sorted(valid_vol)[len(valid_vol) // 2] if valid_vol else 0.2

    regimes = []
    current_regime = None
    regime_start = None

    for i in range(len(rows)):
        if vol[i] is None or trend[i] is None:
            continue

        slope = 0
        if i >= 20:
            slope = (closes[i] - closes[i - 20]) / closes[i - 20]

        regime = classify_regime(vol[i], vol_median, trend[i], slope, skew[i] if i < len(skew) else 0)

        if regime != current_regime:
            if current_regime is not None:
                regimes.append({
                    "regime": current_regime,
                    "start": dates[regime_start],
                    "end": dates[i - 1],
                    "days": i - regime_start,
                })
            current_regime = regime
            regime_start = i

    if current_regime is not None:
        regimes.append({
            "regime": current_regime,
            "start": dates[regime_start],
            "end": dates[-1],
            "days": len(rows) - regime_start,
        })

    regime_counts = {}
    for r in regimes:
        regime_counts[r["regime"]] = regime_counts.get(r["regime"], 0) + r["days"]

    total_days = sum(regime_counts.values())

    last_slope = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
    above_sma50 = sma_50[-1] is not None and closes[-1] > sma_50[-1]
    current_rsi = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    current = {
        "price": closes[-1],
        "regime": current_regime,
        "volatility": vol[-1],
        "trend_strength": trend[-1],
        "slope_20d": round(last_slope * 100, 2),
        "skewness": skew[-1] if skew[-1] is not None else None,
        "rsi": round(current_rsi, 1),
        "above_sma50": above_sma50,
        "vol_percentile": round(
            sum(1 for v in valid_vol if v <= vol[-1]) / len(valid_vol) * 100, 1
        ) if vol[-1] and valid_vol else None,
    }

    return {
        "ticker": ticker,
        "regimes": regimes,
        "regime_distribution": {k: round(v / total_days * 100, 1) for k, v in regime_counts.items()},
        "current": current,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python regime.py <ticker> [period]")
        print("  detect market regimes: bull, bear, sideways, volatile")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"regime detection: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    cur = result["current"]
    print(f"\ncurrent regime: {cur['regime'].upper()}")
    print(f"  price: ${cur['price']:.2f}")
    print(f"  volatility: {cur['volatility']*100:.1f}% (percentile: {cur['vol_percentile']:.0f}%)")
    print(f"  trend strength: {cur['trend_strength']:.1f}")
    print(f"  20d slope: {cur['slope_20d']:+.1f}%")
    if cur["skewness"] is not None:
        print(f"  return skewness: {cur['skewness']:+.2f}")

    print(f"\nregime history ({len(result['regimes'])} periods):")
    for r in result["regimes"][-10:]:
        print(f"  {r['start']} -> {r['end']}  {r['regime']:<16} ({r['days']} days)")

    print("\ntime in each regime:")
    for regime, pct in sorted(result["regime_distribution"].items(), key=lambda x: -x[1]):
        bar = "#" * int(pct / 2)
        print(f"  {regime:<16} {pct:>5.1f}%  [{bar}]")
