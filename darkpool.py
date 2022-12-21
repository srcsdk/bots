#!/usr/bin/env python3
# improved: configurable block trade threshold
"""dark pool flow analysis proxy.

detects institutional block trades by finding days with unusually large
volume but small price movement (accumulation/distribution pattern).
compares to normal volume profile to identify stealth positioning.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma, atr, adl


def volume_profile(volumes, period=20):
    """calculate volume z-score relative to rolling average"""
    vol_avg = sma(volumes, period)
    result = []
    for i in range(len(volumes)):
        if vol_avg[i] is None or vol_avg[i] == 0:
            result.append(None)
            continue
        window = volumes[max(0, i - period + 1):i + 1]
        mean = sum(window) / len(window)
        if len(window) < 2:
            result.append(None)
            continue
        variance = sum((v - mean) ** 2 for v in window) / len(window)
        std = variance ** 0.5
        if std == 0:
            result.append(0)
        else:
            result.append(round((volumes[i] - mean) / std, 2))
    return result


def detect_block_trades(rows, vol_z_threshold=1.5, move_threshold=0.5):
    """detect days with high volume but small price moves.

    this pattern suggests institutional accumulation or distribution:
    large players executing block trades while minimizing price impact.
    """
    if len(rows) < 30:
        return []

    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    volumes = [r["volume"] for r in rows]

    vol_z = volume_profile(volumes, 20)
    atr_vals = atr(highs, lows, closes, 14)
    adl_vals = adl(highs, lows, closes, volumes)

    signals = []
    for i in range(1, len(rows)):
        if vol_z[i] is None or atr_vals[i] is None:
            continue

        price_move = abs(closes[i] - closes[i - 1]) / closes[i - 1] * 100
        intraday_range = (highs[i] - lows[i]) / closes[i] * 100

        if vol_z[i] >= vol_z_threshold and price_move < move_threshold:
            close_position = 0
            hl_range = highs[i] - lows[i]
            if hl_range > 0:
                close_position = (closes[i] - lows[i]) / hl_range

            if close_position > 0.6:
                flow_type = "accumulation"
            elif close_position < 0.4:
                flow_type = "distribution"
            else:
                flow_type = "neutral"

            adl_change = adl_vals[i] - adl_vals[i - 1] if i > 0 else 0

            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "volume": volumes[i],
                "vol_zscore": vol_z[i],
                "price_move_pct": round(price_move, 3),
                "intraday_range_pct": round(intraday_range, 3),
                "close_position": round(close_position, 2),
                "flow_type": flow_type,
                "adl_change": round(adl_change, 0),
            })

    return signals


def analyze(ticker, period="1y"):
    """analyze dark pool flow proxy signals.

    returns detected block trade signals with flow type classification.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    signals = detect_block_trades(rows)
    if not signals:
        return {"ticker": ticker, "signals": [], "summary": "no block trade signals"}

    accumulation = [s for s in signals if s["flow_type"] == "accumulation"]
    distribution = [s for s in signals if s["flow_type"] == "distribution"]

    recent = signals[-20:] if len(signals) > 20 else signals
    recent_acc = sum(1 for s in recent if s["flow_type"] == "accumulation")
    recent_dist = sum(1 for s in recent if s["flow_type"] == "distribution")

    if recent_acc > recent_dist * 1.5:
        bias = "institutional buying"
    elif recent_dist > recent_acc * 1.5:
        bias = "institutional selling"
    else:
        bias = "mixed flow"

    return {
        "ticker": ticker,
        "signals": signals,
        "total_signals": len(signals),
        "accumulation_days": len(accumulation),
        "distribution_days": len(distribution),
        "recent_bias": bias,
        "recent_acc": recent_acc,
        "recent_dist": recent_dist,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python darkpool.py <ticker> [period]")
        print("  detects institutional block trade patterns")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"dark pool flow analysis: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result or not result["signals"]:
        print("no block trade signals detected")
        sys.exit(0)

    print(f"\n  total signals: {result['total_signals']}")
    print(f"  accumulation: {result['accumulation_days']}  distribution: {result['distribution_days']}")
    print(f"  recent bias: {result['recent_bias']}")

    print("\nrecent signals:")
    for s in result["signals"][-15:]:
        print(f"  {s['date']}  ${s['price']:>8.2f}  vol_z={s['vol_zscore']:+.1f}  "
              f"move={s['price_move_pct']:.3f}%  {s['flow_type']}")
