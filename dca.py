#!/usr/bin/env python3
"""dollar-cost averaging with volatility adjustment.

fixed-interval buys with rsi/volatility modifier. buys more when rsi < 30,
less when > 70. tracks average cost basis and unrealized pnl.
"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, atr, sma


def volatility_multiplier(rsi_val, atr_val, atr_avg):
    """calculate position size multiplier based on rsi and volatility.

    low rsi = buy more aggressively, high rsi = buy less.
    high volatility relative to average = slight increase (better entries).
    """
    if rsi_val is None or atr_val is None or atr_avg is None:
        return 1.0

    if rsi_val < 20:
        rsi_mult = 2.0
    elif rsi_val < 30:
        rsi_mult = 1.5
    elif rsi_val < 40:
        rsi_mult = 1.2
    elif rsi_val > 80:
        rsi_mult = 0.3
    elif rsi_val > 70:
        rsi_mult = 0.5
    elif rsi_val > 60:
        rsi_mult = 0.8
    else:
        rsi_mult = 1.0

    if atr_avg > 0:
        vol_ratio = atr_val / atr_avg
        if vol_ratio > 1.5:
            vol_mult = 1.15
        elif vol_ratio > 1.2:
            vol_mult = 1.05
        else:
            vol_mult = 1.0
    else:
        vol_mult = 1.0

    return round(rsi_mult * vol_mult, 2)


def analyze(ticker, period="1y", base_amount=100, interval_days=7):
    """simulate dca with volatility-adjusted position sizing.

    returns summary with cost basis, total invested, current value, pnl.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]

    rsi_vals = rsi(closes, 14)
    atr_vals = atr(highs, lows, closes, 14)
    atr_sma = sma([v if v is not None else 0 for v in atr_vals], 20)

    purchases = []
    total_shares = 0.0
    total_invested = 0.0

    for i in range(0, len(rows), interval_days):
        mult = volatility_multiplier(rsi_vals[i], atr_vals[i], atr_sma[i])
        amount = base_amount * mult
        shares = amount / closes[i]

        total_shares += shares
        total_invested += amount

        purchases.append({
            "date": rows[i]["date"],
            "price": closes[i],
            "amount": round(amount, 2),
            "shares": round(shares, 4),
            "multiplier": mult,
            "rsi": rsi_vals[i],
        })

    current_price = closes[-1]
    current_value = total_shares * current_price
    avg_cost = total_invested / total_shares if total_shares > 0 else 0
    unrealized_pnl = current_value - total_invested
    pnl_pct = (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0

    return {
        "ticker": ticker,
        "purchases": purchases,
        "total_invested": round(total_invested, 2),
        "total_shares": round(total_shares, 4),
        "avg_cost_basis": round(avg_cost, 2),
        "current_price": current_price,
        "current_value": round(current_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "num_buys": len(purchases),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python dca.py <ticker> [period]")
        print("  simulates volatility-adjusted dollar-cost averaging")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"dca analysis: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\n  buys: {result['num_buys']}")
    print(f"  total invested: ${result['total_invested']:,.2f}")
    print(f"  total shares: {result['total_shares']:.4f}")
    print(f"  avg cost basis: ${result['avg_cost_basis']:.2f}")
    print(f"  current price: ${result['current_price']:.2f}")
    print(f"  current value: ${result['current_value']:,.2f}")
    print(f"  unrealized pnl: ${result['unrealized_pnl']:+,.2f} ({result['pnl_pct']:+.2f}%)")

    print("\nrecent purchases:")
    for p in result["purchases"][-10:]:
        rsi_str = f"rsi={p['rsi']:.1f}" if p["rsi"] is not None else "rsi=n/a"
        print(f"  {p['date']}  ${p['price']:>8.2f}  "
              f"x{p['multiplier']:.2f}  ${p['amount']:>7.2f}  {rsi_str}")
