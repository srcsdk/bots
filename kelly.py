#!/usr/bin/env python3
"""kelly criterion position sizing for optimal bet sizing"""

import sys


def kelly_fraction(win_rate, avg_win, avg_loss):
    """calculate kelly criterion fraction.

    f* = (p * b - q) / b
    where p = win probability, q = loss probability, b = win/loss ratio
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return 0
    b = abs(avg_win / avg_loss)
    q = 1 - win_rate
    f = (win_rate * b - q) / b
    return round(max(0, f), 4)


def half_kelly(win_rate, avg_win, avg_loss):
    """half kelly for more conservative sizing"""
    return round(kelly_fraction(win_rate, avg_win, avg_loss) / 2, 4)


def kelly_from_trades(trades):
    """calculate kelly fraction from a list of trade results.

    trades: list of dicts with 'pnl_pct' key
    """
    if not trades:
        return 0
    wins = [t["pnl_pct"] for t in trades if t["pnl_pct"] > 0]
    losses = [t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0]
    if not wins or not losses:
        return 0
    win_rate = len(wins) / len(trades)
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)
    return kelly_fraction(win_rate, avg_win, avg_loss)


def optimal_allocation(strategies, capital):
    """calculate optimal capital allocation across strategies.

    strategies: dict of {name: trades_list}
    distributes capital proportionally to kelly fractions
    """
    fractions = {}
    for name, trades in strategies.items():
        f = kelly_from_trades(trades)
        if f > 0:
            fractions[name] = f

    if not fractions:
        return {}

    total_f = sum(fractions.values())
    allocation = {}
    for name, f in fractions.items():
        weight = f / total_f
        allocation[name] = {
            "kelly": f,
            "half_kelly": round(f / 2, 4),
            "weight": round(weight, 4),
            "capital": round(capital * weight, 2),
        }

    return allocation


def growth_rate(win_rate, avg_win, avg_loss, fraction):
    """calculate expected geometric growth rate for a given fraction.

    used to compare different sizing strategies
    """
    if fraction <= 0 or fraction >= 1:
        return 0
    p = win_rate
    q = 1 - p
    win_factor = 1 + fraction * avg_win / 100
    loss_factor = 1 - fraction * abs(avg_loss) / 100
    if win_factor <= 0 or loss_factor <= 0:
        return -999
    import math
    g = p * math.log(win_factor) + q * math.log(loss_factor)
    return round(g * 100, 4)


def multi_asset_kelly(assets, max_leverage=1.0):
    """extend kelly for multiple simultaneous positions with a total leverage cap.

    assets: list of dicts with keys: win_rate, avg_win, avg_loss
    max_leverage: maximum total allocation (1.0 = 100% of capital)
    returns list of dicts with kelly fraction and capped allocation
    """
    fractions = []
    for a in assets:
        f = kelly_fraction(a["win_rate"], a["avg_win"], a["avg_loss"])
        fractions.append(f)

    total = sum(fractions)
    results = []
    for i, a in enumerate(assets):
        raw = fractions[i]
        if total > max_leverage and total > 0:
            capped = round(raw / total * max_leverage, 4)
        else:
            capped = raw
        results.append({
            "asset": a.get("name", f"asset_{i}"),
            "raw_kelly": raw,
            "capped_allocation": capped,
        })
    return results


def kelly_table(win_rate, avg_win, avg_loss, steps=10):
    """generate table of kelly fractions and expected growth rates.

    shows how different fraction sizes affect expected geometric growth.
    useful for comparing full kelly vs fractional kelly approaches.
    """
    import math
    full = kelly_fraction(win_rate, avg_win, avg_loss)
    if full <= 0:
        return []
    rows = []
    for i in range(1, steps + 1):
        frac = full * i / steps
        p = win_rate
        q = 1 - p
        win_factor = 1 + frac * avg_win / 100
        loss_factor = 1 - frac * abs(avg_loss) / 100
        if win_factor <= 0 or loss_factor <= 0:
            g = -999
        else:
            g = p * math.log(win_factor) + q * math.log(loss_factor)
        rows.append({
            "fraction": round(frac, 4),
            "pct_of_kelly": round(i / steps * 100, 0),
            "growth_rate": round(g * 100, 4),
        })
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: python kelly.py <win_rate> <avg_win_pct> <avg_loss_pct>")
        print("  example: python kelly.py 0.55 3.5 2.0")
        print("  win_rate: 0-1 probability")
        print("  avg_win_pct: average winning trade %")
        print("  avg_loss_pct: average losing trade % (positive number)")
        sys.exit(1)

    win_rate = float(sys.argv[1])
    avg_win = float(sys.argv[2])
    avg_loss = float(sys.argv[3])

    full = kelly_fraction(win_rate, avg_win, avg_loss)
    half = half_kelly(win_rate, avg_win, avg_loss)

    print("\nkelly criterion")
    print(f"  win rate:   {win_rate*100:.1f}%")
    print(f"  avg win:    {avg_win:.2f}%")
    print(f"  avg loss:   {avg_loss:.2f}%")
    print(f"  full kelly: {full*100:.2f}% of capital per trade")
    print(f"  half kelly: {half*100:.2f}% of capital per trade")

    print("\ngrowth rate at different fractions:")
    for frac in [0.05, 0.10, 0.15, 0.20, half, full, 0.50]:
        g = growth_rate(win_rate, avg_win, avg_loss, frac)
        label = ""
        if frac == full:
            label = " (full kelly)"
        elif frac == half:
            label = " (half kelly)"
        print(f"  {frac*100:>5.1f}%: {g:+.4f}%/trade{label}")
