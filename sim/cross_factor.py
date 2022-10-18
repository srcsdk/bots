#!/usr/bin/env python3
"""cross-factor analysis pipeline for strategy attribution"""

import json
import math
import os
import statistics
from collections import defaultdict


def load_macro_data(filepath=None):
    """load economic calendar events from json file.

    expects json with list of event dicts: date, event, value, previous,
    impact (high/medium/low).
    falls back to built-in sample data if no file provided.
    """
    if filepath and os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return [
        {"date": "2022-01-12", "event": "cpi", "value": 7.0, "previous": 6.8, "impact": "high"},
        {"date": "2022-01-26", "event": "fomc", "value": 0.25, "previous": 0.25, "impact": "high"},
        {"date": "2022-02-10", "event": "cpi", "value": 7.5, "previous": 7.0, "impact": "high"},
        {"date": "2022-03-16", "event": "fomc", "value": 0.50, "previous": 0.25, "impact": "high"},
        {"date": "2022-03-31", "event": "gdp", "value": 6.9, "previous": 2.3, "impact": "medium"},
        {"date": "2022-04-12", "event": "cpi", "value": 8.5, "previous": 7.9, "impact": "high"},
        {"date": "2022-05-04", "event": "fomc", "value": 1.0, "previous": 0.5, "impact": "high"},
        {"date": "2022-05-11", "event": "cpi", "value": 8.3, "previous": 8.5, "impact": "high"},
        {"date": "2022-06-01", "event": "nfp", "value": 390, "previous": 436, "impact": "high"},
        {"date": "2022-06-10", "event": "cpi", "value": 8.6, "previous": 8.3, "impact": "high"},
        {"date": "2022-06-15", "event": "fomc", "value": 1.75, "previous": 1.0, "impact": "high"},
    ]


def load_news_sentiment(filepath=None):
    """load aggregated news sentiment scores by date.

    expects json with date -> sentiment_score mapping (-1 to 1).
    generates synthetic data if no file provided.
    """
    if filepath and os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    import hashlib
    sentiment = {}
    for day_offset in range(180):
        date_str = f"2022-{(day_offset // 30) + 1:02d}-{(day_offset % 30) + 1:02d}"
        h = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
        score = (h % 200 - 100) / 100
        sentiment[date_str] = round(score, 3)
    return sentiment


def load_social_hype(filepath=None):
    """load social media sentiment aggregated by date.

    designed to read output from hype.py ticker analysis.
    """
    if filepath and os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return {}


class CrossFactorAnalyzer:
    """correlate strategy performance with external factors."""

    def __init__(self):
        self.macro_events = []
        self.news_sentiment = {}
        self.social_hype = {}
        self.strategy_returns = {}

    def load_factors(self, macro_file=None, news_file=None, social_file=None):
        """load all factor data sources."""
        self.macro_events = load_macro_data(macro_file)
        self.news_sentiment = load_news_sentiment(news_file)
        self.social_hype = load_social_hype(social_file)

    def set_strategy_returns(self, returns_by_date):
        """set strategy daily returns for attribution.

        returns_by_date: dict of date_str -> daily return float
        """
        self.strategy_returns = returns_by_date

    def factor_attribution(self):
        """attribute strategy returns to macro/news/social factors.

        splits returns into event days vs non-event days and measures
        the impact of each factor type.
        """
        event_dates = {e["date"] for e in self.macro_events}
        event_returns = []
        non_event_returns = []
        for date, ret in self.strategy_returns.items():
            if date in event_dates:
                event_returns.append(ret)
            else:
                non_event_returns.append(ret)
        high_impact_dates = {
            e["date"] for e in self.macro_events if e.get("impact") == "high"
        }
        high_impact_returns = [
            self.strategy_returns[d] for d in high_impact_dates
            if d in self.strategy_returns
        ]
        news_corr = self._news_correlation()
        social_corr = self._social_correlation()
        return {
            "event_day_avg": round(
                statistics.mean(event_returns), 6
            ) if event_returns else 0,
            "non_event_avg": round(
                statistics.mean(non_event_returns), 6
            ) if non_event_returns else 0,
            "high_impact_avg": round(
                statistics.mean(high_impact_returns), 6
            ) if high_impact_returns else 0,
            "event_days": len(event_returns),
            "non_event_days": len(non_event_returns),
            "news_correlation": news_corr,
            "social_correlation": social_corr,
            "macro_sensitivity": self._macro_sensitivity(),
        }

    def _news_correlation(self):
        """calculate correlation between news sentiment and returns."""
        paired = []
        for date, ret in self.strategy_returns.items():
            if date in self.news_sentiment:
                paired.append((self.news_sentiment[date], ret))
        if len(paired) < 10:
            return 0
        x = [p[0] for p in paired]
        y = [p[1] for p in paired]
        return _pearson(x, y)

    def _social_correlation(self):
        """calculate correlation between social hype and returns."""
        paired = []
        for date, ret in self.strategy_returns.items():
            if date in self.social_hype:
                paired.append((self.social_hype[date], ret))
        if len(paired) < 10:
            return 0
        x = [p[0] for p in paired]
        y = [p[1] for p in paired]
        return _pearson(x, y)

    def _macro_sensitivity(self):
        """measure sensitivity to each macro event type."""
        event_type_returns = defaultdict(list)
        for event in self.macro_events:
            date = event["date"]
            if date in self.strategy_returns:
                event_type_returns[event["event"]].append(
                    self.strategy_returns[date]
                )
        sensitivity = {}
        for event_type, returns in event_type_returns.items():
            if len(returns) < 2:
                sensitivity[event_type] = {
                    "avg_return": round(statistics.mean(returns), 6),
                    "count": len(returns),
                }
            else:
                sensitivity[event_type] = {
                    "avg_return": round(statistics.mean(returns), 6),
                    "volatility": round(statistics.pstdev(returns), 6),
                    "count": len(returns),
                }
        return sensitivity

    def regime_factor_matrix(self, regime_dates):
        """show which factors matter in which market regimes.

        regime_dates: dict of date_str -> regime_name
        """
        regime_factors = defaultdict(lambda: {
            "returns": [],
            "news_scores": [],
            "event_count": 0,
        })
        event_dates = {e["date"] for e in self.macro_events}
        for date, regime in regime_dates.items():
            bucket = regime_factors[regime]
            if date in self.strategy_returns:
                bucket["returns"].append(self.strategy_returns[date])
            if date in self.news_sentiment:
                bucket["news_scores"].append(self.news_sentiment[date])
            if date in event_dates:
                bucket["event_count"] += 1
        matrix = {}
        for regime, data in regime_factors.items():
            returns = data["returns"]
            news = data["news_scores"]
            matrix[regime] = {
                "n_days": len(returns),
                "avg_return": round(
                    statistics.mean(returns), 6
                ) if returns else 0,
                "news_correlation": _pearson(
                    news[:len(returns)], returns[:len(news)]
                ) if len(news) >= 10 and len(returns) >= 10 else 0,
                "event_density": round(
                    data["event_count"] / max(len(returns), 1), 3
                ),
            }
        return matrix


def _pearson(x, y):
    """pearson correlation coefficient."""
    n = min(len(x), len(y))
    if n < 3:
        return 0
    x = x[:n]
    y = y[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return 0
    return round(cov / denom, 4)


if __name__ == "__main__":
    analyzer = CrossFactorAnalyzer()
    analyzer.load_factors()
    import hashlib
    returns = {}
    for day in range(1, 181):
        date_str = f"2022-{(day // 30) + 1:02d}-{(day % 30) + 1:02d}"
        h = int(hashlib.md5(f"ret_{date_str}".encode()).hexdigest()[:8], 16)
        returns[date_str] = round((h % 400 - 200) / 10000, 4)
    analyzer.set_strategy_returns(returns)
    attr = analyzer.factor_attribution()
    print("factor attribution:")
    for k, v in attr.items():
        print(f"  {k}: {v}")
