#!/usr/bin/env python3
"""hype: social media ticker sentiment aggregator"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from urllib.request import urlopen, Request
from urllib.error import URLError


SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "options",
    "smallstreetbets",
    "pennystocks",
    "spacs",
    "stockmarket",
]

NOISE_WORDS = {
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
    "CAN", "HAS", "HER", "WAS", "ONE", "OUR", "OUT", "HIS",
    "HIM", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE",
    "WAY", "WHO", "BOY", "DID", "GET", "LET", "SAY",
    "SHE", "TOO", "USE", "IMO", "YOLO", "WSB", "HOLD",
    "BUY", "SELL", "MOON", "GANG", "PUTS", "CALL", "EDIT",
    "TLDR", "LOL", "OMG", "WTF", "FYI", "PSA", "LMAO",
    "SEC", "ETF", "IPO", "CEO", "CFO", "GDP", "FDA", "NYSE",
    "FOMO", "HODL", "APES", "THIS", "THAT", "WITH", "FROM",
    "JUST", "BEEN", "HAVE", "WILL", "WHAT", "WHEN", "YOUR",
    "THEY", "THEM", "SOME", "THAN", "THEN", "VERY",
    "ALSO", "MUCH", "LIKE", "ONLY", "OVER", "SUCH", "TAKE",
    "LONG", "COME", "MADE", "FIND", "HERE", "KNOW", "WANT",
    "GIVE", "MOST", "MAKE", "GOOD", "LOOK", "NEED", "DOES",
    "WELL", "BACK", "EVEN", "CALL", "EACH", "JUST", "THOSE",
    "MANY", "SAME", "KEEP", "LAST", "WEEK", "YEAR", "OPEN",
    "HIGH", "STOP", "WENT", "DOWN", "PLAY", "DONT", "CANT",
    "WONT", "PUMP", "DUMP", "BEAR", "BULL", "BAGS", "RISK",
    "HUGE", "LOSS", "GAIN", "MOVE", "DROP", "JUMP", "PUSH",
    "PULL", "PICK", "NEXT", "BEST", "EVER", "PART", "FREE",
    "REAL", "SURE", "IDEA", "HELP", "TOLD", "READ", "POST",
    "LINK", "HOPE", "FEEL", "FUCK", "SHIT", "DAMN", "HELL",
}

BULLISH_WORDS = {
    "bull", "bullish", "buy", "long", "calls", "call", "moon",
    "rocket", "squeeze", "breakout", "undervalued", "upside",
    "profit", "gains", "green", "rally", "soar", "surge",
    "boom", "rip", "pump", "diamond", "tendies", "lambo",
    "yolo", "fomo", "gap up", "mooning", "printing", "brrrr",
    "strong", "growth", "promising", "opportunity", "winner",
    "beat", "exceeded", "upgrade", "upgraded", "accumulate",
    "outperform", "positive", "recovery", "rebound",
}

BEARISH_WORDS = {
    "bear", "bearish", "sell", "short", "puts", "put", "crash",
    "dump", "tank", "overvalued", "downside", "loss", "losses",
    "red", "drill", "plunge", "drop", "sink", "bag", "bags",
    "bagholder", "bleeding", "dead", "rip", "dump", "fade",
    "weak", "decline", "risk", "warning", "avoid", "bubble",
    "scam", "fraud", "dilution", "bankruptcy", "default",
    "downgrade", "downgraded", "underperform", "negative",
    "miss", "missed", "worse", "worst", "falling", "crashing",
}


def fetch_reddit_json(subreddit, sort="hot", limit=100):
    """fetch posts from a subreddit via public json api."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    req = Request(url, headers={"User-Agent": "hype-scanner/1.0"})
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
                "subreddit": subreddit,
            })
        return posts
    except (URLError, json.JSONDecodeError, ValueError) as e:
        print(f"  error fetching r/{subreddit}: {e}", file=sys.stderr)
        return []


def fetch_reddit_comments(subreddit, post_id, limit=50):
    """fetch comments from a specific post."""
    url = (
        f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        f"?limit={limit}"
    )
    req = Request(url, headers={"User-Agent": "hype-scanner/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        comments = []
        if len(data) < 2:
            return comments
        _flatten_comments(data[1].get("data", {}).get("children", []), comments)
        return comments
    except (URLError, json.JSONDecodeError, ValueError) as e:
        print(f"  error fetching comments: {e}", file=sys.stderr)
        return []


def _flatten_comments(children, out):
    """recursively flatten reddit comment tree into a list of text strings."""
    for child in children:
        if child.get("kind") != "t1":
            continue
        cdata = child.get("data", {})
        body = cdata.get("body", "")
        if body:
            out.append(body)
        replies = cdata.get("replies")
        if isinstance(replies, dict):
            nested = replies.get("data", {}).get("children", [])
            _flatten_comments(nested, out)


def extract_tickers(text):
    """extract stock tickers from text using $TICKER and standalone caps."""
    dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
    word_tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
    tickers = dollar_tickers + [t for t in word_tickers if t not in NOISE_WORDS]
    return tickers


def score_sentiment(text):
    """score sentiment of text based on keyword matching.

    Returns a float between -1.0 (very bearish) and 1.0 (very bullish).
    """
    words = text.lower().split()
    bull_count = sum(1 for w in words if w in BULLISH_WORDS)
    bear_count = sum(1 for w in words if w in BEARISH_WORDS)
    total = bull_count + bear_count
    if total == 0:
        return 0.0
    return (bull_count - bear_count) / total


def scan_subreddit(subreddit, sort="hot", limit=100):
    """scan a subreddit and return per-ticker mention and sentiment data.

    Returns dict mapping ticker -> {mentions, sentiment_sum, sentiment_count,
    timestamps, sources}.
    """
    posts = fetch_reddit_json(subreddit, sort, limit)
    if not posts:
        return {}

    ticker_data = defaultdict(lambda: {
        "mentions": 0,
        "sentiment_sum": 0.0,
        "sentiment_count": 0,
        "timestamps": [],
        "sources": set(),
    })

    for post in posts:
        text = post["title"] + " " + post["selftext"]
        tickers = extract_tickers(text)
        if not tickers:
            continue
        sentiment = score_sentiment(text)
        weight = max(1, post["score"] // 100) + max(1, post["num_comments"] // 50)
        for t in tickers:
            entry = ticker_data[t]
            entry["mentions"] += weight
            entry["sentiment_sum"] += sentiment * weight
            entry["sentiment_count"] += weight
            entry["timestamps"].append(post["created"])
            entry["sources"].add(f"r/{subreddit}")

    return ticker_data


def merge_ticker_data(combined, new_data):
    """merge new ticker data into the combined accumulator."""
    for ticker, data in new_data.items():
        if ticker not in combined:
            combined[ticker] = {
                "mentions": 0,
                "sentiment_sum": 0.0,
                "sentiment_count": 0,
                "timestamps": [],
                "sources": set(),
            }
        entry = combined[ticker]
        entry["mentions"] += data["mentions"]
        entry["sentiment_sum"] += data["sentiment_sum"]
        entry["sentiment_count"] += data["sentiment_count"]
        entry["timestamps"].extend(data["timestamps"])
        entry["sources"].update(data["sources"])


def detect_hype_cycles(ticker_data, window_hours=6):
    """detect tickers with rapidly increasing mention volume.

    Compares mentions in the recent window to the older window. A ratio
    above 2.0 indicates a hype cycle is forming.
    """
    now = time.time()
    window_sec = window_hours * 3600
    hype_tickers = {}

    for ticker, data in ticker_data.items():
        timestamps = data["timestamps"]
        if len(timestamps) < 3:
            continue
        recent = sum(1 for ts in timestamps if (now - ts) < window_sec)
        older = sum(1 for ts in timestamps if window_sec <= (now - ts) < window_sec * 2)
        if older == 0:
            if recent >= 3:
                hype_tickers[ticker] = {
                    "recent": recent,
                    "older": older,
                    "ratio": float(recent),
                    "status": "new_spike",
                }
            continue
        ratio = recent / older
        if ratio >= 2.0:
            hype_tickers[ticker] = {
                "recent": recent,
                "older": older,
                "ratio": ratio,
                "status": "accelerating",
            }

    return hype_tickers


def compute_hype_score(mentions, sentiment, source_count):
    """compute a composite hype score from mentions, sentiment, and breadth.

    Score weights volume heavily, adds a sentiment bonus, and rewards
    tickers mentioned across multiple sources.
    """
    volume_score = mentions
    sentiment_bonus = max(0, sentiment) * mentions * 0.5
    breadth_bonus = (source_count - 1) * mentions * 0.25 if source_count > 1 else 0
    return volume_score + sentiment_bonus + breadth_bonus


def scan_all(subreddits, sort="hot", limit=100):
    """scan all configured subreddits and aggregate results."""
    combined = {}
    for sub in subreddits:
        print(f"  scanning r/{sub}...")
        data = scan_subreddit(sub, sort, limit)
        merge_ticker_data(combined, data)
        time.sleep(2)
    return combined


def format_sentiment(value):
    """format a sentiment float as a labeled string."""
    if value > 0.3:
        return f"+{value:.2f} bullish"
    if value < -0.3:
        return f"{value:.2f} bearish"
    if value > 0.05:
        return f"+{value:.2f} leaning bull"
    if value < -0.05:
        return f"{value:.2f} leaning bear"
    return f"{value:.2f} neutral"


def print_results(ticker_data, hype_cycles, filter_ticker=None):
    """print ranked ticker results to stdout."""
    results = []
    for ticker, data in ticker_data.items():
        if filter_ticker and ticker != filter_ticker.upper():
            continue
        sentiment = 0.0
        if data["sentiment_count"] > 0:
            sentiment = data["sentiment_sum"] / data["sentiment_count"]
        source_count = len(data["sources"])
        hype_score = compute_hype_score(data["mentions"], sentiment, source_count)
        results.append({
            "ticker": ticker,
            "mentions": data["mentions"],
            "sentiment": sentiment,
            "sources": sorted(data["sources"]),
            "hype_score": hype_score,
            "hype_cycle": hype_cycles.get(ticker),
        })

    results.sort(key=lambda r: r["hype_score"], reverse=True)

    if not results:
        if filter_ticker:
            print(f"no mentions found for ${filter_ticker.upper()}")
        else:
            print("no tickers found")
        return

    print(f"\n{'ticker':<8} {'score':>7} {'mentions':>9} {'sentiment':>18} {'sources':>8}  hype")
    print("-" * 72)

    display_count = len(results) if filter_ticker else min(30, len(results))
    for r in results[:display_count]:
        sent_str = format_sentiment(r["sentiment"])
        hype_flag = ""
        cycle = r["hype_cycle"]
        if cycle:
            hype_flag = f"<< {cycle['status']} ({cycle['ratio']:.1f}x)"
        src_count = len(r["sources"])
        bar = "#" * min(int(r["hype_score"]), 20)  # noqa: F841
        print(
            f"  ${r['ticker']:<6} {r['hype_score']:>7.1f} {r['mentions']:>9} "
            f"{sent_str:>18} {src_count:>8}  {hype_flag}"
        )

    if filter_ticker and results:
        r = results[0]
        print(f"\ndetail for ${r['ticker']}:")
        print(f"  mentioned in: {', '.join(r['sources'])}")
        print(f"  raw mentions (weighted): {r['mentions']}")
        cycle = r["hype_cycle"]
        if cycle:
            print(
                f"  hype cycle: {cycle['status']} "
                f"(recent={cycle['recent']}, older={cycle['older']}, "
                f"ratio={cycle['ratio']:.1f}x)"
            )
        else:
            print("  hype cycle: none detected")


def parse_args():
    """parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="social media ticker sentiment aggregator"
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        help="filter results to a specific ticker symbol",
    )
    parser.add_argument(
        "--subreddits", type=str, nargs="+", default=None,
        help="override default subreddit list",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="number of posts to fetch per subreddit (default: 50)",
    )
    parser.add_argument(
        "--sort", type=str, default="hot", choices=["hot", "new", "top"],
        help="sort order for reddit posts (default: hot)",
    )
    parser.add_argument(
        "--window", type=float, default=6.0,
        help="hype cycle detection window in hours (default: 6)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    subreddits = args.subreddits if args.subreddits else SUBREDDITS

    print(f"hype scanner: {len(subreddits)} subreddits, limit={args.limit}")
    ticker_data = scan_all(subreddits, sort=args.sort, limit=args.limit)

    if not ticker_data:
        print("no data collected")
        return

    hype_cycles = detect_hype_cycles(ticker_data, window_hours=args.window)

    if hype_cycles:
        print(f"\nhype cycles detected: {len(hype_cycles)} tickers")

    print_results(ticker_data, hype_cycles, filter_ticker=args.ticker)


if __name__ == "__main__":
    main()
