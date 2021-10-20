#!/usr/bin/env python3
"""mooon: moon squeeze detection with lambda options contracts

When moon detects a high-probability squeeze setup, evaluates options contracts
via lambda to find optimal strike/expiry for maximum leverage. Generates
specific contract alerts with greeks.

usage: python mooon.py AMC 2021-04-16
"""

import importlib
import sys
from datetime import datetime

from moon import analyze_moon
from ohlc import fetch_ohlc

_lambda = importlib.import_module("lambda")


DEFAULT_SQUEEZE_THRESHOLD = 40
STRIKE_OFFSETS_CALL = [0.95, 1.00, 1.05, 1.10, 1.15]
STRIKE_OFFSETS_PUT = [0.85, 0.90, 0.95, 1.00, 1.05]


def find_squeeze_candidates(tickers, threshold=DEFAULT_SQUEEZE_THRESHOLD):
    """run moon analysis and filter to candidates above the squeeze threshold.

    Returns only results where the combined squeeze+hype score meets
    or exceeds the threshold.
    """
    results = analyze_moon(tickers)
    candidates = [r for r in results if r["combined_score"] >= threshold]
    return candidates


def generate_strike_ladder(spot, option_type):
    """generate a list of strike prices around the current spot price.

    For calls, strikes range from slightly ITM to OTM.
    For puts, strikes range from OTM to slightly ITM.
    Rounds strikes to the nearest dollar.
    """
    if option_type == "call":
        offsets = STRIKE_OFFSETS_CALL
    else:
        offsets = STRIKE_OFFSETS_PUT

    strikes = []
    for mult in offsets:
        strike = round(spot * mult, 0)
        if strike > 0 and strike not in strikes:
            strikes.append(strike)

    return sorted(strikes)


def evaluate_contract(spot, strike, rate, vol, t, option_type):
    """evaluate a single options contract using lambda greeks.

    Returns greeks, moneyness classification, and a quality score
    that favors good delta, manageable theta, and sufficient vega
    for a squeeze play.
    """
    if t <= 0:
        return {"strike": strike, "score": 0, "greeks": {}, "moneyness": "expired",
                "reasons": ["contract has expired"]}

    greeks = _lambda.calc_greeks(spot, strike, rate, vol, t, option_type)
    delta = greeks["delta"]
    theta = greeks["theta"]
    vega = greeks["vega"]
    gamma = greeks["gamma"]
    price = greeks["price"]

    if option_type == "call":
        if spot > strike:
            moneyness = "itm"
        elif abs(spot - strike) / spot < 0.03:
            moneyness = "atm"
        else:
            moneyness = "otm"
    else:
        if spot < strike:
            moneyness = "itm"
        elif abs(spot - strike) / spot < 0.03:
            moneyness = "atm"
        else:
            moneyness = "otm"

    score = 0
    reasons = []

    abs_delta = abs(delta)
    if 0.35 <= abs_delta <= 0.65:
        score += 30
        reasons.append(f"delta {delta:.3f} ideal for leverage with directional exposure")
    elif 0.20 <= abs_delta < 0.35:
        score += 20
        reasons.append(f"delta {delta:.3f} moderate leverage, higher risk")
    elif abs_delta > 0.65:
        score += 15
        reasons.append(f"delta {delta:.3f} deep itm, less leverage")
    else:
        score += 5
        reasons.append(f"delta {delta:.3f} far otm, speculative")

    if vega > 0.15:
        score += 25
        reasons.append(f"vega {vega:.3f} benefits from vol expansion in squeeze")
    elif vega > 0.08:
        score += 15
        reasons.append(f"vega {vega:.3f} moderate vol sensitivity")
    else:
        score += 5
        reasons.append(f"vega {vega:.3f} limited vol benefit")

    if gamma > 0.02:
        score += 20
        reasons.append(f"gamma {gamma:.4f} strong acceleration on move")
    elif gamma > 0.01:
        score += 10
        reasons.append(f"gamma {gamma:.4f} moderate acceleration")
    else:
        score += 5
        reasons.append(f"gamma {gamma:.4f} slow delta change")

    if price > 0:
        theta_pct = abs(theta) / price
        if theta_pct < 0.01:
            score += 20
            reasons.append(f"theta {theta:.4f} minimal daily decay")
        elif theta_pct < 0.03:
            score += 10
            reasons.append(f"theta {theta:.4f} acceptable decay")
        else:
            score += 0
            reasons.append(f"theta {theta:.4f} significant daily decay")

    if moneyness == "atm":
        score += 5
        reasons.append("atm strike maximizes gamma and vega")

    return {
        "strike": strike,
        "score": min(100, score),
        "greeks": greeks,
        "moneyness": moneyness,
        "reasons": reasons,
    }


def find_optimal_contracts(spot, expiry_str, vol, rate=0.05):
    """evaluate call and put contracts across a strike ladder.

    For a squeeze play, evaluates calls (primary) and puts (hedge).
    Returns contracts sorted by score, with the best at the top.
    """
    days = _lambda.days_to_expiry(expiry_str)
    t = days / 365.0

    if t <= 0:
        return {"calls": [], "puts": [], "days_to_expiry": 0}

    call_strikes = generate_strike_ladder(spot, "call")
    put_strikes = generate_strike_ladder(spot, "put")

    calls = []
    for strike in call_strikes:
        result = evaluate_contract(spot, strike, rate, vol, t, "call")
        calls.append(result)

    puts = []
    for strike in put_strikes:
        result = evaluate_contract(spot, strike, rate, vol, t, "put")
        puts.append(result)

    calls.sort(key=lambda c: c["score"], reverse=True)
    puts.sort(key=lambda p: p["score"], reverse=True)

    return {"calls": calls, "puts": puts, "days_to_expiry": days}


def generate_alerts(candidate, contracts):
    """generate buy/sell alerts for a squeeze candidate with evaluated contracts.

    Creates specific actionable alerts based on the candidate's signal
    strength and the best available contracts.
    """
    alerts = []
    signal = candidate.get("signal", "hold")
    combined = candidate.get("combined_score", 0)
    ticker = candidate["ticker"]

    best_calls = contracts["calls"][:2]
    best_puts = contracts["puts"][:1]

    if signal == "entry" and combined >= 55:
        for c in best_calls:
            g = c["greeks"]
            alerts.append({
                "action": "buy",
                "ticker": ticker,
                "type": "call",
                "strike": c["strike"],
                "contract_score": c["score"],
                "price": g.get("price", 0),
                "delta": g.get("delta", 0),
                "gamma": g.get("gamma", 0),
                "theta": g.get("theta", 0),
                "vega": g.get("vega", 0),
                "moneyness": c["moneyness"],
                "reasoning": c["reasons"],
            })
        if best_puts:
            p = best_puts[0]
            g = p["greeks"]
            alerts.append({
                "action": "hedge",
                "ticker": ticker,
                "type": "put",
                "strike": p["strike"],
                "contract_score": p["score"],
                "price": g.get("price", 0),
                "delta": g.get("delta", 0),
                "gamma": g.get("gamma", 0),
                "theta": g.get("theta", 0),
                "vega": g.get("vega", 0),
                "moneyness": p["moneyness"],
                "reasoning": p["reasons"],
            })
    elif signal == "watch":
        if best_calls:
            c = best_calls[0]
            g = c["greeks"]
            alerts.append({
                "action": "watch",
                "ticker": ticker,
                "type": "call",
                "strike": c["strike"],
                "contract_score": c["score"],
                "price": g.get("price", 0),
                "delta": g.get("delta", 0),
                "gamma": g.get("gamma", 0),
                "theta": g.get("theta", 0),
                "vega": g.get("vega", 0),
                "moneyness": c["moneyness"],
                "reasoning": c["reasons"],
            })

    return alerts


def run_mooon(ticker, expiry_str, rate=0.05, threshold=DEFAULT_SQUEEZE_THRESHOLD):
    """run the full mooon analysis for a ticker and expiry.

    Steps:
    1. Run moon analysis for squeeze + hype detection
    2. If candidate scores above threshold, evaluate options via lambda
    3. Generate specific contract alerts with greeks
    """
    candidates = find_squeeze_candidates([ticker], threshold=threshold)

    if not candidates:
        print(f"\n{ticker} did not meet squeeze threshold ({threshold})")
        rows = fetch_ohlc(ticker, period="6mo")
        if not rows:
            return None
        spot = rows[-1]["close"]
        closes = [r["close"] for r in rows]
        vol = _lambda.historical_volatility(closes)
        if vol is None:
            return None
        contracts = find_optimal_contracts(spot, expiry_str, vol, rate)
        return {
            "ticker": ticker,
            "expiry": expiry_str,
            "spot": spot,
            "hist_vol": round(vol, 4),
            "candidate": None,
            "contracts": contracts,
            "alerts": [],
            "status": "below threshold",
        }

    candidate = candidates[0]
    spot = candidate["last_close"]

    rows = fetch_ohlc(ticker, period="6mo")
    if not rows:
        return None
    closes = [r["close"] for r in rows]
    vol = _lambda.historical_volatility(closes)
    if vol is None:
        vol = 0.50

    contracts = find_optimal_contracts(spot, expiry_str, vol, rate)
    alerts = generate_alerts(candidate, contracts)

    return {
        "ticker": ticker,
        "expiry": expiry_str,
        "spot": spot,
        "hist_vol": round(vol, 4),
        "candidate": candidate,
        "contracts": contracts,
        "alerts": alerts,
        "status": "active" if alerts else "monitoring",
    }


def format_report(result):
    """format the mooon analysis result as readable text."""
    if not result:
        return "no result to display"

    lines = []
    ticker = result["ticker"]
    lines.append(f"mooon analysis: {ticker}")
    lines.append(f"expiry: {result['expiry']}  |  spot: ${result['spot']:.2f}  |  "
                 f"hist vol: {result['hist_vol']:.2%}")
    lines.append(f"status: {result['status']}")
    lines.append("")

    candidate = result.get("candidate")
    if candidate:
        lines.append(f"[squeeze + hype]")
        lines.append(f"  squeeze: {candidate['squeeze_score']}/100  |  "
                     f"hype: {candidate['hype_score']}/100  |  "
                     f"combined: {candidate['combined_score']}/100")
        lines.append(f"  convergence: {candidate['convergence']}")
        lines.append(f"  moon signal: {candidate['signal'].upper()}")
        lines.append("")
    else:
        lines.append("[squeeze + hype]")
        lines.append(f"  {ticker} did not meet squeeze threshold")
        lines.append("")

    contracts = result.get("contracts", {})
    calls = contracts.get("calls", [])
    puts = contracts.get("puts", [])
    days = contracts.get("days_to_expiry", 0)

    if calls:
        lines.append(f"[call contracts] ({days} days to expiry)")
        for c in calls[:3]:
            g = c["greeks"]
            lines.append(f"  ${c['strike']:.0f} {c['moneyness']}  "
                         f"score={c['score']}/100  "
                         f"price={g.get('price', 0):.4f}  "
                         f"delta={g.get('delta', 0):.4f}  "
                         f"gamma={g.get('gamma', 0):.4f}  "
                         f"theta={g.get('theta', 0):.4f}  "
                         f"vega={g.get('vega', 0):.4f}")
        lines.append("")

    if puts:
        lines.append(f"[put contracts] ({days} days to expiry)")
        for p in puts[:2]:
            g = p["greeks"]
            lines.append(f"  ${p['strike']:.0f} {p['moneyness']}  "
                         f"score={p['score']}/100  "
                         f"price={g.get('price', 0):.4f}  "
                         f"delta={g.get('delta', 0):.4f}  "
                         f"gamma={g.get('gamma', 0):.4f}  "
                         f"theta={g.get('theta', 0):.4f}  "
                         f"vega={g.get('vega', 0):.4f}")
        lines.append("")

    alerts = result.get("alerts", [])
    if alerts:
        lines.append("[alerts]")
        for a in alerts:
            lines.append(f"  {a['action'].upper()} {ticker} {a['type'].upper()} "
                         f"${a['strike']:.0f}  "
                         f"(score={a['contract_score']}, {a['moneyness']})")
            lines.append(f"    price=${a['price']:.4f}  delta={a['delta']:.4f}  "
                         f"gamma={a['gamma']:.4f}  theta={a['theta']:.4f}  "
                         f"vega={a['vega']:.4f}")
            for reason in a["reasoning"][:3]:
                lines.append(f"    {reason}")
        lines.append("")
    else:
        lines.append("[alerts]")
        lines.append("  no actionable alerts at this time")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python mooon.py <ticker> <expiry>")
        print("  example: python mooon.py AMC 2021-04-16")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    expiry = sys.argv[2]

    try:
        datetime.strptime(expiry, "%Y-%m-%d")
    except ValueError:
        print("error: expiry must be YYYY-MM-DD format", file=sys.stderr)
        sys.exit(1)

    result = run_mooon(ticker, expiry)
    print("\n" + format_report(result))
