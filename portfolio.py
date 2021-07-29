#!/usr/bin/env python3
"""portfolio tracker with position sizing and allocation"""

import json
import os
import sys
from ohlc import fetch_ohlc


PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")


def load_portfolio():
    """load portfolio from json file"""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"cash": 10000.0, "positions": {}}


def save_portfolio(portfolio):
    """save portfolio to json file"""
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def position_size(capital, risk_pct, entry, stop_loss):
    """calculate position size based on risk percentage.

    risk_pct: fraction of capital to risk (e.g. 0.02 for 2%)
    returns number of shares to buy
    """
    if entry <= stop_loss or entry <= 0:
        return 0
    risk_per_share = entry - stop_loss
    dollar_risk = capital * risk_pct
    shares = int(dollar_risk / risk_per_share)
    max_shares = int(capital * 0.25 / entry)
    return min(shares, max_shares)


def add_position(portfolio, ticker, shares, price):
    """add a position to the portfolio"""
    cost = shares * price
    if cost > portfolio["cash"]:
        return False
    portfolio["cash"] -= cost
    if ticker in portfolio["positions"]:
        pos = portfolio["positions"][ticker]
        total_shares = pos["shares"] + shares
        total_cost = pos["avg_price"] * pos["shares"] + cost
        pos["avg_price"] = round(total_cost / total_shares, 2)
        pos["shares"] = total_shares
    else:
        portfolio["positions"][ticker] = {
            "shares": shares,
            "avg_price": price,
        }
    save_portfolio(portfolio)
    return True


def close_position(portfolio, ticker, price):
    """close a position and return pnl"""
    if ticker not in portfolio["positions"]:
        return None
    pos = portfolio["positions"][ticker]
    proceeds = pos["shares"] * price
    cost_basis = pos["shares"] * pos["avg_price"]
    pnl = proceeds - cost_basis
    portfolio["cash"] += proceeds
    del portfolio["positions"][ticker]
    save_portfolio(portfolio)
    return round(pnl, 2)


def portfolio_value(portfolio):
    """calculate total portfolio value at current prices"""
    total = portfolio["cash"]
    for ticker, pos in portfolio["positions"].items():
        rows = fetch_ohlc(ticker, "1mo")
        if rows:
            current = rows[-1]["close"]
            total += pos["shares"] * current
    return round(total, 2)


def allocation_pcts(portfolio):
    """calculate allocation percentages"""
    total = portfolio_value(portfolio)
    if total <= 0:
        return {}
    alloc = {"cash": round(portfolio["cash"] / total * 100, 1)}
    for ticker, pos in portfolio["positions"].items():
        rows = fetch_ohlc(ticker, "1mo")
        if rows:
            current = rows[-1]["close"]
            value = pos["shares"] * current
            alloc[ticker] = round(value / total * 100, 1)
    return alloc


def rebalance_targets(portfolio, targets):
    """calculate trades needed to reach target allocation.

    targets: dict of {ticker: target_pct} where pcts sum to <= 100
    returns list of (ticker, action, shares) tuples
    """
    total = portfolio_value(portfolio)
    current = allocation_pcts(portfolio)
    trades = []

    for ticker, target_pct in targets.items():
        current_pct = current.get(ticker, 0)
        diff_pct = target_pct - current_pct
        if abs(diff_pct) < 1:
            continue
        dollar_diff = total * diff_pct / 100
        rows = fetch_ohlc(ticker, "1mo")
        if not rows:
            continue
        price = rows[-1]["close"]
        shares = int(abs(dollar_diff) / price)
        if shares == 0:
            continue
        action = "buy" if diff_pct > 0 else "sell"
        trades.append((ticker, action, shares, price))

    return trades


if __name__ == "__main__":
    portfolio = load_portfolio()

    if len(sys.argv) < 2:
        print("portfolio tracker")
        print(f"  cash:  ${portfolio['cash']:,.2f}")
        total = 0
        for ticker, pos in portfolio["positions"].items():
            value = pos["shares"] * pos["avg_price"]
            total += value
            print(f"  {ticker:<6} {pos['shares']:>5} shares @ ${pos['avg_price']:.2f}"
                  f"  (${value:,.2f})")
        print(f"  total: ${portfolio['cash'] + total:,.2f}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "size":
        if len(sys.argv) < 5:
            print("usage: portfolio.py size <capital> <entry> <stop_loss>")
            sys.exit(1)
        capital = float(sys.argv[2])
        entry = float(sys.argv[3])
        stop = float(sys.argv[4])
        shares = position_size(capital, 0.02, entry, stop)
        print(f"position size: {shares} shares")
        print(f"  risk: ${capital * 0.02:,.2f} (2%)")
        print(f"  cost: ${shares * entry:,.2f}")
    elif cmd == "buy":
        ticker = sys.argv[2].upper()
        shares = int(sys.argv[3])
        price = float(sys.argv[4])
        if add_position(portfolio, ticker, shares, price):
            print(f"bought {shares} {ticker} @ ${price:.2f}")
        else:
            print("insufficient cash")
    elif cmd == "sell":
        ticker = sys.argv[2].upper()
        rows = fetch_ohlc(ticker, "1mo")
        price = float(sys.argv[3]) if len(sys.argv) > 3 else rows[-1]["close"]
        pnl = close_position(portfolio, ticker, price)
        if pnl is not None:
            print(f"closed {ticker} @ ${price:.2f}  pnl: ${pnl:+,.2f}")
        else:
            print(f"no position in {ticker}")
