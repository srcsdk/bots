#!/usr/bin/env python3
"""grid trading strategy: place buy/sell orders at fixed price intervals.

calculates optimal grid levels based on atr and support/resistance zones,
then simulates grid trading over historical data to estimate profitability.
each grid level acts as a buy-low-sell-high pair.
"""

import sys
from ohlc import fetch_ohlc
from indicators import atr, bollinger_bands


def calculate_grid_levels(price, atr_val, num_grids=10, range_mult=3.0):
    """calculate grid price levels centered around current price.

    grid spacing based on atr for adaptive sizing.
    """
    if not atr_val or atr_val <= 0:
        spacing = price * 0.01
    else:
        total_range = atr_val * range_mult * 2
        spacing = total_range / num_grids

    levels = []
    half = num_grids // 2
    for i in range(-half, half + 1):
        level = round(price + i * spacing, 2)
        if level > 0:
            levels.append(level)

    return sorted(levels), round(spacing, 2)


def find_range_bounds(highs, lows, closes, lookback=60):
    """find trading range bounds from recent price action"""
    recent_high = max(highs[-lookback:])
    recent_low = min(lows[-lookback:])

    _, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    if bb_upper[-1] and bb_lower[-1]:
        range_high = max(recent_high, bb_upper[-1])
        range_low = min(recent_low, bb_lower[-1])
    else:
        range_high = recent_high
        range_low = recent_low

    return round(range_low, 2), round(range_high, 2)


def simulate_grid(rows, grid_levels, position_size=100):
    """simulate grid trading over historical data.

    at each grid level, place a buy order. when price rises to next level,
    sell for profit. track total profit and per-level performance.
    """
    closes = [r["close"] for r in rows]
    dates = [r["date"] for r in rows]
    lows = [r["low"] for r in rows]
    highs = [r["high"] for r in rows]

    holdings = {}
    trades = []
    level_stats = {level: {"buys": 0, "sells": 0, "profit": 0} for level in grid_levels}

    for i in range(1, len(rows)):
        for j, level in enumerate(grid_levels):
            if lows[i] <= level <= highs[i]:
                if level not in holdings and closes[i - 1] > level:
                    holdings[level] = {
                        "price": level,
                        "date": dates[i],
                        "shares": position_size / level,
                    }
                    level_stats[level]["buys"] += 1

        for j, level in enumerate(grid_levels[:-1]):
            next_level = grid_levels[j + 1]
            if level in holdings and highs[i] >= next_level:
                entry = holdings[level]
                profit = entry["shares"] * (next_level - entry["price"])
                trades.append({
                    "entry_date": entry["date"],
                    "exit_date": dates[i],
                    "entry_price": entry["price"],
                    "exit_price": next_level,
                    "profit": round(profit, 2),
                    "profit_pct": round((next_level - entry["price"]) / entry["price"] * 100, 2),
                })
                level_stats[level]["sells"] += 1
                level_stats[level]["profit"] += profit
                del holdings[level]

    total_profit = sum(t["profit"] for t in trades)
    active_positions = len(holdings)
    capital_deployed = sum(position_size for _ in holdings)

    unrealized = 0
    for level, pos in holdings.items():
        unrealized += pos["shares"] * (closes[-1] - pos["price"])

    return {
        "trades": trades,
        "total_trades": len(trades),
        "total_profit": round(total_profit, 2),
        "unrealized": round(unrealized, 2),
        "active_positions": active_positions,
        "capital_in_use": round(capital_deployed, 2),
        "level_stats": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
                        for k, v in level_stats.items()},
    }


def analyze(ticker, period="1y", num_grids=10, position_size=100):
    """run grid trading analysis on a ticker"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]

    price = closes[-1]
    atr_vals = atr(highs, lows, closes, 14)
    current_atr = atr_vals[-1]

    range_low, range_high = find_range_bounds(highs, lows, closes)
    grid_levels, spacing = calculate_grid_levels(price, current_atr, num_grids)

    grid_levels = [lv for lv in grid_levels if range_low * 0.9 <= lv <= range_high * 1.1]

    sim = simulate_grid(rows, grid_levels, position_size)

    total_range = range_high - range_low
    range_pct = total_range / range_low * 100 if range_low > 0 else 0

    avg_profit_per_trade = sim["total_profit"] / sim["total_trades"] if sim["total_trades"] > 0 else 0

    total_capital = len(grid_levels) * position_size
    roi = sim["total_profit"] / total_capital * 100 if total_capital > 0 else 0
    days = len(rows)
    annual_roi = roi * 365 / days if days > 0 else 0

    return {
        "ticker": ticker,
        "price": price,
        "grid": {
            "levels": grid_levels,
            "spacing": spacing,
            "num_levels": len(grid_levels),
            "range": [range_low, range_high],
            "range_pct": round(range_pct, 1),
        },
        "simulation": sim,
        "performance": {
            "total_profit": sim["total_profit"],
            "unrealized": sim["unrealized"],
            "combined": round(sim["total_profit"] + sim["unrealized"], 2),
            "total_trades": sim["total_trades"],
            "avg_profit_per_trade": round(avg_profit_per_trade, 2),
            "total_capital_needed": round(total_capital, 2),
            "roi_pct": round(roi, 2),
            "annualized_roi_pct": round(annual_roi, 2),
        },
        "atr": round(current_atr, 2) if current_atr else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python gridbot.py <ticker> [period]")
        print("  grid trading strategy with historical simulation")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"grid trading analysis: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    g = result["grid"]
    print(f"\nprice: ${result['price']:.2f}  atr: ${result['atr']}")
    print(f"trading range: ${g['range'][0]:.2f} - ${g['range'][1]:.2f} ({g['range_pct']:.1f}%)")
    print(f"grid: {g['num_levels']} levels, ${g['spacing']:.2f} spacing")

    print("\ngrid levels:")
    stats = result["simulation"]["level_stats"]
    for level in g["levels"]:
        s = stats.get(level, {"buys": 0, "sells": 0, "profit": 0})
        marker = " <-- current" if abs(level - result["price"]) < g["spacing"] * 0.5 else ""
        print(f"  ${level:>8.2f}  buys={s['buys']:>3}  sells={s['sells']:>3}  profit=${s['profit']:>8.2f}{marker}")

    p = result["performance"]
    print("\nsimulation results:")
    print(f"  total trades:    {p['total_trades']}")
    print(f"  realized profit: ${p['total_profit']:,.2f}")
    print(f"  unrealized:      ${p['unrealized']:,.2f}")
    print(f"  combined:        ${p['combined']:,.2f}")
    print(f"  avg per trade:   ${p['avg_profit_per_trade']:.2f}")
    print(f"  capital needed:  ${p['total_capital_needed']:,.2f}")
    print(f"  roi:             {p['roi_pct']:.2f}%")
    print(f"  annualized roi:  {p['annualized_roi_pct']:.2f}%")
