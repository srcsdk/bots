#!/usr/bin/env python3
"""margin and buying power calculations"""


def buying_power(cash, margin_positions, margin_rate=2.0):
    """calculate available buying power with margin.

    margin_rate: 2.0 = 2:1 margin (reg-t for stocks).
    """
    return cash * margin_rate - sum(
        p.get("margin_used", 0) for p in margin_positions.values()
    )


def margin_requirement(shares, price, maintenance_pct=25):
    """calculate margin requirement for a position."""
    market_value = shares * price
    initial_margin = market_value * 0.5
    maintenance_margin = market_value * (maintenance_pct / 100)
    return {
        "market_value": round(market_value, 2),
        "initial_margin": round(initial_margin, 2),
        "maintenance_margin": round(maintenance_margin, 2),
    }


def margin_call_check(equity, positions, prices, maintenance_pct=25):
    """check if account is in margin call."""
    total_market_value = sum(
        pos["shares"] * prices.get(sym, 0)
        for sym, pos in positions.items()
    )
    maintenance = total_market_value * (maintenance_pct / 100)
    margin_excess = equity - maintenance
    return {
        "equity": round(equity, 2),
        "market_value": round(total_market_value, 2),
        "maintenance_required": round(maintenance, 2),
        "margin_excess": round(margin_excess, 2),
        "margin_call": margin_excess < 0,
    }


def max_shares(cash, price, margin_rate=2.0, commission=0):
    """calculate maximum shares purchasable with margin."""
    available = cash * margin_rate - commission
    if price <= 0:
        return 0
    return int(available / price)


if __name__ == "__main__":
    bp = buying_power(50000, {})
    print(f"buying power: ${bp}")
    req = margin_requirement(100, 150.0)
    print(f"margin req for 100 shares @ $150: {req}")
    check = margin_call_check(
        25000, {"AAPL": {"shares": 200}}, {"AAPL": 150.0}
    )
    print(f"margin call: {check['margin_call']}")
