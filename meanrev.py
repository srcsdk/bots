#!/usr/bin/env python3
"""mean reversion strategy: buy oversold, sell overbought"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, bollinger_bands, sma


def zscore_deviation(closes, period=20):
    """calculate z-score deviation from rolling mean"""
    result = [None] * (period - 1)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = variance ** 0.5
        if std == 0:
            result.append(0)
        else:
            result.append(round((closes[i] - mean) / std, 4))
    return result


def scan(ticker, period="1y", rsi_low=25, rsi_high=75, bb_threshold=0.02):
    """scan for mean reversion entries.

    buy when: rsi oversold + price below lower bollinger + negative z-score
    sell when: rsi overbought + price above upper bollinger + positive z-score
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 40:
        return []

    closes = [r["close"] for r in rows]
    rsi_vals = rsi(closes, 14)
    _, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    z_scores = zscore_deviation(closes, 20)

    signals = []
    for i in range(1, len(rows)):
        if rsi_vals[i] is None or bb_upper[i] is None or z_scores[i] is None:
            continue

        below_bb = closes[i] < bb_lower[i] * (1 + bb_threshold)
        above_bb = closes[i] > bb_upper[i] * (1 - bb_threshold)

        if rsi_vals[i] < rsi_low and below_bb and z_scores[i] < -1.5:
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "type": "buy",
                "rsi": rsi_vals[i],
                "zscore": z_scores[i],
                "bb_lower": bb_lower[i],
            })
        elif rsi_vals[i] > rsi_high and above_bb and z_scores[i] > 1.5:
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "type": "sell",
                "rsi": rsi_vals[i],
                "zscore": z_scores[i],
                "bb_upper": bb_upper[i],
            })

    return signals


def backtest_meanrev(ticker, period="2y"):
    """backtest mean reversion with paired entry/exit"""
    signals = scan(ticker, period)
    if not signals:
        return None

    trades = []
    entry = None
    for sig in signals:
        if sig["type"] == "buy" and entry is None:
            entry = sig
        elif sig["type"] == "sell" and entry is not None:
            pnl = (sig["price"] - entry["price"]) / entry["price"] * 100
            trades.append({
                "entry_date": entry["date"],
                "exit_date": sig["date"],
                "entry_price": entry["price"],
                "exit_price": sig["price"],
                "pnl_pct": round(pnl, 2),
            })
            entry = None

    if not trades:
        return {"ticker": ticker, "trades": 0}

    wins = [t for t in trades if t["pnl_pct"] > 0]
    return {
        "ticker": ticker,
        "trades": len(trades),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl": round(sum(t["pnl_pct"] for t in trades) / len(trades), 2),
        "total_pnl": round(sum(t["pnl_pct"] for t in trades), 2),
        "best": max(t["pnl_pct"] for t in trades),
        "worst": min(t["pnl_pct"] for t in trades),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python meanrev.py <ticker> [period]")
        print("  scans for mean reversion buy/sell signals")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"mean reversion scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            direction = "BUY" if s["type"] == "buy" else "SELL"
            print(f"  [{direction}] {s['date']} ${s['price']:.2f}  "
                  f"rsi={s['rsi']:.1f} z={s['zscore']:+.2f}")
        print(f"\n{len(signals)} signals")

    if period in ("2y", "5y"):
        result = backtest_meanrev(ticker, period)
        if result and result["trades"] > 0:
            print(f"\nbacktest:")
            print(f"  trades: {result['trades']}  win rate: {result['win_rate']}%")
            print(f"  avg pnl: {result['avg_pnl']}%  total: {result['total_pnl']}%")
