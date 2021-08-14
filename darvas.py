#!/usr/bin/env python3
"""darvas box theory: detect consolidation boxes and trade breakouts.

nicolas darvas's method identifies stocks making new highs, then waits for
a consolidation box to form. buy on breakout above box top with volume
confirmation, trail stop at box bottom.
"""

import sys
from ohlc import fetch_ohlc
from indicators import volume_sma


def find_boxes(highs, lows, closes, min_box_days=3):
    """detect darvas boxes from price data.

    a box forms when:
    1. price makes a new high
    2. fails to make a new high for min_box_days+ consecutive days (box top set)
    3. lowest low during that period becomes box bottom
    """
    boxes = []
    n = len(closes)
    i = 0

    while i < n:
        if i < 1:
            i += 1
            continue

        is_new_high = highs[i] > max(highs[max(0, i - 20):i])
        if not is_new_high:
            i += 1
            continue

        box_top = highs[i]
        top_date_idx = i
        no_new_high_count = 0
        box_bottom = lows[i]
        j = i + 1

        while j < n:
            if highs[j] > box_top:
                break
            no_new_high_count += 1
            box_bottom = min(box_bottom, lows[j])
            j += 1

        if no_new_high_count >= min_box_days:
            boxes.append({
                "start_idx": top_date_idx,
                "end_idx": j - 1,
                "top": round(box_top, 2),
                "bottom": round(box_bottom, 2),
                "days": no_new_high_count,
                "height_pct": round((box_top - box_bottom) / box_bottom * 100, 2),
            })
            i = j
        else:
            i = j if j < n else i + 1

    return boxes


def scan(ticker, period="1y", vol_mult=1.5, min_box_days=3):
    """scan for darvas box breakout signals.

    generates buy signals when price breaks above box top with volume
    confirmation (volume > vol_mult * average volume).
    trail stop at box bottom.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 40:
        return None

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    dates = [r["date"] for r in rows]

    vol_avg = volume_sma(volumes, 20)
    boxes = find_boxes(highs, lows, closes, min_box_days)

    signals = []

    for box in boxes:
        end = box["end_idx"]
        for i in range(end + 1, min(end + 20, len(rows))):
            if closes[i] > box["top"]:
                has_volume = vol_avg[i] is not None and volumes[i] > vol_avg[i] * vol_mult
                signals.append({
                    "date": dates[i],
                    "type": "breakout",
                    "price": closes[i],
                    "box_top": box["top"],
                    "box_bottom": box["bottom"],
                    "box_days": box["days"],
                    "volume_confirmed": has_volume,
                    "volume_ratio": round(volumes[i] / vol_avg[i], 2) if vol_avg[i] else None,
                    "stop": box["bottom"],
                    "risk_pct": round((closes[i] - box["bottom"]) / closes[i] * 100, 2),
                })
                break

            if closes[i] < box["bottom"]:
                signals.append({
                    "date": dates[i],
                    "type": "breakdown",
                    "price": closes[i],
                    "box_top": box["top"],
                    "box_bottom": box["bottom"],
                })
                break

    last_box = boxes[-1] if boxes else None
    current = {
        "price": closes[-1],
        "last_box": last_box,
        "in_box": False,
        "distance_to_top": None,
    }

    if last_box and last_box["end_idx"] >= len(rows) - 5:
        current["in_box"] = True
        current["distance_to_top"] = round((last_box["top"] - closes[-1]) / closes[-1] * 100, 2)

    return {"ticker": ticker, "boxes": boxes, "signals": signals, "current": current}


def box_history(prices, volumes):
    """return all historical darvas boxes detected in a price/volume series.

    a box forms when price consolidates between a high and low for
    at least 3 bars, with volume declining.
    """
    if len(prices) < 5 or len(volumes) < 5:
        return []
    n = min(len(prices), len(volumes))
    boxes = []
    i = 0
    while i < n - 3:
        high = prices[i]
        low = prices[i]
        box_start = i
        for j in range(i + 1, min(i + 20, n)):
            if prices[j] > high * 1.02:
                break
            if prices[j] < low * 0.98:
                break
            high = max(high, prices[j])
            low = min(low, prices[j])
            if j - box_start >= 3:
                vol_start = sum(volumes[box_start:box_start + 2]) / 2
                vol_end = sum(volumes[j - 1:j + 1]) / 2
                boxes.append({
                    "start_idx": box_start,
                    "end_idx": j,
                    "top": round(high, 2),
                    "bottom": round(low, 2),
                    "width": j - box_start,
                    "vol_declining": vol_end < vol_start,
                })
                i = j
                break
        i += 1
    return boxes


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python darvas.py <ticker> [period]")
        print("  darvas box theory: breakout on consolidation boxes")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"darvas box scan: {ticker} ({period})")
    result = scan(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    boxes = result["boxes"]
    print(f"\nboxes found: {len(boxes)}")
    for b in boxes[-5:]:
        print(f"  [{b['top']:.2f} - {b['bottom']:.2f}]  {b['days']} days  height: {b['height_pct']:.1f}%")

    signals = result["signals"]
    if signals:
        print(f"\nsignals ({len(signals)}):")
        for s in signals[-10:]:
            label = s["type"].upper()
            line = f"  [{label}] {s['date']} ${s['price']:.2f}"
            if s["type"] == "breakout":
                vol_tag = "vol confirmed" if s["volume_confirmed"] else "low vol"
                line += f"  box=[{s['box_bottom']:.2f}-{s['box_top']:.2f}]  {vol_tag}"
                line += f"  stop=${s['stop']:.2f}  risk={s['risk_pct']:.1f}%"
            print(line)
    else:
        print("\nno breakout signals")

    cur = result["current"]
    if cur["in_box"]:
        print(f"\ncurrently in box, {cur['distance_to_top']:+.1f}% from box top")
    print(f"current price: ${cur['price']:.2f}")
