#!/usr/bin/env python3
"""order fill simulation with volume-based modeling"""

import random


def market_fill(price, side, spread_bps=3):
    """simulate market order fill with bid-ask spread."""
    half_spread = price * (spread_bps / 20000)
    if side == "buy":
        return round(price + half_spread, 4)
    return round(price - half_spread, 4)


def limit_fill_check(order, bar):
    """check if limit order would fill on given bar.

    bar: dict with open, high, low, close.
    """
    if order["side"] == "buy":
        if bar["low"] <= order["limit_price"]:
            fill_price = min(order["limit_price"], bar["open"])
            return {"filled": True, "price": fill_price}
    elif order["side"] == "sell":
        if bar["high"] >= order["limit_price"]:
            fill_price = max(order["limit_price"], bar["open"])
            return {"filled": True, "price": fill_price}
    return {"filled": False}


def volume_participation(order_shares, bar_volume, max_participation=0.05):
    """calculate fillable shares based on volume participation limit."""
    max_shares = int(bar_volume * max_participation)
    filled = min(order_shares, max_shares)
    remaining = order_shares - filled
    return {"filled_shares": filled, "remaining": remaining}


def partial_fill(order_shares, bar_volume, fill_probability=0.8):
    """simulate partial fill with random component."""
    max_from_volume = int(bar_volume * 0.02)
    if random.random() > fill_probability:
        return {"filled_shares": 0, "remaining": order_shares}
    filled = min(order_shares, max_from_volume)
    return {"filled_shares": filled, "remaining": order_shares - filled}


def impact_model(price, shares, avg_volume, impact_coeff=0.1):
    """estimate price impact of a large order.

    larger orders relative to volume create more impact.
    """
    participation = shares / avg_volume if avg_volume > 0 else 1
    impact_pct = participation * impact_coeff
    impacted_price = price * (1 + impact_pct)
    return {
        "original_price": price,
        "impacted_price": round(impacted_price, 4),
        "impact_bps": round(impact_pct * 10000, 1),
        "participation_pct": round(participation * 100, 2),
    }


if __name__ == "__main__":
    buy_fill = market_fill(150.0, "buy")
    sell_fill = market_fill(150.0, "sell")
    print(f"market buy fill: {buy_fill}")
    print(f"market sell fill: {sell_fill}")
    impact = impact_model(150.0, 10000, 500000)
    print(f"price impact: {impact['impact_bps']} bps")
