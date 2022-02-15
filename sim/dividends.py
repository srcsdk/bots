#!/usr/bin/env python3
"""dividend and corporate action handling for portfolio sim"""


def apply_dividend(positions, symbol, dividend_per_share, reinvest=True, price=None):
    """apply dividend to position.

    if reinvest, buy more shares with dividend proceeds.
    """
    pos = positions.get(symbol)
    if not pos or pos["shares"] <= 0:
        return {"cash_received": 0, "shares_added": 0}
    total_dividend = pos["shares"] * dividend_per_share
    shares_added = 0
    if reinvest and price and price > 0:
        shares_added = int(total_dividend / price)
        pos["shares"] += shares_added
        cash_remainder = total_dividend - shares_added * price
    else:
        cash_remainder = total_dividend
    return {
        "symbol": symbol,
        "dividend_per_share": dividend_per_share,
        "total_dividend": round(total_dividend, 2),
        "shares_added": shares_added,
        "cash_received": round(cash_remainder, 2),
        "reinvested": reinvest,
    }


def apply_split(positions, symbol, ratio):
    """apply stock split to position.

    ratio: split ratio (e.g. 4 for 4:1 split).
    """
    pos = positions.get(symbol)
    if not pos:
        return None
    old_shares = pos["shares"]
    old_cost = pos["avg_cost"]
    pos["shares"] = int(old_shares * ratio)
    pos["avg_cost"] = round(old_cost / ratio, 4)
    return {
        "symbol": symbol,
        "ratio": ratio,
        "old_shares": old_shares,
        "new_shares": pos["shares"],
        "old_avg_cost": old_cost,
        "new_avg_cost": pos["avg_cost"],
    }


def dividend_yield(annual_dividend, current_price):
    """calculate dividend yield percentage."""
    if current_price <= 0:
        return 0.0
    return round(annual_dividend / current_price * 100, 2)


def ex_dividend_adjustment(price, dividend_amount):
    """adjust price for ex-dividend date."""
    return round(price - dividend_amount, 4)


if __name__ == "__main__":
    positions = {"AAPL": {"shares": 100, "avg_cost": 150.0}}
    result = apply_dividend(positions, "AAPL", 0.82, reinvest=True, price=170.0)
    print(f"dividend: ${result['total_dividend']}")
    print(f"shares added: {result['shares_added']}")
    split = apply_split(positions, "AAPL", 4)
    print(f"split: {split['old_shares']} -> {split['new_shares']}")
