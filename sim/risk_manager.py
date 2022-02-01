#!/usr/bin/env python3
"""risk management for paper trading"""


def position_size_risk_pct(capital, risk_pct, entry_price, stop_price):
    """calculate position size based on risk percentage.

    risk_pct: max percentage of capital to risk per trade.
    """
    risk_amount = capital * (risk_pct / 100)
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0
    shares = int(risk_amount / risk_per_share)
    return shares


def position_size_kelly(capital, win_rate, avg_win, avg_loss, fraction=0.5):
    """kelly criterion position sizing with fractional kelly.

    fraction: use half-kelly (0.5) for conservative sizing.
    """
    if avg_loss == 0:
        return 0
    b = avg_win / abs(avg_loss)
    q = 1 - win_rate
    kelly = (b * win_rate - q) / b
    adjusted = kelly * fraction
    return round(max(0, capital * adjusted), 2)


def max_position_check(shares, price, capital, max_pct=20):
    """ensure position doesn't exceed max portfolio percentage."""
    position_value = shares * price
    max_value = capital * (max_pct / 100)
    if position_value > max_value:
        return int(max_value / price)
    return shares


def portfolio_heat(positions, prices, capital):
    """calculate total portfolio risk (heat).

    sum of individual position risks as percentage of capital.
    """
    total_risk = 0
    for sym, pos in positions.items():
        if sym not in prices:
            continue
        stop = pos.get("stop_price", 0)
        current = prices[sym]
        shares = pos.get("shares", 0)
        if stop > 0:
            risk = abs(current - stop) * shares
        else:
            risk = current * shares * 0.02
        total_risk += risk
    return round(total_risk / capital * 100, 2) if capital > 0 else 0


def risk_reward_ratio(entry, stop, target):
    """calculate risk/reward ratio for a potential trade."""
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        return float("inf")
    return round(reward / risk, 2)


if __name__ == "__main__":
    shares = position_size_risk_pct(100000, 1.0, 150.0, 145.0)
    print(f"risk-based size: {shares} shares")
    kelly_size = position_size_kelly(100000, 0.55, 200, 150)
    print(f"half-kelly size: ${kelly_size}")
    rr = risk_reward_ratio(150, 145, 165)
    print(f"risk/reward: {rr}")
