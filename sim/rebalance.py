#!/usr/bin/env python3
"""portfolio rebalancing to maintain target allocations"""


def target_allocation(portfolio_value, targets, prices):
    """calculate shares needed to hit target allocation.

    targets: dict of symbol -> target percentage (0-100).
    prices: dict of symbol -> current price.
    """
    orders = {}
    for symbol, target_pct in targets.items():
        if symbol not in prices or prices[symbol] <= 0:
            continue
        target_value = portfolio_value * (target_pct / 100)
        target_shares = int(target_value / prices[symbol])
        orders[symbol] = target_shares
    return orders


def rebalance_orders(current_positions, target_shares):
    """determine buy/sell orders to reach target allocation."""
    orders = []
    all_symbols = set(list(current_positions.keys()) + list(target_shares.keys()))
    for symbol in sorted(all_symbols):
        current = current_positions.get(symbol, 0)
        target = target_shares.get(symbol, 0)
        diff = target - current
        if diff > 0:
            orders.append({
                "symbol": symbol, "action": "buy", "shares": diff,
            })
        elif diff < 0:
            orders.append({
                "symbol": symbol, "action": "sell", "shares": abs(diff),
            })
    return orders


def drift_check(current_positions, prices, targets, threshold=5.0):
    """check if portfolio has drifted beyond threshold from targets."""
    total = sum(
        current_positions.get(s, 0) * prices.get(s, 0)
        for s in set(list(current_positions.keys()) + list(targets.keys()))
    )
    if total <= 0:
        return []
    drifted = []
    for symbol, target_pct in targets.items():
        actual_value = current_positions.get(symbol, 0) * prices.get(symbol, 0)
        actual_pct = (actual_value / total) * 100
        drift = abs(actual_pct - target_pct)
        if drift > threshold:
            drifted.append({
                "symbol": symbol,
                "target_pct": target_pct,
                "actual_pct": round(actual_pct, 2),
                "drift": round(drift, 2),
            })
    return drifted


def rebalance_cost(orders, prices, commission_per_trade=1.0):
    """estimate total cost of rebalancing."""
    total_cost = 0
    for order in orders:
        price = prices.get(order["symbol"], 0)
        total_cost += order["shares"] * price * 0.001
        total_cost += commission_per_trade
    return round(total_cost, 2)


if __name__ == "__main__":
    positions = {"AAPL": 50, "MSFT": 30, "GLD": 100}
    prices = {"AAPL": 170.0, "MSFT": 300.0, "GLD": 180.0}
    targets = {"AAPL": 40, "MSFT": 30, "GLD": 30}
    total_value = sum(positions[s] * prices[s] for s in positions)
    print(f"portfolio value: ${total_value:,.2f}")
    target_sh = target_allocation(total_value, targets, prices)
    orders = rebalance_orders(positions, target_sh)
    for o in orders:
        print(f"  {o['action']} {o['shares']} {o['symbol']}")
    cost = rebalance_cost(orders, prices)
    print(f"estimated rebalance cost: ${cost}")
