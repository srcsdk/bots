#!/usr/bin/env python3
"""position sizing with kelly criterion and fixed fractional"""


def kelly_fraction(win_rate, avg_win, avg_loss):
    """calculate kelly criterion fraction.

    f = (bp - q) / b
    where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate.
    """
    if avg_loss == 0:
        return 0.0
    b = avg_win / abs(avg_loss)
    q = 1 - win_rate
    f = (b * win_rate - q) / b
    return max(0.0, round(f, 4))


def fixed_fractional(account_value, risk_pct, stop_distance):
    """calculate position size using fixed fractional method."""
    risk_amount = account_value * (risk_pct / 100)
    if stop_distance <= 0:
        return 0
    shares = int(risk_amount / stop_distance)
    return shares


def max_drawdown_size(account_value, max_dd_pct, expected_streak):
    """size positions to survive expected losing streak."""
    max_dd = account_value * (max_dd_pct / 100)
    if expected_streak <= 0:
        return 0
    per_trade = max_dd / expected_streak
    return round(per_trade, 2)


if __name__ == "__main__":
    kf = kelly_fraction(0.55, 200, 150)
    print(f"kelly fraction: {kf}")
    shares = fixed_fractional(100000, 1.0, 2.50)
    print(f"position size: {shares} shares")
    mds = max_drawdown_size(100000, 10, 8)
    print(f"max risk per trade: ${mds}")
