#!/usr/bin/env python3
"""mooop: combined investing and options strategy for high conviction plays

combines vested (reverse-engineered buy patterns), momentum/volume analysis,
and squeeze detection with options greeks evaluation. scores each dimension
separately, produces composite signal, suggests both share entry and options
contracts.
"""

import importlib
import sys
from datetime import datetime, timedelta

from ohlc import fetch_ohlc
from indicators import (
    sma, ema, rsi, macd, bollinger_bands, atr,
    volume_sma,
)
from vested import (
    check_current_match, analyze as vested_analyze,
)

_lambda = importlib.import_module("lambda")


def score_vested(ticker, period="1y"):
    """score based on vested pattern match against big-winner bottoms.

    returns dict with match_pct, matched indicators, and raw scores.
    uses NVDA 5y as default reference pattern.
    """
    ref = vested_analyze("NVDA", "5y")
    if not ref or not ref.get("pattern"):
        return {"score": 0, "match_pct": 0, "detail": "no reference pattern"}

    match = check_current_match(ticker, ref["pattern"], period)
    if not match:
        return {"score": 0, "match_pct": 0, "detail": "insufficient data"}

    pct = match["match_pct"]
    normalized = min(pct / 100.0, 1.0)

    return {
        "score": round(normalized, 3),
        "match_pct": pct,
        "matched": match.get("matched", {}),
        "current_scores": match.get("current_scores", {}),
        "price": match.get("price", 0),
        "date": match.get("date", ""),
    }


def score_momentum(ticker, period="1y"):
    """score momentum, volume, and options-readiness.

    checks trend alignment, volume confirmation, rsi positioning,
    macd direction, and bollinger band position.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return {"score": 0, "detail": "insufficient data"}

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]

    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, histogram = macd(closes)
    bb_mid, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    vol_sma_vals = volume_sma(volumes, 20)
    atr_vals = atr(highs, lows, closes, 14)  # noqa: F841

    idx = len(closes) - 1
    points = 0
    max_points = 0
    details = []

    if sma_20[idx] is not None and sma_50[idx] is not None:
        max_points += 2
        if sma_20[idx] > sma_50[idx]:
            points += 1
            details.append("sma20 > sma50 (uptrend)")
        if sma_200[idx] is not None and closes[idx] > sma_200[idx]:
            points += 1
            details.append("price above sma200")

    if rsi_vals[idx] is not None:
        max_points += 1
        if 40 < rsi_vals[idx] < 70:
            points += 1
            details.append(f"rsi {rsi_vals[idx]:.1f} in momentum zone")

    if histogram[idx] is not None and histogram[idx - 1] is not None:
        max_points += 1
        if histogram[idx] > histogram[idx - 1]:
            points += 1
            details.append("macd histogram rising")

    if vol_sma_vals[idx] is not None and vol_sma_vals[idx] > 0:
        max_points += 1
        vol_ratio = volumes[idx] / vol_sma_vals[idx]
        if vol_ratio > 1.2:
            points += 1
            details.append(f"volume {vol_ratio:.1f}x average")

    if bb_lower[idx] is not None and bb_upper[idx] is not None:
        max_points += 1
        bb_width = (bb_upper[idx] - bb_lower[idx]) / bb_mid[idx]  # noqa: F841
        bb_pos = (closes[idx] - bb_lower[idx]) / (bb_upper[idx] - bb_lower[idx])
        if 0.3 < bb_pos < 0.8:
            points += 1
            details.append(f"bb position {bb_pos:.2f} mid-range")

    normalized = points / max_points if max_points > 0 else 0
    hvol = _lambda.historical_volatility(closes)

    return {
        "score": round(normalized, 3),
        "points": points,
        "max_points": max_points,
        "details": details,
        "hist_vol": round(hvol, 4) if hvol else None,
        "rsi": rsi_vals[idx],
        "trend": "bullish" if sma_20[idx] and sma_50[idx] and sma_20[idx] > sma_50[idx] else "bearish",
    }


def score_squeeze(ticker, period="1y"):
    """score squeeze potential: tight bollinger bands with volume compression.

    a squeeze occurs when volatility contracts (bb narrows), volume dries up,
    and the stock coils before a directional move.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return {"score": 0, "detail": "insufficient data"}

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]

    bb_mid, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    atr_vals = atr(highs, lows, closes, 14)  # noqa: F841
    vol_sma_vals = volume_sma(volumes, 20)
    kc_mult = 1.5

    idx = len(closes) - 1
    points = 0
    max_points = 0
    details = []

    if bb_upper[idx] is not None and bb_lower[idx] is not None and bb_mid[idx] > 0:
        max_points += 2
        bb_width = (bb_upper[idx] - bb_lower[idx]) / bb_mid[idx]
        bb_widths = []
        for i in range(max(0, idx - 60), idx + 1):
            if bb_upper[i] is not None and bb_lower[i] is not None and bb_mid[i] > 0:
                bb_widths.append((bb_upper[i] - bb_lower[i]) / bb_mid[i])
        if bb_widths:
            avg_width = sum(bb_widths) / len(bb_widths)
            if bb_width < avg_width * 0.7:
                points += 2
                details.append(f"bb squeeze: width {bb_width:.4f} vs avg {avg_width:.4f}")
            elif bb_width < avg_width * 0.85:
                points += 1
                details.append(f"bb narrowing: width {bb_width:.4f} vs avg {avg_width:.4f}")

    if atr_vals[idx] is not None and closes[idx] > 0:
        max_points += 1
        atr_pct = atr_vals[idx] / closes[idx]
        atr_pcts = []
        for i in range(max(0, idx - 60), idx + 1):
            if atr_vals[i] is not None and closes[i] > 0:
                atr_pcts.append(atr_vals[i] / closes[i])
        if atr_pcts:
            avg_atr_pct = sum(atr_pcts) / len(atr_pcts)
            if atr_pct < avg_atr_pct * 0.7:
                points += 1
                details.append(f"atr compressing: {atr_pct:.4f} vs avg {avg_atr_pct:.4f}")

    if vol_sma_vals[idx] is not None and vol_sma_vals[idx] > 0:
        max_points += 1
        recent_avg_vol = sum(volumes[idx - 5:idx + 1]) / 6
        long_avg_vol = vol_sma_vals[idx]
        if recent_avg_vol < long_avg_vol * 0.7:
            points += 1
            details.append(f"volume drying up: {recent_avg_vol:.0f} vs avg {long_avg_vol:.0f}")

    if bb_upper[idx] is not None and atr_vals[idx] is not None:
        max_points += 1
        ema_20 = ema(closes, 20)
        if ema_20[idx] is not None:
            kc_upper = ema_20[idx] + kc_mult * atr_vals[idx]
            kc_lower = ema_20[idx] - kc_mult * atr_vals[idx]
            if bb_lower[idx] > kc_lower and bb_upper[idx] < kc_upper:
                points += 1
                details.append("bb inside keltner channel (squeeze on)")

    normalized = points / max_points if max_points > 0 else 0
    return {
        "score": round(normalized, 3),
        "points": points,
        "max_points": max_points,
        "details": details,
    }


def suggest_options(ticker, spot, hist_vol, momentum_result):
    """suggest options contracts based on analysis.

    picks strike near the money, expiry 30-60 days out, evaluates greeks.
    """
    if hist_vol is None or spot <= 0:
        return None

    trend = momentum_result.get("trend", "neutral")
    option_type = "call" if trend == "bullish" else "put"

    if option_type == "call":
        strike = round(spot * 1.05, 0)
    else:
        strike = round(spot * 0.95, 0)

    expiry_date = datetime.now() + timedelta(days=45)
    expiry_str = expiry_date.strftime("%Y-%m-%d")

    days = _lambda.days_to_expiry(expiry_str)
    t = days / 365.0
    rate = 0.05

    greeks = _lambda.calc_greeks(spot, strike, rate, hist_vol, t, option_type)

    rows = fetch_ohlc(ticker, period="6mo")
    if rows:
        technicals = _lambda.check_technical_signals(rows)
        evaluation = _lambda.evaluate_option(
            spot, strike, rate, hist_vol, t, option_type, technicals
        )
    else:
        evaluation = {"signal": "unknown", "score": 0, "max_score": 1, "reasons": []}

    return {
        "type": option_type,
        "strike": strike,
        "expiry": expiry_str,
        "days_to_expiry": days,
        "greeks": greeks,
        "evaluation": evaluation,
    }


def composite_score(vested_result, momentum_result, squeeze_result):
    """combine three dimension scores into weighted composite.

    vested pattern:  40% (long term conviction)
    momentum:        35% (current conditions)
    squeeze:         25% (bonus catalyst)
    """
    v = vested_result.get("score", 0) * 0.40
    m = momentum_result.get("score", 0) * 0.35
    s = squeeze_result.get("score", 0) * 0.25
    total = v + m + s

    if total >= 0.7:
        signal = "strong_buy"
    elif total >= 0.5:
        signal = "buy"
    elif total >= 0.3:
        signal = "watch"
    else:
        signal = "pass"

    return {
        "composite": round(total, 3),
        "signal": signal,
        "vested_weighted": round(v, 3),
        "momentum_weighted": round(m, 3),
        "squeeze_weighted": round(s, 3),
    }


def analyze_ticker(ticker):
    """run full mooop analysis on a single ticker.

    returns all dimension scores, composite signal, share entry guidance,
    and options contract suggestion.
    """
    print(f"  analyzing {ticker}...")

    vested_result = score_vested(ticker)
    momentum_result = score_momentum(ticker)
    squeeze_result = score_squeeze(ticker)
    comp = composite_score(vested_result, momentum_result, squeeze_result)

    spot = vested_result.get("price", 0)
    if spot <= 0:
        rows = fetch_ohlc(ticker, "1y")
        if rows:
            spot = rows[-1]["close"]

    hvol = momentum_result.get("hist_vol")
    options = suggest_options(ticker, spot, hvol, momentum_result)

    share_guidance = "hold"
    if comp["signal"] in ("strong_buy", "buy"):
        share_guidance = "accumulate"
    elif comp["signal"] == "watch":
        share_guidance = "small position ok, set alerts"

    return {
        "ticker": ticker,
        "spot": spot,
        "composite": comp,
        "vested": vested_result,
        "momentum": momentum_result,
        "squeeze": squeeze_result,
        "options": options,
        "share_guidance": share_guidance,
    }


def print_report(result):
    """print formatted analysis report for a single ticker."""
    comp = result["composite"]
    v = result["vested"]
    m = result["momentum"]
    s = result["squeeze"]
    opt = result["options"]

    print(f"\n{result['ticker']}  ${result['spot']:.2f}")
    print(f"  signal: {comp['signal']}  composite: {comp['composite']:.3f}")
    print(f"  vested:   {v['score']:.3f} (x0.40 = {comp['vested_weighted']:.3f})"
          f"  match: {v.get('match_pct', 0):.1f}%")
    print(f"  momentum: {m['score']:.3f} (x0.35 = {comp['momentum_weighted']:.3f})"
          f"  trend: {m.get('trend', '?')}  rsi: {m.get('rsi', 0):.1f}")
    print(f"  squeeze:  {s['score']:.3f} (x0.25 = {comp['squeeze_weighted']:.3f})")

    if m.get("details"):
        print("  momentum detail:")
        for d in m["details"]:
            print(f"    {d}")

    if s.get("details"):
        print("  squeeze detail:")
        for d in s["details"]:
            print(f"    {d}")

    if v.get("matched"):
        matched_names = ", ".join(v["matched"].keys())
        print(f"  vested matches: {matched_names}")

    print(f"  shares: {result['share_guidance']}")

    if opt:
        ev = opt["evaluation"]
        g = opt["greeks"]
        print(f"  options: {opt['type']} ${opt['strike']:.0f} exp {opt['expiry']}"
              f" ({opt['days_to_expiry']}d)")
        print(f"    price: ${g['price']:.2f}  delta: {g['delta']:.3f}"
              f"  theta: {g['theta']:.4f}  vega: {g['vega']:.3f}")
        print(f"    signal: {ev.get('signal', '?')}"
              f"  score: {ev.get('score', 0)}/{ev.get('max_score', 0)}")


def portfolio_heat(results):
    """summarize mooop results by signal strength level.

    results: list of analyze_ticker result dicts
    returns dict with counts and tickers grouped by signal level
    """
    heat = {
        "strong_buy": [],
        "buy": [],
        "watch": [],
        "pass": [],
    }
    for r in results:
        signal = r["composite"]["signal"]
        entry = {"ticker": r["ticker"], "composite": r["composite"]["composite"]}
        if signal in heat:
            heat[signal].append(entry)
        else:
            heat["pass"].append(entry)
    summary = {}
    for level, entries in heat.items():
        summary[level] = {"count": len(entries), "tickers": entries}
    return summary


def main():
    if len(sys.argv) < 2:
        print("usage: python mooop.py TICKER [TICKER ...]")
        print("  example: python mooop.py NVDA AAPL MSFT")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    print(f"mooop analysis: {', '.join(tickers)}")

    results = []
    for ticker in tickers:
        result = analyze_ticker(ticker)
        results.append(result)

    results.sort(key=lambda r: -r["composite"]["composite"])

    for result in results:
        print_report(result)

    print("\nranking:")
    for i, r in enumerate(results, 1):
        c = r["composite"]
        print(f"  {i}. {r['ticker']:<6} {c['signal']:<12} {c['composite']:.3f}"
              f"  shares: {r['share_guidance']}")


if __name__ == "__main__":
    main()
