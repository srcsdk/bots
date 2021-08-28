#!/usr/bin/env python3
"""turtle trading strategy: donchian channel breakouts with atr-based position sizing.

based on richard dennis's turtle trading system. uses 20-day donchian channel
for entries and 10-day channel for exits, with atr-based stops and pyramiding.
"""

import sys
from ohlc import fetch_ohlc
from indicators import atr


def donchian_channel(highs, lows, period):
    """calculate donchian channel (highest high, lowest low over period)"""
    upper = [None] * (period - 1)
    lower = [None] * (period - 1)
    for i in range(period - 1, len(highs)):
        upper.append(max(highs[i - period + 1:i + 1]))
        lower.append(min(lows[i - period + 1:i + 1]))
    return upper, lower


def position_size(equity, atr_value, risk_pct=0.01):
    """calculate position size based on atr (1% risk per unit).

    unit size = (equity * risk_pct) / atr_value
    """
    if atr_value <= 0:
        return 0
    return int((equity * risk_pct) / atr_value)


def scan(ticker, period="1y", entry_period=20, exit_period=10, max_units=4):
    """scan for turtle trading signals.

    entry: price breaks above 20-day high (long) or below 20-day low (short)
    exit: price breaks below 10-day low (long exit) or above 10-day high (short exit)
    stop: 2 * atr from entry
    pyramiding: add unit every 0.5 * atr move in profit direction, up to max_units
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < max(entry_period, exit_period) + 15:
        return None

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]

    entry_upper, entry_lower = donchian_channel(highs, lows, entry_period)
    exit_upper, exit_lower = donchian_channel(highs, lows, exit_period)
    atr_vals = atr(highs, lows, closes, 20)

    signals = []
    position = None
    units = 0
    last_add_price = 0

    for i in range(1, len(rows)):
        if entry_upper[i] is None or exit_lower[i] is None or atr_vals[i] is None:
            continue

        current_atr = atr_vals[i]

        if position is None:
            if closes[i] > entry_upper[i - 1] if entry_upper[i - 1] else False:
                position = "long"
                units = 1
                last_add_price = closes[i]
                stop = closes[i] - 2 * current_atr
                signals.append({
                    "date": rows[i]["date"],
                    "type": "buy",
                    "price": closes[i],
                    "units": units,
                    "stop": round(stop, 2),
                    "atr": round(current_atr, 2),
                    "channel_high": entry_upper[i],
                })
            elif closes[i] < entry_lower[i - 1] if entry_lower[i - 1] else False:
                position = "short"
                units = 1
                last_add_price = closes[i]
                stop = closes[i] + 2 * current_atr
                signals.append({
                    "date": rows[i]["date"],
                    "type": "sell_short",
                    "price": closes[i],
                    "units": units,
                    "stop": round(stop, 2),
                    "atr": round(current_atr, 2),
                    "channel_low": entry_lower[i],
                })

        elif position == "long":
            if closes[i] < exit_lower[i]:
                signals.append({
                    "date": rows[i]["date"],
                    "type": "exit_long",
                    "price": closes[i],
                    "units": units,
                    "exit_channel": exit_lower[i],
                })
                position = None
                units = 0
            elif units < max_units and closes[i] >= last_add_price + 0.5 * current_atr:
                units += 1
                last_add_price = closes[i]
                stop = closes[i] - 2 * current_atr
                signals.append({
                    "date": rows[i]["date"],
                    "type": "pyramid_long",
                    "price": closes[i],
                    "units": units,
                    "stop": round(stop, 2),
                })

        elif position == "short":
            if closes[i] > exit_upper[i]:
                signals.append({
                    "date": rows[i]["date"],
                    "type": "exit_short",
                    "price": closes[i],
                    "units": units,
                    "exit_channel": exit_upper[i],
                })
                position = None
                units = 0
            elif units < max_units and closes[i] <= last_add_price - 0.5 * current_atr:
                units += 1
                last_add_price = closes[i]
                stop = closes[i] + 2 * current_atr
                signals.append({
                    "date": rows[i]["date"],
                    "type": "pyramid_short",
                    "price": closes[i],
                    "units": units,
                    "stop": round(stop, 2),
                })

    current = {
        "price": closes[-1],
        "atr": round(atr_vals[-1], 2) if atr_vals[-1] else None,
        "donchian_high": entry_upper[-1],
        "donchian_low": entry_lower[-1],
        "exit_high": exit_upper[-1],
        "exit_low": exit_lower[-1],
        "position": position,
        "units": units,
        "unit_size": position_size(100000, atr_vals[-1]) if atr_vals[-1] else 0,
    }

    return {"ticker": ticker, "signals": signals, "current": current}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python turtle.py <ticker> [period]")
        print("  turtle trading: donchian channel breakout strategy")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"turtle trading scan: {ticker} ({period})")
    result = scan(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    cur = result["current"]
    print(f"\ncurrent: ${cur['price']:.2f}  atr: {cur['atr']}")
    print(f"  donchian [{cur['donchian_low']:.2f} - {cur['donchian_high']:.2f}]")
    print(f"  exit channel [{cur['exit_low']:.2f} - {cur['exit_high']:.2f}]")
    print(f"  unit size (100k account): {cur['unit_size']} shares")

    if cur["position"]:
        print(f"  active position: {cur['position']} ({cur['units']} units)")

    signals = result["signals"]
    if signals:
        print(f"\nsignals ({len(signals)}):")
        for s in signals[-15:]:
            label = s["type"].upper().replace("_", " ")
            line = f"  [{label}] {s['date']} ${s['price']:.2f}"
            if "stop" in s:
                line += f"  stop=${s['stop']:.2f}"
            if "units" in s:
                line += f"  units={s['units']}"
            print(line)
    else:
        print("\nno signals found")
