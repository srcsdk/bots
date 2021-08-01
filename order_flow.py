#!/usr/bin/env python3
"""market microstructure order flow analysis"""


def classify_trades(prices, volumes):
    """classify trades as buyer or seller initiated using tick rule.

    uptick = buyer initiated, downtick = seller initiated.
    returns list of dicts with price, volume, and side.
    """
    if not prices or not volumes:
        return []
    trades = []
    prev = prices[0]
    for price, vol in zip(prices, volumes):
        if price > prev:
            side = "buy"
        elif price < prev:
            side = "sell"
        else:
            side = trades[-1]["side"] if trades else "buy"
        trades.append({"price": price, "volume": vol, "side": side})
        prev = price
    return trades


def cumulative_delta(trades):
    """calculate cumulative volume delta from classified trades.

    positive delta = buying pressure, negative = selling pressure.
    """
    delta = 0
    deltas = []
    for t in trades:
        if t["side"] == "buy":
            delta += t["volume"]
        else:
            delta -= t["volume"]
        deltas.append(delta)
    return deltas


def bid_ask_imbalance(bids, asks):
    """calculate order book imbalance ratio.

    imbalance > 0 suggests buying pressure, < 0 selling pressure.
    range is -1 to 1.
    """
    total_bid = sum(bids) if bids else 0
    total_ask = sum(asks) if asks else 0
    total = total_bid + total_ask
    if total == 0:
        return 0.0
    return (total_bid - total_ask) / total


def detect_large_trades(trades, threshold_mult=3.0):
    """detect unusually large trades relative to average volume."""
    if not trades:
        return []
    avg_vol = sum(t["volume"] for t in trades) / len(trades)
    threshold = avg_vol * threshold_mult
    return [t for t in trades if t["volume"] >= threshold]


def flow_summary(prices, volumes):
    """generate order flow summary from price and volume series."""
    trades = classify_trades(prices, volumes)
    if not trades:
        return {}
    deltas = cumulative_delta(trades)
    buy_vol = sum(t["volume"] for t in trades if t["side"] == "buy")
    sell_vol = sum(t["volume"] for t in trades if t["side"] == "sell")
    large = detect_large_trades(trades)
    return {
        "total_trades": len(trades),
        "buy_volume": buy_vol,
        "sell_volume": sell_vol,
        "net_delta": deltas[-1] if deltas else 0,
        "buy_pct": round(buy_vol / (buy_vol + sell_vol) * 100, 1),
        "large_trades": len(large),
    }


if __name__ == "__main__":
    import random
    p = [100.0]
    for _ in range(99):
        p.append(p[-1] + random.gauss(0, 0.5))
    v = [random.randint(50, 5000) for _ in range(100)]
    summary = flow_summary(p, v)
    for k, val in summary.items():
        print(f"  {k}: {val}")
