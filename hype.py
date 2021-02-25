#!/usr/bin/env python3
"""hype: social media ticker sentiment aggregator"""

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
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


def extract_tickers(text):
    """extract stock tickers from text using $TICKER and standalone caps."""
    dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
    word_tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
    tickers = dollar_tickers + [t for t in word_tickers if t not in NOISE_WORDS]
    return tickers


def scan_subreddit(subreddit, sort="hot", limit=100):
    """scan a subreddit and return per-ticker mention counts."""
    posts = fetch_reddit_json(subreddit, sort, limit)
    if not posts:
        return {}

    ticker_data = defaultdict(lambda: {
        "mentions": 0,
        "timestamps": [],
        "sources": set(),
    })

    for post in posts:
        text = post["title"] + " " + post["selftext"]
        tickers = extract_tickers(text)
        if not tickers:
            continue
        weight = max(1, post["score"] // 100) + max(1, post["num_comments"] // 50)
        for t in tickers:
            entry = ticker_data[t]
            entry["mentions"] += weight
            entry["timestamps"].append(post["created"])
            entry["sources"].add(f"r/{subreddit}")

    return ticker_data


def scan_all(subreddits, sort="hot", limit=100):
    """scan all configured subreddits and aggregate results."""
    combined = {}
    for sub in subreddits:
        print(f"  scanning r/{sub}...")
        data = scan_subreddit(sub, sort, limit)
        for ticker, tdata in data.items():
            if ticker not in combined:
                combined[ticker] = {
                    "mentions": 0,
                    "timestamps": [],
                    "sources": set(),
                }
            combined[ticker]["mentions"] += tdata["mentions"]
            combined[ticker]["timestamps"].extend(tdata["timestamps"])
            combined[ticker]["sources"].update(tdata["sources"])
        time.sleep(2)
    return combined


def main():
    args = parse_args()
    subreddits = args.subreddits if args.subreddits else SUBREDDITS

    print(f"hype scanner: {len(subreddits)} subreddits, limit={args.limit}")
    ticker_data = scan_all(subreddits, sort=args.sort, limit=args.limit)

    if not ticker_data:
        print("no data collected")
        return

    results = []
    for ticker, data in ticker_data.items():
        results.append({
            "ticker": ticker,
            "mentions": data["mentions"],
            "sources": sorted(data["sources"]),
        })

    results.sort(key=lambda r: r["mentions"], reverse=True)

    print(f"\n{'ticker':<8} {'mentions':>9} {'sources':>8}")
    for r in results[:30]:
        src_count = len(r["sources"])
        print(f"  ${r['ticker']:<6} {r['mentions']:>9} {src_count:>8}")


def parse_args():
    """parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="social media ticker sentiment aggregator"
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
    return parser.parse_args()


if __name__ == "__main__":
    main()
