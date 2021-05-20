#!/usr/bin/env python3
"""mo4p: mooop enhanced with news and macro data feeds

runs mooop combined strategy then adjusts signals based on macro environment:
treasury yield curve, vix trend, sector etf performance, and financial news
headlines scraped from rss feeds.
"""

import json
import sys
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError

from mooop import analyze_ticker, print_report


SECTOR_ETFS = {
    "XLK": "technology",
    "XLF": "financials",
    "XLE": "energy",
    "XLV": "healthcare",
    "XLI": "industrials",
    "XLY": "consumer discretionary",
    "XLP": "consumer staples",
    "XLU": "utilities",
    "XLB": "materials",
    "XLRE": "real estate",
    "XLC": "communication",
}

RSS_FEEDS = [
    ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
     "yahoo sp500"),
    ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EVIX&region=US&lang=en-US",
     "yahoo vix"),
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html",
     "cnbc markets"),
]

TICKER_SECTOR_MAP = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "GOOG": "XLC",
    "GOOGL": "XLC", "META": "XLC", "AMZN": "XLY", "TSLA": "XLY",
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "XOM": "XLE",
    "CVX": "XLE", "JNJ": "XLV", "UNH": "XLV", "PFE": "XLV",
    "CAT": "XLI", "BA": "XLI", "HD": "XLY", "WMT": "XLP",
    "PG": "XLP", "NEE": "XLU", "DUK": "XLU",
}


def fetch_url(url, timeout=10):
    """fetch url content as bytes, return None on error."""
    req = Request(url, headers={"User-Agent": "market-scanner/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, OSError) as e:
        print(f"  fetch error {url}: {e}", file=sys.stderr)
        return None


def fetch_json(url, timeout=10):
    """fetch and parse json from url."""
    raw = fetch_url(url, timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None


def get_vix_trend():
    """fetch recent vix data and compute trend.

    returns dict with current vix, 5-day trend direction, and sentiment label.
    """
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
           "?range=1mo&interval=1d")
    data = fetch_json(url)
    if not data:
        return None

    try:
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
    except (KeyError, IndexError):
        return None

    if len(closes) < 5:
        return None

    current = closes[-1]
    avg_5d = sum(closes[-5:]) / 5
    avg_20d = sum(closes[-20:]) / len(closes[-20:]) if len(closes) >= 20 else avg_5d

    if current < avg_5d < avg_20d:
        trend = "declining"
    elif current > avg_5d > avg_20d:
        trend = "rising"
    elif current < avg_5d:
        trend = "easing"
    else:
        trend = "elevated"

    if current < 15:
        sentiment = "extreme greed"
    elif current < 20:
        sentiment = "greed"
    elif current < 25:
        sentiment = "neutral"
    elif current < 30:
        sentiment = "fear"
    else:
        sentiment = "extreme fear"

    return {
        "vix": round(current, 2),
        "avg_5d": round(avg_5d, 2),
        "avg_20d": round(avg_20d, 2),
        "trend": trend,
        "sentiment": sentiment,
    }


def get_treasury_curve():
    """fetch treasury yield curve data from fiscal data api.

    returns dict with short and long term rates plus curve status.
    """
    url = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
           "v2/accounting/od/avg_interest_rates"
           "?sort=-record_date&page[size]=10")
    data = fetch_json(url)
    if not data:
        return None

    records = data.get("data", [])
    if not records:
        return None

    short_rate = None
    long_rate = None
    for r in records:
        desc = r.get("security_desc", "").lower()
        rate = r.get("avg_interest_rate_amt")
        if rate is None:
            continue
        try:
            rate = float(rate)
        except (ValueError, TypeError):
            continue
        if "treasury bills" in desc and short_rate is None:
            short_rate = rate
        elif "treasury bonds" in desc and long_rate is None:
            long_rate = rate

    if short_rate is not None and long_rate is not None:
        spread = long_rate - short_rate
        if spread < 0:
            status = "inverted"
        elif spread < 0.5:
            status = "flat"
        else:
            status = "normal"
    else:
        spread = None
        status = "unknown"

    return {
        "short_rate": short_rate,
        "long_rate": long_rate,
        "spread": round(spread, 3) if spread is not None else None,
        "status": status,
    }


def get_sector_performance():
    """fetch recent performance for sector etfs via yahoo finance.

    returns dict mapping etf symbol to performance data.
    """
    results = {}
    for etf, sector_name in SECTOR_ETFS.items():
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{etf}"
               f"?range=1mo&interval=1d")
        data = fetch_json(url)
        if not data:
            continue

        try:
            chart = data["chart"]["result"][0]
            closes = chart["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
        except (KeyError, IndexError):
            continue

        if len(closes) < 2:
            continue

        pct_1m = (closes[-1] - closes[0]) / closes[0] * 100
        pct_1w = 0
        if len(closes) >= 5:
            pct_1w = (closes[-1] - closes[-5]) / closes[-5] * 100

        results[etf] = {
            "sector": sector_name,
            "price": round(closes[-1], 2),
            "pct_1w": round(pct_1w, 2),
            "pct_1m": round(pct_1m, 2),
        }

    return results


def fetch_rss_headlines():
    """scrape headlines from financial rss feeds.

    parses rss xml, extracts title and pub date from each item.
    """
    all_headlines = []
    for feed_url, source_name in RSS_FEEDS:
        raw = fetch_url(feed_url)
        if raw is None:
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue

        for item in root.iter("item"):
            title_el = item.find("title")
            pub_el = item.find("pubDate")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            pub = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
            if title:
                all_headlines.append({
                    "source": source_name,
                    "title": title,
                    "date": pub,
                })

    return all_headlines


def headline_sentiment(headlines, tickers):
    """simple keyword sentiment from headlines relevant to tickers.

    scans for bullish/bearish keywords in headlines that mention any ticker.
    returns score from -1 (bearish) to +1 (bullish).
    """
    bullish_words = [
        "surge", "rally", "gain", "rise", "jump", "soar", "record",
        "upgrade", "beat", "strong", "bull", "growth", "boost", "high",
        "breakout", "outperform", "buy",
    ]
    bearish_words = [
        "fall", "drop", "plunge", "crash", "decline", "loss", "cut",
        "downgrade", "miss", "weak", "bear", "recession", "fear",
        "sell", "warning", "tariff", "sanction",
    ]

    relevant = []
    ticker_set = {t.lower() for t in tickers}
    for h in headlines:
        title_lower = h["title"].lower()
        for t in ticker_set:
            if t in title_lower:
                relevant.append(h)
                break

    if not relevant:
        return {"score": 0, "relevant_count": 0, "headlines": []}

    bull_count = 0
    bear_count = 0
    for h in relevant:
        title_lower = h["title"].lower()
        for w in bullish_words:
            if w in title_lower:
                bull_count += 1
        for w in bearish_words:
            if w in title_lower:
                bear_count += 1

    total = bull_count + bear_count
    if total == 0:
        sentiment_score = 0
    else:
        sentiment_score = (bull_count - bear_count) / total

    return {
        "score": round(sentiment_score, 3),
        "relevant_count": len(relevant),
        "bull_hits": bull_count,
        "bear_hits": bear_count,
        "headlines": relevant[:10],
    }


def macro_adjustment(vix_data, curve_data, sector_data, sector_etf, news_sentiment):
    """compute macro adjustment factor for mooop composite score.

    positive adjustment means macro supports the trade.
    negative means macro headwinds.
    range: -0.15 to +0.15
    """
    adj = 0.0
    reasons = []

    if vix_data:
        if vix_data["sentiment"] in ("greed", "extreme greed"):
            adj += 0.03
            reasons.append(f"vix {vix_data['vix']} ({vix_data['sentiment']}): favorable")
        elif vix_data["sentiment"] in ("fear", "extreme fear"):
            adj -= 0.05
            reasons.append(f"vix {vix_data['vix']} ({vix_data['sentiment']}): headwind")
        if vix_data["trend"] == "declining":
            adj += 0.02
            reasons.append("vix declining: risk appetite improving")
        elif vix_data["trend"] == "rising":
            adj -= 0.03
            reasons.append("vix rising: risk aversion increasing")

    if curve_data:
        if curve_data["status"] == "inverted":
            adj -= 0.04
            reasons.append(f"yield curve inverted (spread {curve_data['spread']}): bearish")
        elif curve_data["status"] == "normal":
            adj += 0.02
            reasons.append(f"yield curve normal (spread {curve_data['spread']}): healthy")

    if sector_data and sector_etf and sector_etf in sector_data:
        perf = sector_data[sector_etf]
        if perf["pct_1w"] > 2:
            adj += 0.03
            reasons.append(f"{sector_etf} ({perf['sector']}) +{perf['pct_1w']}% 1w: sector strong")
        elif perf["pct_1w"] < -2:
            adj -= 0.03
            reasons.append(f"{sector_etf} ({perf['sector']}) {perf['pct_1w']}% 1w: sector weak")

    if news_sentiment:
        ns = news_sentiment.get("score", 0)
        adj += ns * 0.05
        if ns > 0.3:
            reasons.append(f"news sentiment positive ({ns:.2f})")
        elif ns < -0.3:
            reasons.append(f"news sentiment negative ({ns:.2f})")

    adj = max(-0.15, min(0.15, adj))
    return {"adjustment": round(adj, 4), "reasons": reasons}


def check_yield_curve(yields_data):
    """detect yield curve inversion (2y > 10y) and return inversion status.

    yields_data: dict with short_rate and long_rate keys (from get_treasury_curve)
    returns dict with inversion status and spread
    """
    if not yields_data:
        return {"inverted": False, "spread": None, "status": "no data"}
    short = yields_data.get("short_rate")
    long = yields_data.get("long_rate")
    if short is None or long is None:
        return {"inverted": False, "spread": None, "status": "incomplete data"}
    spread = round(long - short, 4)
    inverted = spread < 0
    if inverted:
        status = "inverted"
    elif spread < 0.25:
        status = "flat"
    else:
        status = "normal"
    return {"inverted": inverted, "spread": spread, "status": status}


def analyze_with_macro(tickers):
    """run mooop analysis enhanced with macro data for each ticker.

    fetches macro data once, applies to all tickers.
    """
    print("fetching macro data...")
    vix_data = get_vix_trend()
    curve_data = get_treasury_curve()
    sector_data = get_sector_performance()
    headlines = fetch_rss_headlines()

    print(f"  vix: {vix_data['vix'] if vix_data else '?'}"
          f"  curve: {curve_data['status'] if curve_data else '?'}"
          f"  headlines: {len(headlines)}")

    news_sent = headline_sentiment(headlines, tickers)
    results = []

    for ticker in tickers:
        result = analyze_ticker(ticker)
        sector_etf = TICKER_SECTOR_MAP.get(ticker)
        macro_adj = macro_adjustment(
            vix_data, curve_data, sector_data, sector_etf, news_sent
        )
        original_composite = result["composite"]["composite"]
        adjusted = max(0, min(1.0, original_composite + macro_adj["adjustment"]))

        if adjusted >= 0.7:
            adj_signal = "strong_buy"
        elif adjusted >= 0.5:
            adj_signal = "buy"
        elif adjusted >= 0.3:
            adj_signal = "watch"
        else:
            adj_signal = "pass"

        result["macro"] = {
            "vix": vix_data,
            "curve": curve_data,
            "sector_etf": sector_etf,
            "sector_perf": sector_data.get(sector_etf) if sector_etf else None,
            "news_sentiment": news_sent,
            "adjustment": macro_adj,
            "original_composite": original_composite,
            "adjusted_composite": round(adjusted, 3),
            "adjusted_signal": adj_signal,
        }
        results.append(result)

    results.sort(key=lambda r: -r["macro"]["adjusted_composite"])
    return results


def print_macro_report(results):
    """print full mo4p report with macro overlay."""
    for result in results:
        print_report(result)
        m = result["macro"]
        adj = m["adjustment"]

        print(f"  macro adjustment: {adj['adjustment']:+.4f}"
              f"  ({m['original_composite']:.3f} -> {m['adjusted_composite']:.3f})")
        print(f"  adjusted signal: {m['adjusted_signal']}")

        if adj["reasons"]:
            print("  macro factors:")
            for reason in adj["reasons"]:
                print(f"    {reason}")

        if m.get("sector_perf"):
            sp = m["sector_perf"]
            print(f"  sector: {sp['sector']} ({m['sector_etf']})"
                  f"  1w: {sp['pct_1w']:+.2f}%  1m: {sp['pct_1m']:+.2f}%")

        ns = m.get("news_sentiment", {})
        if ns.get("relevant_count", 0) > 0:
            print(f"  news: {ns['relevant_count']} relevant headlines"
                  f"  sentiment: {ns['score']:+.3f}")
            for h in ns.get("headlines", [])[:3]:
                print(f"    [{h['source']}] {h['title'][:80]}")

    print("\nmo4p ranking (macro-adjusted):")
    for i, r in enumerate(results, 1):
        m = r["macro"]
        print(f"  {i}. {r['ticker']:<6} {m['adjusted_signal']:<12}"
              f" {m['adjusted_composite']:.3f}"
              f"  (base {m['original_composite']:.3f}"
              f"  adj {m['adjustment']['adjustment']:+.4f})")


def main():
    if len(sys.argv) < 2:
        print("usage: python mo4p.py TICKER [TICKER ...]")
        print("  example: python mo4p.py NVDA AAPL")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    print(f"mo4p analysis: {', '.join(tickers)}")

    results = analyze_with_macro(tickers)
    print_macro_report(results)


if __name__ == "__main__":
    main()
