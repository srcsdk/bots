#!/usr/bin/env python3
"""gapup: buy when rsi <30, macd banana up, at 52wk low, recent gap down"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, macd, fifty_two_week_low, gap_percent


def scan(ticker, period="1y"):
    """scan for gapup buy signals"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return []

    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]

    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    low_52 = fifty_two_week_low(closes)
    gaps = gap_percent(opens, closes)

    signals = []
    for i in range(1, len(rows)):
        if rsi_vals[i] is None or macd_line[i] is None:
            continue
        if hist[i] is None or hist[i - 1] is None:
            continue

        at_52_low = closes[i] <= low_52[i] * 1.05
        rsi_oversold = rsi_vals[i] < 30
        macd_turning = hist[i] > hist[i - 1] and hist[i - 1] < 0

        recent_gap = False
        for j in range(max(0, i - 5), i):
            if gaps[j] is not None and gaps[j] < -2:
                recent_gap = True
                break

        if at_52_low and rsi_oversold and macd_turning and recent_gap:
            signals.append({
                "date": rows[i]["date"],
                "price": closes[i],
                "rsi": rsi_vals[i],
                "macd_hist": hist[i],
                "gap": gaps[i],
            })

    return signals


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python gapup.py <ticker> [period]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"gapup scan: {ticker} ({period})")
    signals = scan(ticker, period)

    if not signals:
        print("no signals found")
    else:
        for s in signals:
            print(f"  {s['date']} ${s['price']:.2f} "
                  f"rsi={s['rsi']:.1f} hist={s['macd_hist']:.4f}")
        print(f"\n{len(signals)} signals")


def backtest(ticker, period="2y"):
    """backtest gap down recovery strategy on historical data"""
    from ohlc import fetch_ohlc
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None
    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]
    trades = []
    for i in range(1, len(rows)):
        gap = (opens[i] - closes[i - 1]) / closes[i - 1] * 100
        if gap < -2:
            entry = opens[i]
            exit_price = closes[i]
            pnl = (exit_price - entry) / entry * 100
            trades.append({"date": rows[i]["date"], "gap": round(gap, 2), "pnl": round(pnl, 2)})
    if not trades:
        return {"ticker": ticker, "trades": 0}
    wins = [t for t in trades if t["pnl"] > 0]
    return {
        "ticker": ticker,
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl": round(sum(t["pnl"] for t in trades) / len(trades), 2),
        "best": max(t["pnl"] for t in trades),
        "worst": min(t["pnl"] for t in trades),
    }
