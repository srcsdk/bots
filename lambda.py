#!/usr/bin/env python3
"""lambda: options strategy based on greeks"""

import math
import sys
from datetime import datetime

from ohlc import fetch_ohlc
from indicators import rsi, macd, sma, bollinger_bands


def norm_cdf(x):
    """standard normal cumulative distribution using math.erf"""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x):
    """standard normal probability density"""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def d1(spot, strike, rate, vol, t):
    """black-scholes d1 term"""
    return (math.log(spot / strike) + (rate + 0.5 * vol * vol) * t) / (vol * math.sqrt(t))


def d2(spot, strike, rate, vol, t):
    """black-scholes d2 term"""
    return d1(spot, strike, rate, vol, t) - vol * math.sqrt(t)


def bs_price(spot, strike, rate, vol, t, option_type="call"):
    """black-scholes option price"""
    if t <= 0 or vol <= 0:
        if option_type == "call":
            return max(spot - strike, 0.0)
        return max(strike - spot, 0.0)

    d1_val = d1(spot, strike, rate, vol, t)
    d2_val = d2(spot, strike, rate, vol, t)

    if option_type == "call":
        price = spot * norm_cdf(d1_val) - strike * math.exp(-rate * t) * norm_cdf(d2_val)
    else:
        price = strike * math.exp(-rate * t) * norm_cdf(-d2_val) - spot * norm_cdf(-d1_val)

    return max(price, 0.0)


def calc_delta(spot, strike, rate, vol, t, option_type="call"):
    """option delta: sensitivity to underlying price"""
    if t <= 0 or vol <= 0:
        if option_type == "call":
            return 1.0 if spot > strike else 0.0
        return -1.0 if spot < strike else 0.0

    d1_val = d1(spot, strike, rate, vol, t)
    if option_type == "call":
        return norm_cdf(d1_val)
    return norm_cdf(d1_val) - 1.0


def calc_gamma(spot, strike, rate, vol, t):
    """option gamma: rate of change of delta"""
    if t <= 0 or vol <= 0 or spot <= 0:
        return 0.0
    d1_val = d1(spot, strike, rate, vol, t)
    return norm_pdf(d1_val) / (spot * vol * math.sqrt(t))


def calc_theta(spot, strike, rate, vol, t, option_type="call"):
    """option theta: time decay per calendar day"""
    if t <= 0 or vol <= 0:
        return 0.0

    d1_val = d1(spot, strike, rate, vol, t)
    d2_val = d2(spot, strike, rate, vol, t)

    common = -(spot * norm_pdf(d1_val) * vol) / (2.0 * math.sqrt(t))

    if option_type == "call":
        theta = common - rate * strike * math.exp(-rate * t) * norm_cdf(d2_val)
    else:
        theta = common + rate * strike * math.exp(-rate * t) * norm_cdf(-d2_val)

    return theta / 365.0


def calc_vega(spot, strike, rate, vol, t):
    """option vega: sensitivity to volatility (per 1% move)"""
    if t <= 0 or vol <= 0:
        return 0.0
    d1_val = d1(spot, strike, rate, vol, t)
    return spot * norm_pdf(d1_val) * math.sqrt(t) / 100.0


def calc_greeks(spot, strike, rate, vol, t, option_type="call"):
    """calculate all greeks for an option"""
    return {
        "price": round(bs_price(spot, strike, rate, vol, t, option_type), 4),
        "delta": round(calc_delta(spot, strike, rate, vol, t, option_type), 4),
        "gamma": round(calc_gamma(spot, strike, rate, vol, t), 4),
        "theta": round(calc_theta(spot, strike, rate, vol, t, option_type), 4),
        "vega": round(calc_vega(spot, strike, rate, vol, t), 4),
    }


def implied_volatility(market_price, spot, strike, rate, t, option_type="call"):
    """solve for implied vol using bisection method"""
    if market_price <= 0:
        return 0.0

    low = 0.01
    high = 5.0

    for _ in range(100):
        mid = (low + high) / 2.0
        price = bs_price(spot, strike, rate, mid, t, option_type)

        if abs(price - market_price) < 0.0001:
            return mid

        if price < market_price:
            low = mid
        else:
            high = mid

    return (low + high) / 2.0


def historical_volatility(closes, window=30):
    """annualized historical volatility from closing prices"""
    if len(closes) < window + 1:
        return None

    recent = closes[-(window + 1):]
    log_returns = [math.log(recent[i] / recent[i - 1]) for i in range(1, len(recent))]

    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)

    return math.sqrt(variance * 252)


def days_to_expiry(expiry_str):
    """calendar days from today to expiry date"""
    expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
    today = datetime.now()
    delta = (expiry - today).days
    return max(delta, 0)


def check_technical_signals(ohlc_data):
    """check underlying technicals for confirmation signals"""
    closes = [r["close"] for r in ohlc_data]

    if len(closes) < 30:
        return {"trend": "unknown", "momentum": "neutral", "signals": []}

    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, histogram = macd(closes)
    _, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)

    signals = []
    current_price = closes[-1]

    trend = "neutral"
    if sma_20[-1] is not None and sma_50[-1] is not None:
        if sma_20[-1] > sma_50[-1]:
            trend = "bullish"
        elif sma_20[-1] < sma_50[-1]:
            trend = "bearish"

    momentum = "neutral"
    if rsi_vals[-1] is not None:
        if rsi_vals[-1] > 70:
            momentum = "overbought"
            signals.append("rsi_overbought")
        elif rsi_vals[-1] < 30:
            momentum = "oversold"
            signals.append("rsi_oversold")

    if histogram[-1] is not None and histogram[-2] is not None:
        if histogram[-1] > 0 and histogram[-2] <= 0:
            signals.append("macd_bullish_cross")
        elif histogram[-1] < 0 and histogram[-2] >= 0:
            signals.append("macd_bearish_cross")

    if bb_lower[-1] is not None and current_price <= bb_lower[-1]:
        signals.append("bb_lower_touch")
    if bb_upper[-1] is not None and current_price >= bb_upper[-1]:
        signals.append("bb_upper_touch")

    return {"trend": trend, "momentum": momentum, "signals": signals}


def evaluate_option(spot, strike, rate, vol, t, option_type, technicals):
    """evaluate an option contract and generate trading signal"""
    if t <= 0:
        return {"signal": "expired", "reason": "option has expired"}

    greeks = calc_greeks(spot, strike, rate, vol, t, option_type)
    delta = greeks["delta"]
    theta = greeks["theta"]
    vega = greeks["vega"]
    gamma = greeks["gamma"]

    scores = []
    reasons = []

    abs_delta = abs(delta)
    if option_type == "call" and delta > 0.3:
        scores.append(1)
        reasons.append(f"delta {delta:.3f} above 0.3 threshold")
    elif option_type == "put" and delta < -0.3:
        scores.append(1)
        reasons.append(f"delta {delta:.3f} below -0.3 threshold")
    else:
        scores.append(-1)
        reasons.append(f"delta {delta:.3f} outside favorable range")

    days_left = t * 365
    if 30 <= days_left <= 60:
        scores.append(1)
        reasons.append(f"{days_left:.0f} days to expiry in sweet spot")
    elif days_left < 30:
        scores.append(-1)
        reasons.append(f"{days_left:.0f} days to expiry too short")
    else:
        scores.append(0)
        reasons.append(f"{days_left:.0f} days to expiry outside 30-60 range")

    theta_per_delta = abs(theta / delta) if abs_delta > 0.01 else float("inf")
    if theta_per_delta < 0.02:
        scores.append(1)
        reasons.append(f"favorable theta/delta ratio {theta_per_delta:.4f}")
    elif theta_per_delta < 0.05:
        scores.append(0)
        reasons.append(f"acceptable theta/delta ratio {theta_per_delta:.4f}")
    else:
        scores.append(-1)
        reasons.append(f"poor theta/delta ratio {theta_per_delta:.4f}")

    if vega > 0.10:
        scores.append(1)
        reasons.append(f"vega {vega:.3f} shows vol expansion opportunity")
    elif vega > 0.05:
        scores.append(0)
        reasons.append(f"vega {vega:.3f} moderate vol sensitivity")
    else:
        scores.append(-1)
        reasons.append(f"vega {vega:.3f} low vol sensitivity")

    trend = technicals.get("trend", "neutral")
    if option_type == "call" and trend == "bullish":
        scores.append(1)
        reasons.append("bullish trend confirms call direction")
    elif option_type == "put" and trend == "bearish":
        scores.append(1)
        reasons.append("bearish trend confirms put direction")
    elif trend == "neutral":
        scores.append(0)
        reasons.append("neutral trend, no directional confirmation")
    else:
        scores.append(-1)
        reasons.append(f"{trend} trend opposes option direction")

    tech_signals = technicals.get("signals", [])
    if option_type == "call" and "macd_bullish_cross" in tech_signals:
        scores.append(1)
        reasons.append("macd bullish crossover supports entry")
    elif option_type == "put" and "macd_bearish_cross" in tech_signals:
        scores.append(1)
        reasons.append("macd bearish crossover supports entry")

    if option_type == "call" and "rsi_oversold" in tech_signals:
        scores.append(1)
        reasons.append("rsi oversold suggests bounce opportunity")
    elif option_type == "put" and "rsi_overbought" in tech_signals:
        scores.append(1)
        reasons.append("rsi overbought suggests pullback opportunity")

    total_score = sum(scores)
    max_score = len(scores)

    if total_score >= max_score * 0.6:
        signal = "buy"
    elif total_score <= -max_score * 0.3:
        signal = "sell"
    else:
        signal = "hold"

    return {
        "signal": signal,
        "score": total_score,
        "max_score": max_score,
        "greeks": greeks,
        "reasons": reasons,
    }


def run_strategy(ticker, option_type, strike, expiry_str, rate=0.05):
    """run the lambda options strategy for a given contract"""
    ohlc_data = fetch_ohlc(ticker, period="6mo", interval="1d")
    if not ohlc_data:
        print(f"error: could not fetch price data for {ticker}", file=sys.stderr)
        return None

    spot = ohlc_data[-1]["close"]
    closes = [r["close"] for r in ohlc_data]

    vol = historical_volatility(closes)
    if vol is None:
        print("error: insufficient data for volatility calculation", file=sys.stderr)
        return None

    days = days_to_expiry(expiry_str)
    t = days / 365.0

    technicals = check_technical_signals(ohlc_data)
    evaluation = evaluate_option(spot, strike, rate, vol, t, option_type, technicals)

    return {
        "ticker": ticker,
        "option_type": option_type,
        "strike": strike,
        "expiry": expiry_str,
        "spot": spot,
        "hist_vol": round(vol, 4),
        "days_to_expiry": days,
        "technicals": technicals,
        "evaluation": evaluation,
    }


def format_report(result):
    """format strategy result as readable text"""
    if not result:
        return "no result to display"

    lines = []
    lines.append(f"{'=' * 60}")
    lines.append(f"lambda strategy: {result['ticker']} {result['option_type'].upper()}")
    lines.append(f"{'=' * 60}")
    lines.append(f"underlying:      {result['spot']:.2f}")
    lines.append(f"strike:          {result['strike']:.2f}")
    lines.append(f"expiry:          {result['expiry']} ({result['days_to_expiry']} days)")
    lines.append(f"hist volatility: {result['hist_vol']:.2%}")

    tech = result["technicals"]
    lines.append(f"\ntrend:           {tech['trend']}")
    lines.append(f"momentum:        {tech['momentum']}")
    if tech["signals"]:
        lines.append(f"signals:         {', '.join(tech['signals'])}")

    ev = result["evaluation"]
    greeks = ev.get("greeks", {})
    lines.append(f"\ngreeks:")
    lines.append(f"  price:  {greeks.get('price', 0):.4f}")
    lines.append(f"  delta:  {greeks.get('delta', 0):.4f}")
    lines.append(f"  gamma:  {greeks.get('gamma', 0):.4f}")
    lines.append(f"  theta:  {greeks.get('theta', 0):.4f}")
    lines.append(f"  vega:   {greeks.get('vega', 0):.4f}")

    signal = ev.get("signal", "unknown")
    score = ev.get("score", 0)
    max_score = ev.get("max_score", 1)

    signal_display = signal.upper()
    lines.append(f"\nsignal:          {signal_display} (score: {score}/{max_score})")

    lines.append(f"\nanalysis:")
    for reason in ev.get("reasons", []):
        lines.append(f"  - {reason}")

    lines.append(f"{'=' * 60}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("usage: python lambda.py <ticker> <call|put> <strike> <expiry>")
        print("  example: python lambda.py AAPL call 150 2021-04-16")
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

    result = run_strategy(ticker, option_type, strike, expiry)
    print(format_report(result))
