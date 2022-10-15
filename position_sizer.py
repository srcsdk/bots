#!/usr/bin/env python3
"""position sizing algorithms for risk management"""

import math


def kelly_fraction(win_rate, avg_win, avg_loss):
    """calculate optimal kelly criterion fraction.

    returns fraction of capital to risk per trade.
    """
    if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    win_loss_ratio = abs(avg_win / avg_loss)
    kelly = win_rate - (1 - win_rate) / win_loss_ratio
    return max(0.0, round(kelly, 4))


def half_kelly(win_rate, avg_win, avg_loss):
    """half kelly for more conservative sizing."""
    return round(kelly_fraction(win_rate, avg_win, avg_loss) / 2, 4)


def fixed_fractional(capital, risk_pct, stop_distance, price):
    """calculate shares based on fixed percentage risk.

    risk_pct: max percentage of capital to risk (0.01 = 1%)
    stop_distance: distance from entry to stop loss in price
    """
    if stop_distance <= 0 or price <= 0 or capital <= 0:
        return 0
    risk_amount = capital * risk_pct
    shares = int(risk_amount / stop_distance)
    max_shares = int(capital * 0.25 / price)
    return min(shares, max_shares)


def volatility_adjusted(capital, atr, risk_pct=0.01, atr_multiplier=2.0):
    """size position based on average true range.

    larger atr = smaller position to normalize risk.
    """
    if atr <= 0 or capital <= 0:
        return 0
    risk_per_share = atr * atr_multiplier
    risk_amount = capital * risk_pct
    return int(risk_amount / risk_per_share)


def equal_weight(capital, num_positions, price):
    """equal weight across all positions."""
    if num_positions <= 0 or price <= 0:
        return 0
    per_position = capital / num_positions
    return int(per_position / price)


def scale_in(base_size, scale_factor=0.5, max_additions=3):
    """generate scale-in sizes for averaging into position.

    returns list of (addition_number, size) tuples.
    """
    sizes = [(0, base_size)]
    current_size = base_size
    for i in range(1, max_additions + 1):
        current_size = max(1, int(current_size * scale_factor))
        sizes.append((i, current_size))
    return sizes


if __name__ == "__main__":
    k = kelly_fraction(0.55, 200, 150)
    print(f"kelly: {k:.4f}")
    print(f"half kelly: {half_kelly(0.55, 200, 150):.4f}")

    shares = fixed_fractional(100000, 0.01, 2.50, 150.0)
    print(f"fixed fractional: {shares} shares")

    vol_shares = volatility_adjusted(100000, 3.5)
    print(f"volatility adjusted: {vol_shares} shares")

    sizes = scale_in(100)
    for num, size in sizes:
        print(f"  add #{num}: {size} shares")
