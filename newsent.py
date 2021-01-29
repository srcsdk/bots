#!/usr/bin/env python3
"""news sentiment signal generator.

lexicon-based sentiment scorer for financial context. scores sentiment
from price action patterns that correlate with news-driven moves.
detects divergence between inferred sentiment and price direction.
"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, sma, obv

BULLISH_PATTERNS = {
    "gap_up_strong_close": 2,
    "high_volume_breakout": 3,
    "oversold_reversal": 2,
    "volume_surge_up": 1,
    "consecutive_higher_closes": 1,
}

BEARISH_PATTERNS = {
    "gap_down_weak_close": -2,
    "high_volume_breakdown": -3,
    "overbought_reversal": -2,
    "volume_surge_down": -1,
    "consecutive_lower_closes": -1,
}


def detect_patterns(row, prev_row, rsi_val, vol_avg, obv_val, obv_prev):
    """detect bullish/bearish patterns from price action as sentiment proxy"""
    scores = []
    gap_pct = (row["open"] - prev_row["close"]) / prev_row["close"] * 100

    if gap_pct > 1 and row["close"] > row["open"]:
        scores.append(("gap_up_strong_close", 2))
    elif gap_pct < -1 and row["close"] < row["open"]:
        scores.append(("gap_down_weak_close", -2))

    if vol_avg and vol_avg > 0 and row["volume"] > vol_avg * 2:
        if row["close"] > prev_row["close"]:
            scores.append(("volume_surge_up", 1))
        else:
            scores.append(("volume_surge_down", -1))

    if rsi_val is not None:
        if rsi_val < 25 and row["close"] > row["open"]:
            scores.append(("oversold_reversal", 2))
        elif rsi_val > 75 and row["close"] < row["open"]:
            scores.append(("overbought_reversal", -2))

    if obv_val is not None and obv_prev is not None:
        if obv_val > obv_prev and row["close"] < prev_row["close"]:
            scores.append(("obv_divergence_bull", 1))
        elif obv_val < obv_prev and row["close"] > prev_row["close"]:
            scores.append(("obv_divergence_bear", -1))

    return scores


def rolling_sentiment(scores, window=5):
    """calculate rolling average sentiment over a window"""
    result = [None] * (window - 1)
    for i in range(window - 1, len(scores)):
        window_scores = scores[i - window + 1:i + 1]
        result.append(round(sum(window_scores) / len(window_scores), 2))
    return result


def analyze(ticker, period="1y"):
    """analyze sentiment signals derived from price/volume patterns.

    returns daily sentiment scores, rolling averages, and divergence signals.
    """
    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 30:
        return None

    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]

    rsi_vals = rsi(closes, 14)
    vol_sma = sma(volumes, 20)
    obv_vals = obv(closes, volumes)

    daily_scores = [0]
    daily_details = [{"date": rows[0]["date"], "patterns": [], "score": 0}]

    for i in range(1, len(rows)):
        patterns = detect_patterns(
            rows[i], rows[i - 1], rsi_vals[i],
            vol_sma[i], obv_vals[i], obv_vals[i - 1]
        )
        score = sum(p[1] for p in patterns)
        daily_scores.append(score)
        daily_details.append({
            "date": rows[i]["date"],
            "patterns": [p[0] for p in patterns],
            "score": score,
        })

    rolling_5 = rolling_sentiment(daily_scores, 5)
    rolling_20 = rolling_sentiment(daily_scores, 20)

    price_sma = sma(closes, 20)

    divergences = []
    for i in range(20, len(rows)):
        if rolling_20[i] is None or price_sma[i] is None:
            continue
        price_trend = closes[i] - price_sma[i]
        sent_trend = rolling_20[i]

        if price_trend > 0 and sent_trend < -0.5:
            divergences.append({
                "date": rows[i]["date"],
                "type": "bearish_divergence",
                "price": closes[i],
                "sentiment": sent_trend,
            })
        elif price_trend < 0 and sent_trend > 0.5:
            divergences.append({
                "date": rows[i]["date"],
                "type": "bullish_divergence",
                "price": closes[i],
                "sentiment": sent_trend,
            })

    latest_sent = rolling_5[-1] if rolling_5[-1] is not None else 0
    if latest_sent > 1:
        overall = "bullish"
    elif latest_sent < -1:
        overall = "bearish"
    else:
        overall = "neutral"

    return {
        "ticker": ticker,
        "overall_sentiment": overall,
        "latest_score": latest_sent,
        "daily": daily_details[-10:],
        "divergences": divergences[-5:],
        "total_divergences": len(divergences),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python newsent.py <ticker> [period]")
        print("  generates sentiment signals from price/volume patterns")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"

    print(f"sentiment analysis: {ticker} ({period})")
    result = analyze(ticker, period)

    if not result:
        print("insufficient data")
        sys.exit(1)

    print(f"\n  overall: {result['overall_sentiment']} (score: {result['latest_score']:+.2f})")

    print("\nrecent daily sentiment:")
    for d in result["daily"]:
        patterns = ", ".join(d["patterns"]) if d["patterns"] else "none"
        print(f"  {d['date']}  score={d['score']:+d}  [{patterns}]")

    if result["divergences"]:
        print(f"\nrecent divergences ({result['total_divergences']} total):")
        for div in result["divergences"]:
            print(f"  {div['date']}  {div['type']}  ${div['price']:.2f}  sent={div['sentiment']:+.2f}")
    else:
        print("\nno divergences detected")
