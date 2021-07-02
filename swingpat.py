#!/usr/bin/env python3
"""swing trading pattern recognition.

detects classic chart patterns: higher highs/higher lows (uptrend),
double bottom, ascending triangle, bull flag. scores pattern quality
based on volume confirmation and structure clarity.
"""

import sys
from ohlc import fetch_ohlc
from indicators import sma, rsi


def find_swing_points(highs, lows, lookback=5):
    """identify swing highs and swing lows from price data.

    a swing high is a high surrounded by lower highs on both sides.
    a swing low is a low surrounded by higher lows on both sides.
    """
    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(highs) - lookback):
        is_high = True
        is_low = True
        for j in range(1, lookback + 1):
            if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                is_high = False
            if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                is_low = False

        if is_high:
            swing_highs.append({"index": i, "price": highs[i]})
        if is_low:
            swing_lows.append({"index": i, "price": lows[i]})

    return swing_highs, swing_lows


def detect_uptrend(swing_highs, swing_lows, min_points=3):
    """detect higher highs and higher lows pattern"""
    patterns = []

    if len(swing_highs) < min_points or len(swing_lows) < min_points:
        return patterns

    for i in range(len(swing_highs) - min_points + 1):
        hh_run = [swing_highs[i]]
        for j in range(i + 1, len(swing_highs)):
            if swing_highs[j]["price"] > hh_run[-1]["price"]:
                hh_run.append(swing_highs[j])

        if len(hh_run) < min_points:
            continue

        start_idx = hh_run[0]["index"]
        end_idx = hh_run[-1]["index"]
        matching_lows = [s for s in swing_lows if start_idx <= s["index"] <= end_idx]

        hl_count = 0
        for k in range(1, len(matching_lows)):
            if matching_lows[k]["price"] > matching_lows[k - 1]["price"]:
                hl_count += 1

        if hl_count >= min_points - 2:
            quality = min(100, len(hh_run) * 20 + hl_count * 15)
            patterns.append({
                "type": "uptrend_hh_hl",
                "start_idx": start_idx,
                "end_idx": end_idx,
                "higher_highs": len(hh_run),
                "higher_lows": hl_count + 1,
                "quality": quality,
            })
        break

    return patterns


def detect_double_bottom(swing_lows, closes, tolerance=0.03):
    """detect double bottom pattern (two lows at similar price)"""
    patterns = []

    for i in range(len(swing_lows) - 1):
        for j in range(i + 1, min(i + 5, len(swing_lows))):
            low_a = swing_lows[i]["price"]
            low_b = swing_lows[j]["price"]
            idx_a = swing_lows[i]["index"]
            idx_b = swing_lows[j]["index"]

            if idx_b - idx_a < 10:
                continue

            price_diff = abs(low_a - low_b) / low_a
            if price_diff > tolerance:
                continue

            neckline = max(closes[idx_a:idx_b + 1])
            depth = (neckline - min(low_a, low_b)) / neckline * 100

            if depth < 3:
                continue

            confirmed = False
            if idx_b + 5 < len(closes):
                for k in range(idx_b + 1, min(idx_b + 15, len(closes))):
                    if closes[k] > neckline:
                        confirmed = True
                        break

            quality = 50
            if confirmed:
                quality += 30
            if depth > 5:
                quality += 10
            if 20 < idx_b - idx_a < 60:
                quality += 10

            patterns.append({
                "type": "double_bottom",
                "first_low_idx": idx_a,
                "second_low_idx": idx_b,
                "price_level": round(min(low_a, low_b), 2),
                "neckline": round(neckline, 2),
                "depth_pct": round(depth, 2),
                "confirmed": confirmed,
                "quality": min(100, quality),
            })

    return patterns


def detect_bull_flag(closes, highs, lows, volumes, lookback=30):
    """detect bull flag: sharp rally followed by tight consolidation"""
    patterns = []
    vol_avg = sma(volumes, 20)

    for i in range(lookback, len(closes) - 10):
        pole_start = i - lookback
        pole_move = (highs[i] - lows[pole_start]) / lows[pole_start] * 100

        if pole_move < 5:
            continue

        flag_end = min(i + 15, len(closes))
        flag_range = max(highs[i:flag_end]) - min(lows[i:flag_end])
        flag_pct = flag_range / closes[i] * 100

        if flag_pct > pole_move * 0.5:
            continue

        flag_drift = (closes[flag_end - 1] - closes[i]) / closes[i] * 100
        if flag_drift > 0:
            continue

        vol_declining = True
        if vol_avg[i] and vol_avg[i] > 0:
            avg_flag_vol = sum(volumes[i:flag_end]) / (flag_end - i)
            if avg_flag_vol > vol_avg[i]:
                vol_declining = False

        quality = 40
        if vol_declining:
            quality += 20
        if pole_move > 10:
            quality += 15
        if flag_pct < pole_move * 0.3:
            quality += 15
        if -3 < flag_drift < 0:
            quality += 10

        patterns.append({
            "type": "bull_flag",
            "pole_start_idx": pole_start,
            "flag_start_idx": i,
            "flag_end_idx": flag_end - 1,
            "pole_move_pct": round(pole_move, 2),
            "flag_range_pct": round(flag_pct, 2),
            "vol_declining": vol_declining,
            "quality": min(100, quality),
        })

    return patterns


def analyze(ticker, period="1y"):
    """scan for swing trading patterns and score quality"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return None

    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    volumes = [r["volume"] for r in rows]

    swing_highs, swing_lows = find_swing_points(highs, lows, 5)
    rsi_vals = rsi(closes, 14)

    all_patterns = []

    uptrends = detect_uptrend(swing_highs, swing_lows)
    for p in uptrends:
        p["start_date"] = rows[p["start_idx"]]["date"]
        p["end_date"] = rows[p["end_idx"]]["date"]
        all_patterns.append(p)

    double_bottoms = detect_double_bottom(swing_lows, closes)
    for p in double_bottoms:
        p["first_date"] = rows[p["first_low_idx"]]["date"]
        p["second_date"] = rows[p["second_low_idx"]]["date"]
        all_patterns.append(p)

    bull_flags = detect_bull_flag(closes, highs, lows, volumes)
    for p in bull_flags:
        p["flag_start_date"] = rows[p["flag_start_idx"]]["date"]
        p["flag_end_date"] = rows[p["flag_end_idx"]]["date"]
        all_patterns.append(p)

    all_patterns.sort(key=lambda p: p.get("quality", 0), reverse=True)

    return {
        "ticker": ticker,
        "swing_highs": len(swing_highs),
        "swing_lows": len(swing_lows),
        "patterns": all_patterns,
        "total_patterns": len(all_patterns),
        "current_price": closes[-1],
        "current_rsi": rsi_vals[-1],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python swingpat.py <ticker> [period]")
        print("  detects swing trading chart patterns")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"swing pattern scan: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\n  price: ${result['current_price']:.2f}  rsi: {result['current_rsi']:.1f}")
    print(f"  swing highs: {result['swing_highs']}  swing lows: {result['swing_lows']}")
    print(f"  patterns found: {result['total_patterns']}")

    if result["patterns"]:
        print("\ndetected patterns:")
        for p in result["patterns"][:10]:
            if p["type"] == "uptrend_hh_hl":
                print(f"  [{p['quality']:>3}] uptrend  {p['start_date']} -> {p['end_date']}  "
                      f"HH={p['higher_highs']} HL={p['higher_lows']}")
            elif p["type"] == "double_bottom":
                conf = "confirmed" if p["confirmed"] else "unconfirmed"
                print(f"  [{p['quality']:>3}] double bottom  {p['first_date']} / {p['second_date']}  "
                      f"${p['price_level']:.2f}  neck=${p['neckline']:.2f}  {conf}")
            elif p["type"] == "bull_flag":
                print(f"  [{p['quality']:>3}] bull flag  {p['flag_start_date']} -> {p['flag_end_date']}  "
                      f"pole={p['pole_move_pct']:.1f}%  flag={p['flag_range_pct']:.1f}%")
    else:
        print("\nno patterns detected")
