#!/usr/bin/env python3
"""tape reading / price action analysis.

analyzes candle patterns (engulfing, doji, hammer, shooting star),
volume at price levels, and key level reactions. scores conviction
for each signal based on volume confirmation and context.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma, atr


def body_size(row):
    """calculate candle body size as percentage of price"""
    return abs(row["close"] - row["open"]) / row["close"] * 100


def upper_wick(row):
    """calculate upper wick length"""
    return row["high"] - max(row["open"], row["close"])


def lower_wick(row):
    """calculate lower wick length"""
    return min(row["open"], row["close"]) - row["low"]


def candle_range(row):
    """total candle range (high - low)"""
    return row["high"] - row["low"]


def is_bullish(row):
    """check if candle closed higher than open"""
    return row["close"] > row["open"]


def detect_doji(row, threshold=0.1):
    """detect doji: very small body relative to range"""
    cr = candle_range(row)
    if cr == 0:
        return False
    body_ratio = abs(row["close"] - row["open"]) / cr
    return body_ratio < threshold


def detect_hammer(row, body_ratio_max=0.35, wick_ratio_min=2.0):
    """detect hammer: small body at top, long lower wick"""
    cr = candle_range(row)
    if cr == 0:
        return False
    body = abs(row["close"] - row["open"])
    lw = lower_wick(row)
    uw = upper_wick(row)
    if body == 0:
        return False
    return (body / cr < body_ratio_max and
            lw / body >= wick_ratio_min and
            uw < body)


def detect_shooting_star(row, body_ratio_max=0.35, wick_ratio_min=2.0):
    """detect shooting star: small body at bottom, long upper wick"""
    cr = candle_range(row)
    if cr == 0:
        return False
    body = abs(row["close"] - row["open"])
    uw = upper_wick(row)
    lw = lower_wick(row)
    if body == 0:
        return False
    return (body / cr < body_ratio_max and
            uw / body >= wick_ratio_min and
            lw < body)


def detect_engulfing(curr, prev):
    """detect bullish or bearish engulfing pattern"""
    if is_bullish(curr) and not is_bullish(prev):
        if (curr["open"] <= prev["close"] and
                curr["close"] >= prev["open"] and
                body_size(curr) > body_size(prev)):
            return "bullish_engulfing"
    elif not is_bullish(curr) and is_bullish(prev):
        if (curr["open"] >= prev["close"] and
                curr["close"] <= prev["open"] and
                body_size(curr) > body_size(prev)):
            return "bearish_engulfing"
    return None


def volume_at_price_levels(rows, num_levels=10):
    """build volume profile: aggregate volume at price levels"""
    if not rows:
        return []

    all_prices = [r["close"] for r in rows]
    price_min = min(all_prices)
    price_max = max(all_prices)
    price_range = price_max - price_min

    if price_range == 0:
        return []

    level_size = price_range / num_levels
    levels = []
    for i in range(num_levels):
        low = price_min + i * level_size
        high = low + level_size
        vol = 0
        count = 0
        for r in rows:
            if low <= r["close"] < high or (i == num_levels - 1 and r["close"] == high):
                vol += r["volume"]
                count += 1
        levels.append({
            "price_low": round(low, 2),
            "price_high": round(high, 2),
            "price_mid": round((low + high) / 2, 2),
            "volume": vol,
            "bar_count": count,
        })

    return levels


def find_support_resistance(rows, lookback=60):
    """find key support/resistance levels from recent price action"""
    if len(rows) < lookback:
        lookback = len(rows)

    recent = rows[-lookback:]
    highs = [r["high"] for r in recent]
    lows = [r["low"] for r in recent]

    levels = []
    tolerance = (max(highs) - min(lows)) * 0.02

    for i in range(2, len(recent) - 2):
        if highs[i] >= max(highs[i - 2:i]) and highs[i] >= max(highs[i + 1:i + 3]):
            levels.append({"price": highs[i], "type": "resistance"})
        if lows[i] <= min(lows[i - 2:i]) and lows[i] <= min(lows[i + 1:i + 3]):
            levels.append({"price": lows[i], "type": "support"})

    merged = []
    used = set()
    for i, level in enumerate(levels):
        if i in used:
            continue
        cluster = [level]
        for j in range(i + 1, len(levels)):
            if j in used:
                continue
            if abs(level["price"] - levels[j]["price"]) < tolerance:
                cluster.append(levels[j])
                used.add(j)
        avg_price = sum(c["price"] for c in cluster) / len(cluster)
        touches = len(cluster)
        merged.append({
            "price": round(avg_price, 2),
            "type": cluster[0]["type"],
            "touches": touches,
            "strength": min(100, touches * 25),
        })
        used.add(i)

    merged.sort(key=lambda x: x["price"])
    return merged


def analyze(ticker, period="1y"):
    """full tape reading analysis: candle patterns, volume profile, key levels"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    vol_avg = sma(volumes, 20)
    atr_vals = atr(
        [r["high"] for r in rows],
        [r["low"] for r in rows],
        closes, 14
    )

    candle_signals = []
    for i in range(1, len(rows)):
        vol_ratio = 1.0
        if vol_avg[i] and vol_avg[i] > 0:
            vol_ratio = volumes[i] / vol_avg[i]

        patterns = []
        conviction = 0

        if detect_doji(rows[i]):
            patterns.append("doji")
            conviction += 10

        if detect_hammer(rows[i]):
            patterns.append("hammer")
            conviction += 25

        if detect_shooting_star(rows[i]):
            patterns.append("shooting_star")
            conviction += 25

        engulfing = detect_engulfing(rows[i], rows[i - 1])
        if engulfing:
            patterns.append(engulfing)
            conviction += 35

        if not patterns:
            continue

        if vol_ratio > 1.5:
            conviction += 20
        elif vol_ratio > 1.2:
            conviction += 10

        if atr_vals[i] is not None and atr_vals[i] > 0:
            move = abs(closes[i] - closes[i - 1])
            if move > atr_vals[i] * 1.5:
                conviction += 15

        bias = "neutral"
        bullish_pats = {"hammer", "bullish_engulfing", "doji"}
        bearish_pats = {"shooting_star", "bearish_engulfing"}
        pat_set = set(patterns)
        if pat_set & bullish_pats and not (pat_set & bearish_pats):
            bias = "bullish"
        elif pat_set & bearish_pats and not (pat_set & bullish_pats):
            bias = "bearish"

        candle_signals.append({
            "date": rows[i]["date"],
            "price": closes[i],
            "patterns": patterns,
            "conviction": min(100, conviction),
            "vol_ratio": round(vol_ratio, 2),
            "bias": bias,
        })

    vol_profile = volume_at_price_levels(rows[-60:], 10)
    key_levels = find_support_resistance(rows)

    high_conviction = [s for s in candle_signals if s["conviction"] >= 40]

    return {
        "ticker": ticker,
        "current_price": closes[-1],
        "candle_signals": candle_signals[-20:],
        "high_conviction_signals": high_conviction[-10:],
        "total_signals": len(candle_signals),
        "volume_profile": vol_profile,
        "key_levels": key_levels,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python tape.py <ticker> [period]")
        print("  tape reading: candle patterns, volume profile, key levels")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"tape reading: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\n  price: ${result['current_price']:.2f}")
    print(f"  total candle signals: {result['total_signals']}")

    if result["high_conviction_signals"]:
        print("\nhigh conviction signals:")
        for s in result["high_conviction_signals"]:
            pats = ", ".join(s["patterns"])
            print(f"  {s['date']}  ${s['price']:>8.2f}  [{s['conviction']:>3}]  "
                  f"{s['bias']:<8}  vol={s['vol_ratio']:.1f}x  {pats}")

    if result["key_levels"]:
        print("\nkey levels:")
        for lvl in result["key_levels"][:10]:
            print(f"  ${lvl['price']:>8.2f}  {lvl['type']:<12}  "
                  f"touches={lvl['touches']}  strength={lvl['strength']}")

    if result["volume_profile"]:
        max_vol = max(v["volume"] for v in result["volume_profile"])
        print("\nvolume profile (60d):")
        for v in result["volume_profile"]:
            bar_len = int(v["volume"] / max_vol * 30) if max_vol > 0 else 0
            bar = "#" * bar_len
            print(f"  ${v['price_low']:>8.2f}-${v['price_high']:>7.2f}  {bar}")
