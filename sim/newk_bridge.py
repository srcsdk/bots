#!/usr/bin/env python3
"""bridge to newk feed reader for news-trade correlation"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime

BULLISH_KEYWORDS = {
    "rally", "surge", "beat", "exceeded", "upgrade", "growth",
    "bull", "strong", "recovery", "rebound", "positive", "gains",
    "profit", "boom", "breakout", "record", "outperform", "buy",
    "optimistic", "expansion", "upside", "momentum",
}

BEARISH_KEYWORDS = {
    "crash", "plunge", "miss", "downgrade", "recession", "bear",
    "weak", "decline", "negative", "losses", "sell", "warning",
    "risk", "bubble", "default", "bankruptcy", "slump", "fear",
    "pessimistic", "contraction", "downside", "correction",
}

FINANCIAL_CATEGORIES = {"finance", "economics", "markets", "crypto", "stocks"}


class NewkBridge:
    """reads newk feed data for financial news correlation."""

    def __init__(self, newk_data_dir=None):
        self.data_dir = newk_data_dir or os.path.expanduser("~/src/newk/data")
        self.feeds = []
        self.sentiment_cache = {}

    def fetch_feeds(self, categories=None):
        """load rss feed data from newk data directory.

        categories: set of category names to filter by.
        returns list of feed entry dicts.
        """
        target_cats = categories or FINANCIAL_CATEGORIES
        entries = []
        feed_dir = os.path.join(self.data_dir, "feeds")
        if not os.path.isdir(feed_dir):
            feed_file = os.path.join(self.data_dir, "feeds.json")
            if os.path.exists(feed_file):
                return self._load_feed_file(feed_file, target_cats)
            return entries
        for fname in os.listdir(feed_dir):
            if not fname.endswith(".json"):
                continue
            cat = fname.replace(".json", "").lower()
            if cat not in target_cats:
                continue
            fpath = os.path.join(feed_dir, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        item["category"] = cat
                    entries.extend(data)
                elif isinstance(data, dict) and "entries" in data:
                    for item in data["entries"]:
                        item["category"] = cat
                    entries.extend(data["entries"])
            except (json.JSONDecodeError, IOError):
                continue
        self.feeds = entries
        return entries

    def _load_feed_file(self, filepath, categories):
        """load feeds from a single consolidated json file."""
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
        entries = []
        if isinstance(data, dict):
            for cat, items in data.items():
                if cat.lower() in categories:
                    for item in items:
                        item["category"] = cat.lower()
                    entries.extend(items)
        elif isinstance(data, list):
            entries = data
        self.feeds = entries
        return entries

    def sentiment_from_feeds(self, entries=None):
        """extract bullish/bearish sentiment from feed titles and summaries.

        returns dict of date -> sentiment score (-1 to 1).
        """
        feed_data = entries or self.feeds
        daily_scores = defaultdict(list)
        for entry in feed_data:
            text = (
                entry.get("title", "") + " " + entry.get("summary", "")
            ).lower()
            date = self._extract_date(entry)
            if not date:
                continue
            score = self._score_text(text)
            daily_scores[date].append(score)
        sentiment = {}
        for date, scores in daily_scores.items():
            avg = sum(scores) / len(scores)
            sentiment[date] = round(avg, 4)
        self.sentiment_cache = sentiment
        return sentiment

    def _score_text(self, text):
        """score text sentiment from keyword matches."""
        words = set(re.findall(r"[a-z]+", text))
        bull_count = len(words & BULLISH_KEYWORDS)
        bear_count = len(words & BEARISH_KEYWORDS)
        total = bull_count + bear_count
        if total == 0:
            return 0
        return (bull_count - bear_count) / total

    def _extract_date(self, entry):
        """extract date string from feed entry."""
        for field in ("published", "date", "updated", "created"):
            val = entry.get(field, "")
            if not val:
                continue
            if isinstance(val, str) and len(val) >= 10:
                date_part = val[:10]
                if re.match(r"\d{4}-\d{2}-\d{2}", date_part):
                    return date_part
        return None

    def correlate_with_trades(self, trades, sentiment=None):
        """match trade timestamps with news events.

        trades: list of trade dicts with date/timestamp field
        returns list of trades enriched with news_sentiment field.
        """
        sent = sentiment or self.sentiment_cache
        enriched = []
        for trade in trades:
            trade_copy = dict(trade)
            trade_date = trade.get("date", trade.get("timestamp", ""))[:10]
            trade_copy["news_sentiment"] = sent.get(trade_date, 0)
            prev_date = self._prev_trading_day(trade_date)
            trade_copy["prev_day_sentiment"] = sent.get(prev_date, 0)
            enriched.append(trade_copy)
        return enriched

    def _prev_trading_day(self, date_str):
        """get approximate previous trading day."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return ""
        weekday = dt.weekday()
        if weekday == 0:
            offset = 3
        elif weekday == 6:
            offset = 2
        else:
            offset = 1
        from datetime import timedelta
        prev = dt - timedelta(days=offset)
        return prev.strftime("%Y-%m-%d")

    def generate_news_signals(self, sentiment=None, bull_threshold=0.3,
                              bear_threshold=-0.3):
        """convert news sentiment into tradeable signals.

        returns list of signal dicts with date, direction, strength.
        """
        sent = sentiment or self.sentiment_cache
        signals = []
        prev_score = 0
        for date in sorted(sent.keys()):
            score = sent[date]
            momentum = score - prev_score
            if score >= bull_threshold:
                signals.append({
                    "date": date,
                    "direction": 1,
                    "strength": min(abs(score), 1.0),
                    "momentum": round(momentum, 4),
                    "type": "news_bullish",
                })
            elif score <= bear_threshold:
                signals.append({
                    "date": date,
                    "direction": -1,
                    "strength": min(abs(score), 1.0),
                    "momentum": round(momentum, 4),
                    "type": "news_bearish",
                })
            elif abs(momentum) > 0.4:
                direction = 1 if momentum > 0 else -1
                signals.append({
                    "date": date,
                    "direction": direction,
                    "strength": round(abs(momentum) * 0.5, 4),
                    "momentum": round(momentum, 4),
                    "type": "news_momentum_shift",
                })
            prev_score = score
        return signals

    def daily_summary(self, entries=None):
        """generate daily news summary with counts and sentiment."""
        feed_data = entries or self.feeds
        daily = defaultdict(lambda: {"count": 0, "bull": 0, "bear": 0, "titles": []})
        for entry in feed_data:
            date = self._extract_date(entry)
            if not date:
                continue
            title = entry.get("title", "")
            text = title.lower()
            daily[date]["count"] += 1
            daily[date]["titles"].append(title)
            score = self._score_text(text)
            if score > 0:
                daily[date]["bull"] += 1
            elif score < 0:
                daily[date]["bear"] += 1
        result = {}
        for date, data in sorted(daily.items()):
            total = data["bull"] + data["bear"]
            result[date] = {
                "articles": data["count"],
                "bullish": data["bull"],
                "bearish": data["bear"],
                "ratio": round(data["bull"] / total, 2) if total > 0 else 0.5,
            }
        return result


if __name__ == "__main__":
    bridge = NewkBridge()
    sample_entries = [
        {"title": "markets rally on strong earnings", "date": "2022-07-01"},
        {"title": "fed raises rates amid recession fears", "date": "2022-07-01"},
        {"title": "tech stocks surge on positive guidance", "date": "2022-07-02"},
        {"title": "oil prices plunge on demand concerns", "date": "2022-07-03"},
    ]
    sentiment = bridge.sentiment_from_feeds(sample_entries)
    print("daily sentiment:")
    for date, score in sorted(sentiment.items()):
        print(f"  {date}: {score}")
    signals = bridge.generate_news_signals(sentiment)
    print(f"\ngenerated {len(signals)} signals")
    for s in signals:
        print(f"  {s['date']}: {s['type']} dir={s['direction']}")
