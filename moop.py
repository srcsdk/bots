#!/usr/bin/env python3
"""moop: options strategy combining lambda greeks with mobr momentum and current market data

Finds options plays where mobr signals entry on the underlying, lambda greeks
confirm a favorable options setup, and current market conditions support the
trade. Scores each factor and combines into a composite signal.

usage: python moop.py AAPL call 150 2021-04-16
"""

import importlib
import sys
from datetime import datetime

from movo import scan_mobr
from current import get_fear_greed, get_economic_calendar, get_treasury_yields

_lambda = importlib.import_module("lambda")


def score_mobr_signal(ticker, period="1y"):
    """score the underlying's mobr signal strength.

    Returns a dict with score (0-100) and details about the mobr signals.
    A recent mobr signal within the last 5 bars scores highest.
    """
    signals = scan_mobr(ticker, period)
    if not signals:
        return {"score": 0, "signal_count": 0, "latest": None, "detail": "no mobr signals found"}

    latest = signals[-1]
    total = len(signals)

    from ohlc import fetch_ohlc
    rows = fetch_ohlc(ticker, period)
    if not rows:
        return {"score": 0, "signal_count": total, "latest": latest, "detail": "could not verify recency"}

    dates = [r["date"] for r in rows]
    latest_date = latest["date"]

    recency = 0
    if latest_date in dates:
        bars_ago = len(dates) - 1 - dates.index(latest_date)
        if bars_ago <= 2:
            recency = 100
        elif bars_ago <= 5:
            recency = 75
        elif bars_ago <= 10:
            recency = 50
        elif bars_ago <= 20:
            recency = 25

    frequency_bonus = min(20, total * 5)
    score = min(100, recency + frequency_bonus)

    detail = f"{total} mobr signals, latest on {latest_date}"
    if recency >= 75:
        detail += " (active)"
    elif recency >= 50:
        detail += " (recent)"
    else:
        detail += " (stale)"

    return {"score": score, "signal_count": total, "latest": latest, "detail": detail}


def composite_signal(mobr_score, greeks_score, market_score):
    """combine the three factor scores into a composite signal.

    Weights: mobr 40%, greeks 35%, market 25%.
    Returns signal label and composite score (0-100).
    """
    weighted = mobr_score * 0.40 + greeks_score * 0.35 + market_score * 0.25
    composite = round(weighted, 1)

    if composite >= 70:
        signal = "strong buy"
    elif composite >= 55:
        signal = "buy"
    elif composite >= 40:
        signal = "hold"
    elif composite >= 25:
        signal = "weak"
    else:
        signal = "avoid"

    return signal, composite


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("usage: python moop.py <ticker> <call|put> <strike> <expiry>")
        print("  example: python moop.py AAPL call 150 2021-04-16")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    option_type = sys.argv[2].lower()
    strike = float(sys.argv[3])
    expiry = sys.argv[4]

    if option_type not in ("call", "put"):
        print("error: option type must be 'call' or 'put'", file=sys.stderr)
        sys.exit(1)

    print(f"moop: {ticker} {option_type} ${strike} exp {expiry}")
    print("(scaffold - full strategy coming soon)")
