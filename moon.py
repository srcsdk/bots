#!/usr/bin/env python3
"""moon: combined short squeeze and social hype detection

Finds stocks where both technical squeeze signals from reta and social media
hype from hype align. Generates entry signals when both converge and exit
signals when divergence appears.

usage: python moon.py AMC GME BB
"""

import sys
import time

from reta import analyze_ticker, score_squeeze_potential, fetch_finviz_stats
from ohlc import fetch_ohlc
from hype import (
    scan_subreddit, merge_ticker_data, detect_hype_cycles,
    compute_hype_score, score_sentiment, SUBREDDITS,
)


def gather_hype_data(tickers, subreddits=None, limit=50):
    """scan social media for hype data on specified tickers.

    Returns a dict mapping each requested ticker to its hype metrics:
    mentions, sentiment, hype_score, and cycle status.
    """
    if subreddits is None:
        subreddits = SUBREDDITS[:4]

    combined = {}
    for sub in subreddits:
        data = scan_subreddit(sub, sort="hot", limit=limit)
        merge_ticker_data(combined, data)
        time.sleep(1)

    hype_cycles = detect_hype_cycles(combined)

    results = {}
    for ticker in tickers:
        t_upper = ticker.upper()
        if t_upper in combined:
            entry = combined[t_upper]
            mentions = entry["mentions"]
            sentiment = 0.0
            if entry["sentiment_count"] > 0:
                sentiment = entry["sentiment_sum"] / entry["sentiment_count"]
            source_count = len(entry["sources"])
            hype_score = compute_hype_score(mentions, sentiment, source_count)
            cycle = hype_cycles.get(t_upper)
            results[t_upper] = {
                "mentions": mentions,
                "sentiment": round(sentiment, 3),
                "hype_score": round(hype_score, 1),
                "source_count": source_count,
                "sources": sorted(entry["sources"]),
                "cycle": cycle,
            }
        else:
            results[t_upper] = {
                "mentions": 0,
                "sentiment": 0.0,
                "hype_score": 0.0,
                "source_count": 0,
                "sources": [],
                "cycle": None,
            }

    return results


def score_hype(hype_data):
    """convert raw hype data into a normalized score (0-100).

    Considers mention volume, sentiment direction, source breadth,
    and hype cycle acceleration.
    """
    mentions = hype_data["mentions"]
    sentiment = hype_data["sentiment"]
    source_count = hype_data["source_count"]
    cycle = hype_data["cycle"]

    score = 0

    if mentions >= 50:
        score += 35
    elif mentions >= 20:
        score += 25
    elif mentions >= 10:
        score += 15
    elif mentions >= 5:
        score += 8
    elif mentions >= 1:
        score += 3

    if sentiment > 0.3:
        score += 25
    elif sentiment > 0.1:
        score += 15
    elif sentiment > 0:
        score += 5
    elif sentiment < -0.3:
        score -= 10

    if source_count >= 4:
        score += 20
    elif source_count >= 2:
        score += 10
    elif source_count >= 1:
        score += 5

    if cycle is not None:
        ratio = cycle.get("ratio", 1.0)
        if ratio >= 3.0:
            score += 20
        elif ratio >= 2.0:
            score += 10

    return max(0, min(100, score))


def classify_convergence(squeeze_score, hype_score):
    """classify the convergence or divergence of squeeze and hype signals.

    Returns a label and a combined score. Convergence means both signals
    are elevated. Divergence means they disagree significantly.
    """
    combined = (squeeze_score + hype_score) / 2.0
    diff = abs(squeeze_score - hype_score)

    if squeeze_score >= 50 and hype_score >= 50:
        if diff <= 20:
            return "strong convergence", combined
        return "convergence", combined
    elif squeeze_score >= 50 and hype_score < 30:
        return "squeeze without hype", combined
    elif hype_score >= 50 and squeeze_score < 30:
        return "hype without squeeze", combined
    elif squeeze_score < 30 and hype_score < 30:
        return "no signal", combined
    else:
        return "mixed", combined


def generate_signal(squeeze_score, hype_score, convergence_label):
    """generate a trading signal based on convergence analysis.

    Returns the signal (entry/exit/hold) and confidence level.
    """
    combined = (squeeze_score + hype_score) / 2.0

    if convergence_label in ("strong convergence", "convergence") and combined >= 55:
        return "entry", round(combined, 1)
    elif convergence_label == "squeeze without hype" and squeeze_score >= 70:
        return "watch", round(combined, 1)
    elif convergence_label == "hype without squeeze":
        return "caution", round(combined, 1)
    elif convergence_label == "no signal":
        return "no trade", round(combined, 1)
    else:
        return "hold", round(combined, 1)


def analyze_moon(tickers, period="6mo"):
    """run full moon analysis on a list of tickers.

    For each ticker, runs squeeze analysis via reta and hype analysis via
    hype module, then combines the results into a convergence signal.
    Returns a list of result dicts sorted by combined score descending.
    """
    print(f"moon analysis: {len(tickers)} tickers")
    print(f"scanning social media for hype data...")
    hype_data = gather_hype_data(tickers)

    results = []
    for ticker in tickers:
        t_upper = ticker.upper()
        print(f"\nanalyzing {t_upper}...")

        rows = fetch_ohlc(t_upper, period)
        if not rows or len(rows) < 40:
            print(f"  insufficient price data for {t_upper}")
            continue

        finviz_data = fetch_finviz_stats(t_upper)
        squeeze_score, squeeze_breakdown = score_squeeze_potential(t_upper, rows, finviz_data)

        ticker_hype = hype_data.get(t_upper, {
            "mentions": 0, "sentiment": 0.0, "hype_score": 0.0,
            "source_count": 0, "sources": [], "cycle": None,
        })
        h_score = score_hype(ticker_hype)

        label, combined = classify_convergence(squeeze_score, h_score)
        signal, confidence = generate_signal(squeeze_score, h_score, label)

        results.append({
            "ticker": t_upper,
            "last_close": rows[-1]["close"],
            "last_date": rows[-1]["date"],
            "squeeze_score": squeeze_score,
            "squeeze_breakdown": squeeze_breakdown,
            "hype_score": h_score,
            "hype_data": ticker_hype,
            "convergence": label,
            "combined_score": round(combined, 1),
            "signal": signal,
            "confidence": confidence,
        })

    results.sort(key=lambda r: r["combined_score"], reverse=True)
    return results


def format_report(results):
    """format moon analysis results as readable text."""
    if not results:
        return "no results to display"

    lines = []
    lines.append("moon analysis results")
    lines.append("")

    for r in results:
        lines.append(f"{r['ticker']}  ${r['last_close']:.2f}  ({r['last_date']})")
        lines.append(f"  squeeze: {r['squeeze_score']}/100  |  hype: {r['hype_score']}/100  |  "
                     f"combined: {r['combined_score']}/100")
        lines.append(f"  convergence: {r['convergence']}")
        lines.append(f"  signal: {r['signal'].upper()} (confidence: {r['confidence']})")

        hd = r["hype_data"]
        lines.append(f"  hype detail: {hd['mentions']} mentions, "
                     f"sentiment {hd['sentiment']:+.3f}, "
                     f"{hd['source_count']} sources")
        if hd["cycle"]:
            c = hd["cycle"]
            lines.append(f"  hype cycle: {c['status']} ({c['ratio']:.1f}x acceleration)")

        bd = r["squeeze_breakdown"]
        parts = []
        for factor, (val, pts) in bd.items():
            if val is not None:
                parts.append(f"{factor}={val}({pts}pts)")
            else:
                parts.append(f"{factor}=n/a({pts}pts)")
        lines.append(f"  squeeze detail: {', '.join(parts)}")
        lines.append("")

    if len(results) > 1:
        lines.append("ranking (by combined score):")
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. {r['ticker']:<6} combined={r['combined_score']:>5.1f}  "
                         f"signal={r['signal']}")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python moon.py <ticker> [ticker2] [ticker3] ...")
        print("  checks tickers for squeeze + hype convergence")
        print("  example: python moon.py AMC GME BB")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    results = analyze_moon(tickers)
    print("\n" + format_report(results))
