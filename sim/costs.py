#!/usr/bin/env python3
"""transaction cost modeling for backtesting"""


def commission_per_share(shares, rate=0.005, minimum=1.0):
    """calculate commission cost per share."""
    cost = shares * rate
    return max(cost, minimum)


def commission_flat(rate=4.95):
    """flat commission per trade."""
    return rate


def slippage_fixed(price, bps=5):
    """apply fixed basis point slippage to fill price.

    bps: basis points of slippage (5 = 0.05%).
    """
    return round(price * (1 + bps / 10000), 4)


def slippage_volume(price, volume, trade_size, impact_factor=0.1):
    """volume-based slippage model.

    larger trades relative to volume get more slippage.
    """
    participation = trade_size / volume if volume > 0 else 1
    slippage_bps = participation * impact_factor * 10000
    return round(price * (1 + slippage_bps / 10000), 4)


def total_cost(shares, price, commission_fn=None, slippage_bps=5):
    """calculate total transaction cost including commission and slippage."""
    if commission_fn is None:
        comm = commission_per_share(shares)
    else:
        comm = commission_fn(shares)
    fill_price = slippage_fixed(price, slippage_bps)
    price_impact = abs(fill_price - price) * shares
    return {
        "commission": round(comm, 2),
        "slippage_cost": round(price_impact, 2),
        "fill_price": fill_price,
        "total_cost": round(comm + price_impact, 2),
    }


if __name__ == "__main__":
    cost = total_cost(100, 150.0)
    print(f"100 shares @ $150:")
    for k, v in cost.items():
        print(f"  {k}: {v}")
