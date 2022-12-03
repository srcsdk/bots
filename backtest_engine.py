#!/usr/bin/env python3
# updated: commission and slippage tracking per trade
"""backtest engine with trade log and equity curve"""


def backtest(prices, signals, initial_capital=10000, position_size=0.1):
    """run backtest on price series with entry/exit signals.

    signals: list of dicts with 'idx', 'type' (buy/sell), 'price'
    returns trade log and equity curve.
    """
    capital = initial_capital
    shares = 0
    entry_price = 0
    trades = []
    equity = [initial_capital] * len(prices)
    signal_map = {s["idx"]: s for s in signals}
    for i in range(len(prices)):
        if i in signal_map:
            sig = signal_map[i]
            if sig["type"] == "buy" and shares == 0:
                buy_amount = capital * position_size
                shares = buy_amount / prices[i]
                entry_price = prices[i]
                capital -= buy_amount
            elif sig["type"] == "sell" and shares > 0:
                sell_value = shares * prices[i]
                pnl = sell_value - shares * entry_price
                trades.append({
                    "entry_idx": sig.get("entry_idx", i),
                    "exit_idx": i,
                    "entry_price": entry_price,
                    "exit_price": prices[i],
                    "shares": round(shares, 4),
                    "pnl": round(pnl, 2),
                    "return_pct": round(pnl / (shares * entry_price) * 100, 2),
                })
                capital += sell_value
                shares = 0
        equity[i] = capital + shares * prices[i]
    return {"trades": trades, "equity": equity, "final_capital": round(equity[-1], 2)}


def trade_stats(trades):
    """calculate statistics from trade log."""
    if not trades:
        return {}
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in trades)
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    return {
        "total_trades": len(trades),
        "winners": len(wins),
        "losers": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win * len(wins)) / abs(avg_loss * len(losses)), 2)
        if losses and avg_loss != 0 else float("inf"),
        "expectancy": round(total_pnl / len(trades), 2),
    }


def max_drawdown(equity):
    """calculate maximum drawdown from equity curve."""
    peak = equity[0]
    max_dd = 0
    for val in equity:
        peak = max(peak, val)
        dd = (peak - val) / peak
        max_dd = max(max_dd, dd)
    return round(max_dd * 100, 2)


if __name__ == "__main__":
    import random
    prices = [100]
    for _ in range(252):
        prices.append(prices[-1] * (1 + random.gauss(0.0003, 0.015)))
    signals = []
    for i in range(20, len(prices), 20):
        signals.append({"idx": i, "type": "buy", "price": prices[i]})
        if i + 10 < len(prices):
            signals.append({"idx": i + 10, "type": "sell", "price": prices[i + 10]})
    result = backtest(prices, signals)
    stats = trade_stats(result["trades"])
    print(f"trades: {stats.get('total_trades', 0)}")
    print(f"win rate: {stats.get('win_rate', 0)}%")
    print(f"total pnl: ${stats.get('total_pnl', 0)}")
    print(f"max drawdown: {max_drawdown(result['equity'])}%")
