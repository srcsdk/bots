#!/usr/bin/env python3
"""tax lot tracking with fifo lifo and specific id methods"""

import json
import os
from datetime import datetime, timedelta


def add_lot(lots, ticker, shares, cost_basis, date):
    """add a new tax lot."""
    lots.setdefault(ticker, [])
    lots[ticker].append({
        "shares": shares,
        "cost_basis": cost_basis,
        "date": date,
        "remaining": shares,
    })
    return lots


def sell_fifo(lots, ticker, shares, sale_price, sale_date):
    """sell shares using first-in-first-out method."""
    if ticker not in lots:
        return [], 0
    realized = []
    remaining = shares
    for lot in lots[ticker]:
        if remaining <= 0:
            break
        if lot["remaining"] <= 0:
            continue
        sold = min(lot["remaining"], remaining)
        pnl = (sale_price - lot["cost_basis"]) * sold
        days_held = _days_between(lot["date"], sale_date)
        realized.append({
            "shares": sold,
            "cost_basis": lot["cost_basis"],
            "sale_price": sale_price,
            "pnl": round(pnl, 2),
            "term": "long" if days_held > 365 else "short",
            "days_held": days_held,
        })
        lot["remaining"] -= sold
        remaining -= sold
    total_pnl = sum(r["pnl"] for r in realized)
    return realized, round(total_pnl, 2)


def sell_lifo(lots, ticker, shares, sale_price, sale_date):
    """sell shares using last-in-first-out method."""
    if ticker not in lots:
        return [], 0
    realized = []
    remaining = shares
    for lot in reversed(lots[ticker]):
        if remaining <= 0:
            break
        if lot["remaining"] <= 0:
            continue
        sold = min(lot["remaining"], remaining)
        pnl = (sale_price - lot["cost_basis"]) * sold
        days_held = _days_between(lot["date"], sale_date)
        realized.append({
            "shares": sold, "cost_basis": lot["cost_basis"],
            "pnl": round(pnl, 2),
            "term": "long" if days_held > 365 else "short",
        })
        lot["remaining"] -= sold
        remaining -= sold
    return realized, round(sum(r["pnl"] for r in realized), 2)


def wash_sale_check(lots, ticker, sale_date, window_days=30):
    """check if a repurchase within 30 days triggers wash sale rule."""
    for lot in lots.get(ticker, []):
        days = abs(_days_between(lot["date"], sale_date))
        if days <= window_days and lot["remaining"] > 0:
            return True
    return False


def unrealized_pnl(lots, current_prices):
    """calculate unrealized pnl across all positions."""
    result = {}
    for ticker, ticker_lots in lots.items():
        price = current_prices.get(ticker, 0)
        total = sum(
            (price - lot["cost_basis"]) * lot["remaining"]
            for lot in ticker_lots if lot["remaining"] > 0
        )
        result[ticker] = round(total, 2)
    return result


def _days_between(date1, date2):
    d1 = datetime.strptime(date1, "%Y-%m-%d")
    d2 = datetime.strptime(date2, "%Y-%m-%d")
    return abs((d2 - d1).days)


if __name__ == "__main__":
    lots = {}
    add_lot(lots, "AAPL", 100, 130.0, "2021-01-15")
    add_lot(lots, "AAPL", 50, 145.0, "2021-06-01")
    add_lot(lots, "AAPL", 75, 155.0, "2021-09-10")
    realized, pnl = sell_fifo(lots, "AAPL", 120, 160.0, "2021-12-15")
    print(f"fifo sale: {len(realized)} lots, pnl=${pnl}")
    for r in realized:
        print(f"  {r['shares']}sh @ ${r['cost_basis']} -> ${r['pnl']} ({r['term']})")
