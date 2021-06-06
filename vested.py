#!/usr/bin/env python3
"""vested: reverse engineer technical indicators that flagged bottoms in big winners"""

import sys
from ohlc import fetch_ohlc
from indicators import (
    sma, ema, rsi, macd, bollinger_bands, atr,
    fifty_two_week_low, fifty_two_week_high, volume_sma, gap_percent,
)


def extract_prices(rows):
    """pull price and volume arrays from ohlc rows"""
    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    volumes = [r["volume"] for r in rows]
    return closes, opens, highs, lows, volumes


def compute_indicators(closes, opens, highs, lows, volumes):
    """compute all indicators, return dict of named series"""
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    bb_mid, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    atr_vals = atr(highs, lows, closes, 14)
    low_52 = fifty_two_week_low(closes)
    high_52 = fifty_two_week_high(closes)
    vol_sma = volume_sma(volumes, 20)
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)
    ema_20 = ema(closes, 20)
    gaps = gap_percent(opens, closes)

    return {
        "rsi": rsi_vals,
        "macd_line": macd_line,
        "macd_signal": signal_line,
        "macd_hist": hist,
        "bb_mid": bb_mid,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "atr": atr_vals,
        "low_52": low_52,
        "high_52": high_52,
        "vol_sma": vol_sma,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "ema_20": ema_20,
        "gaps": gaps,
    }


def find_optimal_buy(rows):
    """find the best buy point: lowest price before the largest subsequent gain"""
    if len(rows) < 60:
        return None

    closes = [r["close"] for r in rows]
    best_idx = None
    best_gain = 0

    for i in range(len(closes) - 20):
        future_max = max(closes[i + 1:])
        gain = (future_max - closes[i]) / closes[i]
        if gain > best_gain:
            best_gain = gain
            best_idx = i

    if best_idx is None:
        return None

    future_max = max(closes[best_idx + 1:])
    return {
        "index": best_idx,
        "date": rows[best_idx]["date"],
        "price": closes[best_idx],
        "future_high": round(future_max, 2),
        "gain_pct": round(best_gain * 100, 1),
    }


def score_indicators_at(idx, closes, opens, highs, lows, volumes):
    """score each indicator's contribution to identifying a bottom at idx"""
    ind = compute_indicators(closes, opens, highs, lows, volumes)
    scores = {}

    if ind["rsi"][idx] is not None:
        rsi_val = ind["rsi"][idx]
        if rsi_val < 30:
            scores["rsi_oversold"] = round((30 - rsi_val) / 30, 2)
        elif rsi_val < 40:
            scores["rsi_oversold"] = round((40 - rsi_val) / 40 * 0.5, 2)
        else:
            scores["rsi_oversold"] = 0

    if ind["bb_lower"][idx] is not None:
        bb_dist = (closes[idx] - ind["bb_lower"][idx]) / closes[idx]
        if bb_dist <= 0:
            scores["below_bb_lower"] = round(min(abs(bb_dist) * 10, 1.0), 2)
        elif bb_dist < 0.02:
            scores["below_bb_lower"] = round(0.3 * (1 - bb_dist / 0.02), 2)
        else:
            scores["below_bb_lower"] = 0

    if ind["low_52"][idx] is not None:
        pct_above_low = (closes[idx] - ind["low_52"][idx]) / ind["low_52"][idx]
        if pct_above_low < 0.05:
            scores["near_52wk_low"] = round(1.0 - pct_above_low * 20, 2)
        else:
            scores["near_52wk_low"] = 0

    if ind["high_52"][idx] is not None and ind["high_52"][idx] > 0:
        drawdown = (ind["high_52"][idx] - closes[idx]) / ind["high_52"][idx]
        if drawdown > 0.2:
            scores["deep_drawdown"] = round(min(drawdown, 1.0), 2)
        else:
            scores["deep_drawdown"] = 0

    if (ind["macd_hist"][idx] is not None
            and idx > 0 and ind["macd_hist"][idx - 1] is not None):
        if ind["macd_hist"][idx] > ind["macd_hist"][idx - 1] < 0:
            scores["macd_turning"] = 0.8
        elif ind["macd_hist"][idx] < 0:
            scores["macd_turning"] = 0.3
        else:
            scores["macd_turning"] = 0

    if (ind["macd_line"][idx] is not None
            and ind["macd_signal"][idx] is not None
            and idx > 0
            and ind["macd_line"][idx - 1] is not None
            and ind["macd_signal"][idx - 1] is not None):
        crossed = (ind["macd_line"][idx] > ind["macd_signal"][idx]
                   and ind["macd_line"][idx - 1] <= ind["macd_signal"][idx - 1])
        scores["macd_cross_up"] = 1.0 if crossed else 0

    if ind["vol_sma"][idx] is not None and ind["vol_sma"][idx] > 0:
        vol_ratio = volumes[idx] / ind["vol_sma"][idx]
        if vol_ratio > 2.0:
            scores["volume_spike"] = round(min((vol_ratio - 1) / 3, 1.0), 2)
        else:
            scores["volume_spike"] = 0

    if ind["sma_50"][idx] is not None and ind["sma_200"][idx] is not None:
        if closes[idx] < ind["sma_200"][idx]:
            scores["below_sma200"] = round(
                min((ind["sma_200"][idx] - closes[idx]) / closes[idx] * 5, 1.0), 2
            )
        else:
            scores["below_sma200"] = 0

    if ind["atr"][idx] is not None and closes[idx] > 0:
        atr_pct = ind["atr"][idx] / closes[idx]
        if atr_pct > 0.03:
            scores["high_volatility"] = round(min(atr_pct * 10, 1.0), 2)
        else:
            scores["high_volatility"] = 0

    lookback = min(5, idx)
    gap_score = 0
    for j in range(idx - lookback, idx):
        if ind["gaps"][j] is not None and ind["gaps"][j] < -2:
            gap_score = max(gap_score, min(abs(ind["gaps"][j]) / 10, 1.0))
    scores["recent_gap_down"] = round(gap_score, 2)

    return scores


def build_pattern(scores):
    """build a pattern from the strongest indicators at the bottom"""
    threshold = 0.3
    pattern = {}
    for name, score in sorted(scores.items(), key=lambda x: -x[1]):
        if score >= threshold:
            pattern[name] = score
    return pattern


def analyze(ticker, period="5y"):
    """analyze a ticker's history and find the optimal buy pattern"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        print(f"insufficient data for {ticker}", file=sys.stderr)
        return None

    buy = find_optimal_buy(rows)
    if not buy:
        print(f"no optimal buy point found for {ticker}", file=sys.stderr)
        return None

    closes, opens, highs, lows, volumes = extract_prices(rows)
    scores = score_indicators_at(buy["index"], closes, opens, highs, lows, volumes)
    pattern = build_pattern(scores)

    total = sum(scores.values())
    active_count = sum(1 for v in scores.values() if v > 0)

    return {
        "ticker": ticker,
        "buy": buy,
        "scores": scores,
        "pattern": pattern,
        "total_score": round(total, 2),
        "active_indicators": active_count,
    }


def check_current_match(ticker, pattern, period="1y"):
    """check if a ticker currently matches a reverse-engineered pattern"""
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        return None

    closes, opens, highs, lows, volumes = extract_prices(rows)
    idx = len(closes) - 1
    scores = score_indicators_at(idx, closes, opens, highs, lows, volumes)

    match_total = 0
    pattern_total = 0
    matches = {}
    for name, required in pattern.items():
        pattern_total += required
        actual = scores.get(name, 0)
        if actual >= required * 0.5:
            match_total += min(actual, required)
            matches[name] = actual

    match_pct = (match_total / pattern_total * 100) if pattern_total > 0 else 0

    return {
        "ticker": ticker,
        "date": rows[-1]["date"],
        "price": closes[-1],
        "match_pct": round(match_pct, 1),
        "matched": matches,
        "current_scores": scores,
    }


def scan(tickers, pattern, period="1y"):
    """scan tickers against a reverse-engineered pattern"""
    results = []
    for ticker in tickers:
        result = check_current_match(ticker, pattern, period)
        if result:
            results.append(result)
    results.sort(key=lambda x: -x["match_pct"])
    return results


def print_analysis(result):
    """print analysis results"""
    buy = result["buy"]
    print(f"\n{result['ticker']} optimal buy point")
    print(f"  date:   {buy['date']}")
    print(f"  price:  ${buy['price']:.2f}")
    print(f"  high:   ${buy['future_high']:.2f}")
    print(f"  gain:   {buy['gain_pct']:.1f}%")

    print(f"\nindicator scores at buy point ({result['active_indicators']} active):")
    for name, score in sorted(result["scores"].items(), key=lambda x: -x[1]):
        bar = "#" * int(score * 20)
        marker = " *" if name in result["pattern"] else ""
        print(f"  {name:<20s} {score:.2f} {bar}{marker}")

    print(f"\ntotal score: {result['total_score']:.2f}")
    print("pattern (* = score >= 0.3):")
    for name, score in sorted(result["pattern"].items(), key=lambda x: -x[1]):
        print(f"  {name}: {score:.2f}")


def print_scan(results):
    """print scan results"""
    if not results:
        print("no matches found")
        return

    print(f"\n{'ticker':<8} {'price':>8} {'match':>7} {'date':<12} matched indicators")
    for r in results:
        matched_names = ", ".join(r["matched"].keys())
        print(f"  {r['ticker']:<6} ${r['price']:>7.2f} {r['match_pct']:>5.1f}% "
              f"{r['date']:<12} {matched_names}")


def add_fundamental_stub(ticker):
    """return a dict with placeholder fundamental metrics for future api integration"""
    return {
        "ticker": ticker,
        "pe_ratio": None,
        "forward_pe": None,
        "revenue_growth": None,
        "earnings_growth": None,
        "debt_to_equity": None,
        "profit_margin": None,
        "roe": None,
        "free_cash_flow": None,
        "dividend_yield": None,
        "market_cap": None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python vested.py <ticker>           (analyze)")
        print("       python vested.py --scan T1 T2 T3    (scan current)")
        sys.exit(1)

    if sys.argv[1] == "--scan":
        if len(sys.argv) < 3:
            print("usage: python vested.py --scan <ticker1> <ticker2> ...")
            sys.exit(1)

        scan_tickers = [t.upper() for t in sys.argv[2:]]
        reference = scan_tickers[0]
        print(f"analyzing {reference} to build pattern...")
        ref_result = analyze(reference)
        if not ref_result:
            sys.exit(1)

        print_analysis(ref_result)
        print(f"\nscanning {len(scan_tickers)} tickers against {reference} pattern...")
        scan_results = scan(scan_tickers, ref_result["pattern"])
        print_scan(scan_results)
    else:
        ticker = sys.argv[1].upper()
        period = sys.argv[2] if len(sys.argv) > 2 else "5y"
        print(f"vested analysis: {ticker} ({period})")
        result = analyze(ticker, period)
        if result:
            print_analysis(result)
