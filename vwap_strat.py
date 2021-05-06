#!/usr/bin/env python3
"""vwap trading strategy: generate signals based on price-vwap relationship.

buy when price crosses below vwap and shows reversal with volume confirmation.
sell when price exhausts above vwap. uses cumulative vwap and standard
deviation bands for support/resistance.
"""

import sys
from ohlc import fetch_ohlc
from indicators import vwap, volume_sma


def vwap_bands(closes, volumes, num_std=2):
    """calculate vwap with standard deviation bands"""
    vwap_line = vwap(closes, volumes)
    upper = []
    lower = []

    cum_vol = 0
    cum_pv = 0
    cum_pv2 = 0

    for i in range(len(closes)):
        cum_vol += volumes[i]
        cum_pv += closes[i] * volumes[i]
        cum_pv2 += (closes[i] ** 2) * volumes[i]

        if cum_vol > 0 and vwap_line[i] is not None:
            variance = cum_pv2 / cum_vol - (cum_pv / cum_vol) ** 2
            std = max(0, variance) ** 0.5
            upper.append(round(vwap_line[i] + num_std * std, 2))
            lower.append(round(vwap_line[i] - num_std * std, 2))
        else:
            upper.append(None)
            lower.append(None)

    return vwap_line, upper, lower


def detect_reversal(closes, idx, lookback=3):
    """check if price is showing reversal signs at index"""
    if idx < lookback:
        return False, ""

    recent = closes[idx - lookback:idx + 1]

    declining = all(recent[j] <= recent[j - 1] for j in range(1, len(recent) - 1))
    if declining and closes[idx] > closes[idx - 1]:
        return True, "bullish_reversal"

    rising = all(recent[j] >= recent[j - 1] for j in range(1, len(recent) - 1))
    if rising and closes[idx] < closes[idx - 1]:
        return True, "bearish_reversal"

    return False, ""


def scan(ticker, period="1y", vol_threshold=1.3):
    """scan for vwap-based trading signals.

    buy signals:
    - price crosses below vwap and reverses upward with volume
    - price bounces off lower vwap band

    sell signals:
    - price exhausts above upper vwap band
    - price crosses above vwap and reverses downward
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    dates = [r["date"] for r in rows]

    vwap_line, vwap_upper, vwap_lower = vwap_bands(closes, volumes)
    vol_avg = volume_sma(volumes, 20)

    signals = []

    for i in range(2, len(rows)):
        if vwap_line[i] is None or vol_avg[i] is None:
            continue

        price = closes[i]
        v = vwap_line[i]
        vol_ratio = volumes[i] / vol_avg[i] if vol_avg[i] > 0 else 0

        is_reversal, rev_type = detect_reversal(closes, i)

        if price < v and is_reversal and rev_type == "bullish_reversal" and vol_ratio > vol_threshold:
            signals.append({
                "date": dates[i],
                "type": "buy",
                "subtype": "vwap_bounce",
                "price": price,
                "vwap": v,
                "discount": round((v - price) / v * 100, 2),
                "volume_ratio": round(vol_ratio, 2),
            })

        elif vwap_lower[i] and price <= vwap_lower[i] and closes[i] > closes[i - 1]:
            signals.append({
                "date": dates[i],
                "type": "buy",
                "subtype": "lower_band_bounce",
                "price": price,
                "vwap": v,
                "band": vwap_lower[i],
                "volume_ratio": round(vol_ratio, 2),
            })

        elif price > v and is_reversal and rev_type == "bearish_reversal" and vol_ratio > vol_threshold:
            signals.append({
                "date": dates[i],
                "type": "sell",
                "subtype": "vwap_rejection",
                "price": price,
                "vwap": v,
                "premium": round((price - v) / v * 100, 2),
                "volume_ratio": round(vol_ratio, 2),
            })

        elif vwap_upper[i] and price >= vwap_upper[i] and closes[i] < closes[i - 1]:
            signals.append({
                "date": dates[i],
                "type": "sell",
                "subtype": "upper_band_exhaustion",
                "price": price,
                "vwap": v,
                "band": vwap_upper[i],
                "volume_ratio": round(vol_ratio, 2),
            })

    current_vwap = vwap_line[-1]
    current_pos = "above" if closes[-1] > current_vwap else "below"
    current_dist = round((closes[-1] - current_vwap) / current_vwap * 100, 2)

    return {
        "ticker": ticker,
        "signals": signals,
        "current": {
            "price": closes[-1],
            "vwap": current_vwap,
            "upper_band": vwap_upper[-1],
            "lower_band": vwap_lower[-1],
            "position": current_pos,
            "distance_pct": current_dist,
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python vwap_strat.py <ticker> [period]")
        print("  vwap-based trading signals with band analysis")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"vwap strategy scan: {ticker} ({period})")
    result = scan(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    cur = result["current"]
    print(f"\nprice: ${cur['price']:.2f}  vwap: ${cur['vwap']:.2f}  ({cur['position']} by {cur['distance_pct']:+.2f}%)")
    if cur["upper_band"] and cur["lower_band"]:
        print(f"  bands: [{cur['lower_band']:.2f} - {cur['upper_band']:.2f}]")

    signals = result["signals"]
    if signals:
        buys = [s for s in signals if s["type"] == "buy"]
        sells = [s for s in signals if s["type"] == "sell"]
        print(f"\nsignals: {len(buys)} buy, {len(sells)} sell")
        for s in signals[-12:]:
            label = f"{s['type'].upper()} ({s['subtype']})"
            print(f"  [{label}] {s['date']} ${s['price']:.2f}  vwap=${s['vwap']:.2f}  vol={s['volume_ratio']:.1f}x")
    else:
        print("\nno signals found")
