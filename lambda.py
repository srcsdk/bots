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

    print(f"lambda: {ticker} {option_type} ${strike} exp {expiry}")
    greeks = calc_greeks(100, strike, 0.05, 0.3, 30 / 365.0, option_type)
    for k, v in greeks.items():
        print(f"  {k}: {v}")
