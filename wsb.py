#!/usr/bin/env python3
"""wsb: scrape reddit for ticker mentions and sentiment"""

import json
import re
import sys
import time
from collections import Counter
from urllib.request import urlopen, Request
from urllib.error import URLError


def fetch_reddit_json(subreddit, sort="hot", limit=100):
    """fetch posts from a subreddit via json api"""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    req = Request(url, headers={"User-Agent": "stock-scanner/1.0"})

    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            posts.append({
                "title": post.get("title", ""),
                "selftext": post.get("selftext", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "created": post.get("created_utc", 0),
                "url": post.get("url", ""),
            })
        return posts
    except (URLError, json.JSONDecodeError) as e:
        print(f"error fetching r/{subreddit}: {e}", file=sys.stderr)
        return []


def extract_tickers(text):
    """extract stock tickers from text ($AAPL or standalone caps)"""
    dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
    word_tickers = re.findall(r'\b([A-Z]{2,5})\b', text)

    noise = {
        "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
        "CAN", "HAS", "HER", "WAS", "ONE", "OUR", "OUT", "HIS",
        "HIM", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE",
        "WAY", "WHO", "BOY", "DID", "GET", "HAS", "LET", "SAY",
        "SHE", "TOO", "USE", "IMO", "YOLO", "DD", "WSB", "HOLD",
        "BUY", "SELL", "MOON", "GANG", "PUTS", "CALL", "EDIT",
        "TLDR", "LOL", "OMG", "WTF", "FYI", "PSA", "LMAO",
        "SEC", "ETF", "IPO", "CEO", "CFO", "GDP", "FDA", "NYSE",
        "FOMO", "HODL", "APES", "THIS", "THAT", "WITH", "FROM",
        "JUST", "BEEN", "HAVE", "WILL", "WHAT", "WHEN", "YOUR",
        "THEY", "THEM", "BEEN", "SOME", "THAN", "THEN", "VERY",
    }

    tickers = dollar_tickers + [t for t in word_tickers if t not in noise]
    return tickers


def scan_subreddit(subreddit, sort="hot", limit=100):
    """scan a subreddit for ticker mentions"""
    posts = fetch_reddit_json(subreddit, sort, limit)
    if not posts:
        return Counter()

    all_tickers = Counter()
    for post in posts:
        text = post["title"] + " " + post["selftext"]
        tickers = extract_tickers(text)
        weight = max(1, post["score"] // 100) + max(1, post["num_comments"] // 50)
        for t in tickers:
            all_tickers[t] += weight

    return all_tickers


def scan_wsb(limit=100):
    """scan wallstreetbets specifically"""
    return scan_subreddit("wallstreetbets", "hot", limit)


def scan_multi(subreddits, limit=50):
    """scan multiple subreddits and combine"""
    combined = Counter()
    for sub in subreddits:
        print(f"  scanning r/{sub}...")
        counts = scan_subreddit(sub, "hot", limit)
        combined.update(counts)
        time.sleep(2)
    return combined


def weight_by_subreddit(mentions, weights=None):
    """apply configurable weights to mentions from different subreddits.

    mentions: dict of {subreddit: Counter of tickers}
    weights: dict of {subreddit: float weight}, default equal weight
    returns combined Counter with weighted counts
    """
    if weights is None:
        weights = {}
    combined = Counter()
    for sub, ticker_counts in mentions.items():
        w = weights.get(sub, 1.0)
        for ticker, count in ticker_counts.items():
            combined[ticker] += int(count * w)
    return combined


def sentiment_score_text(text):
    """score text for bullish/bearish sentiment using word matching.

    returns dict with bullish count, bearish count, and net score (-1 to 1)
    """
    bullish_words = {
        "buy", "calls", "moon", "rocket", "bull", "long", "squeeze",
        "breakout", "undervalued", "dip", "tendies", "gains", "upside",
        "bullish", "rip", "pump", "green", "rally",
    }
    bearish_words = {
        "sell", "puts", "crash", "bear", "short", "dump", "overvalued",
        "drop", "tank", "red", "bearish", "fade", "drill", "bag",
        "loss", "losses", "down", "falling",
    }
    words = text.lower().split()
    bull_count = sum(1 for w in words if w in bullish_words)
    bear_count = sum(1 for w in words if w in bearish_words)
    total = bull_count + bear_count
    if total == 0:
        return {"bullish": 0, "bearish": 0, "score": 0.0}
    score = (bull_count - bear_count) / total
    return {
        "bullish": bull_count,
        "bearish": bear_count,
        "score": round(score, 4),
    }


if __name__ == "__main__":
    subs = ["wallstreetbets"]
    limit = 100

    if "--multi" in sys.argv:
        subs = [
            "wallstreetbets", "stocks", "investing",
            "options", "pennystocks", "smallstreetbets",
        ]
        limit = 50

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    print(f"scanning {', '.join(subs)} (limit={limit})")

    if len(subs) == 1:
        tickers = scan_subreddit(subs[0], "hot", limit)
    else:
        tickers = scan_multi(subs, limit)

    if not tickers:
        print("no tickers found")
    else:
        print("\ntop mentions:")
        for ticker, count in tickers.most_common(20):
            bar = "#" * min(count, 40)
            print(f"  ${ticker:<6} {count:>4} {bar}")
