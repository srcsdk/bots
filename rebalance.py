#!/usr/bin/env python3
"""portfolio rebalancing with target allocation drift"""


def current_weights(holdings):
    """calculate current portfolio weights from holdings.

    holdings: dict of {ticker: market_value}
    """
    total = sum(holdings.values())
    if total == 0:
        return {}
    return {k: round(v / total, 4) for k, v in holdings.items()}


def drift(current, target):
    """calculate drift from target allocation.

    returns dict of {ticker: drift_pct} where positive = overweight.
    """
    all_tickers = set(list(current.keys()) + list(target.keys()))
    return {
        t: round(current.get(t, 0) - target.get(t, 0), 4)
        for t in all_tickers
    }


def needs_rebalance(current, target, threshold=0.05):
    """check if any position has drifted beyond threshold."""
    d = drift(current, target)
    return any(abs(v) > threshold for v in d.values())


def rebalance_orders(holdings, target, prices):
    """generate orders to rebalance portfolio to target weights.

    returns list of {ticker, action, shares, value} dicts.
    """
    total_value = sum(holdings.values())
    orders = []
    for ticker, target_weight in target.items():
        target_value = total_value * target_weight
        current_value = holdings.get(ticker, 0)
        diff = target_value - current_value
        price = prices.get(ticker, 0)
        if price > 0 and abs(diff) > price:
            shares = int(diff / price)
            if shares != 0:
                orders.append({
                    "ticker": ticker,
                    "action": "buy" if shares > 0 else "sell",
                    "shares": abs(shares),
                    "value": round(abs(shares) * price, 2),
                })
    return orders


def tax_efficient_rebalance(holdings, target, prices, lots):
    """rebalance preferring to sell lots with losses for tax harvesting.

    lots: dict of {ticker: [(shares, cost_basis)]}
    """
    orders = rebalance_orders(holdings, target, prices)
    for order in orders:
        if order["action"] == "sell":
            ticker = order["ticker"]
            price = prices.get(ticker, 0)
            ticker_lots = lots.get(ticker, [])
            loss_lots = [(s, cb) for s, cb in ticker_lots if cb > price]
            order["tax_lots"] = "loss_harvest" if loss_lots else "fifo"
    return orders


if __name__ == "__main__":
    holdings = {"AAPL": 5000, "GOOGL": 3000, "MSFT": 4000, "AMZN": 3000}
    target = {"AAPL": 0.25, "GOOGL": 0.25, "MSFT": 0.25, "AMZN": 0.25}
    prices = {"AAPL": 150, "GOOGL": 2800, "MSFT": 300, "AMZN": 3300}
    weights = current_weights(holdings)
    print("current weights:", weights)
    print("needs rebalance:", needs_rebalance(weights, target))
    orders = rebalance_orders(holdings, target, prices)
    for o in orders:
        print(f"  {o['action']} {o['shares']} {o['ticker']} (${o['value']})")
