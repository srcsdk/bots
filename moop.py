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


def score_lambda_greeks(spot, strike, rate, vol, t, option_type):
    """score the options greeks from lambda module.

    Evaluates delta adequacy, theta cost, vega opportunity, and gamma leverage.
    Returns a dict with score (0-100) and greeks breakdown.
    """
    if t <= 0:
        return {"score": 0, "greeks": {}, "detail": "option has expired"}

    greeks = _lambda.calc_greeks(spot, strike, rate, vol, t, option_type)
    delta = greeks["delta"]
    theta = greeks["theta"]
    vega = greeks["vega"]
    gamma = greeks["gamma"]
    price = greeks["price"]

    score = 0
    reasons = []

    abs_delta = abs(delta)
    if 0.30 <= abs_delta <= 0.70:
        score += 30
        reasons.append(f"delta {delta:.3f} in sweet spot (0.30-0.70)")
    elif 0.20 <= abs_delta < 0.30 or 0.70 < abs_delta <= 0.80:
        score += 15
        reasons.append(f"delta {delta:.3f} acceptable but not ideal")
    else:
        reasons.append(f"delta {delta:.3f} outside favorable range")

    if price > 0:
        theta_pct = abs(theta) / price
        if theta_pct < 0.01:
            score += 25
            reasons.append(f"low theta decay ({theta:.4f}, {theta_pct:.2%} of premium)")
        elif theta_pct < 0.03:
            score += 15
            reasons.append(f"moderate theta decay ({theta:.4f}, {theta_pct:.2%} of premium)")
        else:
            score += 5
            reasons.append(f"high theta decay ({theta:.4f}, {theta_pct:.2%} of premium)")
    else:
        reasons.append("zero premium, theta not applicable")

    if vega > 0.15:
        score += 25
        reasons.append(f"vega {vega:.3f} strong vol expansion potential")
    elif vega > 0.08:
        score += 15
        reasons.append(f"vega {vega:.3f} moderate vol sensitivity")
    else:
        score += 5
        reasons.append(f"vega {vega:.3f} low vol sensitivity")

    if gamma > 0.02:
        score += 20
        reasons.append(f"gamma {gamma:.4f} provides acceleration")
    elif gamma > 0.01:
        score += 10
        reasons.append(f"gamma {gamma:.4f} moderate leverage")
    else:
        reasons.append(f"gamma {gamma:.4f} limited convexity")

    return {"score": min(100, score), "greeks": greeks, "reasons": reasons, "detail": "; ".join(reasons)}


def score_market_conditions():
    """score current market conditions from current.py feeds.

    Checks fear/greed sentiment and economic calendar for risk events.
    Returns a dict with score (0-100) and condition details.
    """
    score = 50
    reasons = []

    fg = get_fear_greed()
    if fg is not None:
        sentiment = fg.get("sentiment", "neutral")
        vix = fg.get("vix", 0)
        if sentiment == "extreme fear":
            score -= 30
            reasons.append(f"extreme fear (vix {vix}) - high risk environment")
        elif sentiment == "fear":
            score -= 10
            reasons.append(f"fear (vix {vix}) - elevated caution")
        elif sentiment == "neutral":
            score += 10
            reasons.append(f"neutral sentiment (vix {vix}) - stable conditions")
        elif sentiment == "greed":
            score += 20
            reasons.append(f"greed (vix {vix}) - favorable for longs")
        elif sentiment == "extreme greed":
            score += 10
            reasons.append(f"extreme greed (vix {vix}) - may be overextended")
    else:
        reasons.append("fear/greed data unavailable")

    calendar = get_economic_calendar()
    high_impact = {"fomc", "cpi", "nfp", "gdp"}
    upcoming_high = [r for r in calendar if r["name"] in high_impact]
    if upcoming_high:
        names = ", ".join(r["name"] for r in upcoming_high)
        score -= len(upcoming_high) * 5
        reasons.append(f"high-impact events on calendar: {names}")
    else:
        score += 10
        reasons.append("no high-impact releases imminent")

    yields_data = get_treasury_yields()
    if yields_data:
        score += 5
        reasons.append(f"treasury data available ({len(yields_data)} records)")
    else:
        reasons.append("treasury yield data unavailable")

    return {"score": max(0, min(100, score)), "reasons": reasons, "detail": "; ".join(reasons)}


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


def run_moop(ticker, option_type, strike, expiry_str, rate=0.05):
    """run the full moop analysis for a given options contract.

    Combines mobr momentum scoring, lambda greeks evaluation, and current
    market conditions into a single trading recommendation.
    """
    from ohlc import fetch_ohlc

    ohlc_data = fetch_ohlc(ticker, period="6mo", interval="1d")
    if not ohlc_data:
        print(f"error: could not fetch price data for {ticker}", file=sys.stderr)
        return None

    spot = ohlc_data[-1]["close"]
    closes = [r["close"] for r in ohlc_data]

    vol = _lambda.historical_volatility(closes)
    if vol is None:
        print("error: insufficient data for volatility calculation", file=sys.stderr)
        return None

    days = _lambda.days_to_expiry(expiry_str)
    t = days / 365.0

    mobr_result = score_mobr_signal(ticker)
    greeks_result = score_lambda_greeks(spot, strike, rate, vol, t, option_type)
    market_result = score_market_conditions()

    signal, composite = composite_signal(
        mobr_result["score"], greeks_result["score"], market_result["score"]
    )

    return {
        "ticker": ticker,
        "option_type": option_type,
        "strike": strike,
        "expiry": expiry_str,
        "spot": spot,
        "hist_vol": round(vol, 4),
        "days_to_expiry": days,
        "signal": signal,
        "composite_score": composite,
        "mobr": mobr_result,
        "greeks": greeks_result,
        "market": market_result,
    }


def format_report(result):
    """format the moop analysis result as readable text."""
    if not result:
        return "no result to display"

    lines = []
    lines.append(f"moop strategy: {result['ticker']} {result['option_type'].upper()} "
                 f"${result['strike']:.2f} exp {result['expiry']}")
    lines.append(f"spot: ${result['spot']:.2f}  |  hist vol: {result['hist_vol']:.2%}  |  "
                 f"days to expiry: {result['days_to_expiry']}")
    lines.append("")

    lines.append(f"signal: {result['signal'].upper()} (composite: {result['composite_score']}/100)")
    lines.append("")

    mobr = result["mobr"]
    lines.append(f"[mobr momentum] score: {mobr['score']}/100")
    lines.append(f"  {mobr['detail']}")
    lines.append("")

    greeks = result["greeks"]
    lines.append(f"[lambda greeks] score: {greeks['score']}/100")
    g = greeks.get("greeks", {})
    if g:
        lines.append(f"  price={g.get('price', 0):.4f}  delta={g.get('delta', 0):.4f}  "
                     f"gamma={g.get('gamma', 0):.4f}  theta={g.get('theta', 0):.4f}  "
                     f"vega={g.get('vega', 0):.4f}")
    for reason in greeks.get("reasons", []):
        lines.append(f"  {reason}")
    lines.append("")

    market = result["market"]
    lines.append(f"[market conditions] score: {market['score']}/100")
    for reason in market.get("reasons", []):
        lines.append(f"  {reason}")

    return "\n".join(lines)


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

    try:
        datetime.strptime(expiry, "%Y-%m-%d")
    except ValueError:
        print("error: expiry must be YYYY-MM-DD format", file=sys.stderr)
        sys.exit(1)

    result = run_moop(ticker, option_type, strike, expiry)
    print(format_report(result))
