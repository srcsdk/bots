#!/usr/bin/env python3
"""data source manager for backtesting with yahoo finance and csv support"""

import csv
import json
import os
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError


class DataSource:
    """fetch and cache market data for backtesting."""

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data"
            )
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_yahoo(self, ticker, start, end):
        """fetch ohlcv data from yahoo finance api.

        start/end: date strings YYYY-MM-DD or datetime objects.
        returns list of bar dicts with date, open, high, low, close, volume.
        """
        if isinstance(start, str):
            start = datetime.strptime(start, "%Y-%m-%d")
        if isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d")
        p1 = int(start.timestamp())
        p2 = int(end.timestamp())
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?period1={p1}&period2={p2}&interval=1d"
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except (URLError, json.JSONDecodeError) as e:
            print(f"yahoo fetch error for {ticker}: {e}")
            return []
        result = data.get("chart", {}).get("result", [])
        if not result:
            return []
        chart = result[0]
        timestamps = chart.get("timestamp", [])
        quote = chart.get("indicators", {}).get("quote", [{}])[0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])
        bars = []
        for i in range(len(timestamps)):
            if closes[i] is None:
                continue
            dt = datetime.utcfromtimestamp(timestamps[i])
            bars.append({
                "date": dt.strftime("%Y-%m-%d"),
                "open": round(float(opens[i] or 0), 2),
                "high": round(float(highs[i] or 0), 2),
                "low": round(float(lows[i] or 0), 2),
                "close": round(float(closes[i] or 0), 2),
                "volume": int(volumes[i] or 0),
            })
        return bars

    def fetch_from_csv(self, filepath):
        """load ohlcv data from a csv file.

        expects columns: Date,Open,High,Low,Close,Volume (or lowercase).
        returns list of bar dicts.
        """
        if not os.path.isfile(filepath):
            return []
        bars = []
        with open(filepath) as f:
            reader = csv.DictReader(f)
            header_map = {}
            if reader.fieldnames:
                for h in reader.fieldnames:
                    header_map[h.lower().strip()] = h
            for row in reader:
                bar = {}
                for key in ("date", "open", "high", "low", "close", "volume"):
                    col = header_map.get(key, key)
                    val = row.get(col, row.get(key, ""))
                    if key == "date":
                        bar[key] = str(val).strip()
                    elif key == "volume":
                        try:
                            bar[key] = int(float(val))
                        except (ValueError, TypeError):
                            bar[key] = 0
                    else:
                        try:
                            bar[key] = round(float(val), 2)
                        except (ValueError, TypeError):
                            bar[key] = 0.0
                bars.append(bar)
        return bars

    def generate_historical(self, ticker, years=10):
        """fetch up to n years of daily data from yahoo finance.

        fetches in yearly chunks to avoid api limits, then combines.
        returns list of bar dicts sorted by date.
        """
        now = datetime.utcnow()
        start_year = now.year - years
        start = datetime(start_year, 1, 1)
        end = now
        bars = self.fetch_yahoo(ticker, start, end)
        if bars:
            self.cache_data(ticker, bars)
        return bars

    def cache_data(self, ticker, data):
        """cache bar data to the data directory as json."""
        filepath = os.path.join(self.cache_dir, f"{ticker.lower()}_daily.json")
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_cached(self, ticker):
        """load cached data for a ticker.

        returns list of bar dicts or None if cache miss.
        """
        filepath = os.path.join(self.cache_dir, f"{ticker.lower()}_daily.json")
        if not os.path.isfile(filepath):
            return None
        mtime = os.path.getmtime(filepath)
        age_hours = (time.time() - mtime) / 3600
        if age_hours > 24:
            return None
        with open(filepath) as f:
            return json.load(f)

    def normalize(self, data):
        """ensure consistent ohlcv format across all bar dicts.

        fills missing fields with defaults, ensures correct types.
        returns cleaned list of bar dicts.
        """
        cleaned = []
        for bar in data:
            normalized = {
                "date": str(bar.get("date", "1970-01-01")),
                "open": float(bar.get("open", 0)),
                "high": float(bar.get("high", 0)),
                "low": float(bar.get("low", 0)),
                "close": float(bar.get("close", 0)),
                "volume": int(bar.get("volume", 0)),
            }
            if normalized["high"] == 0 and normalized["close"] > 0:
                normalized["high"] = normalized["close"]
            if normalized["low"] == 0 and normalized["close"] > 0:
                normalized["low"] = normalized["close"]
            if normalized["open"] == 0 and normalized["close"] > 0:
                normalized["open"] = normalized["close"]
            cleaned.append(normalized)
        return cleaned

    def get_or_fetch(self, ticker, years=10):
        """try cache first, then fetch from yahoo if stale or missing."""
        cached = self.load_cached(ticker)
        if cached:
            return cached
        return self.generate_historical(ticker, years)


def generate_synthetic_bars(n=2520, start_price=100.0, seed=42, ticker="SYNTH"):
    """generate synthetic ohlcv data for testing without network access.

    creates a random walk with realistic price relationships.
    2520 bars = roughly 10 years of trading days.
    """
    import random
    random.seed(seed)
    bars = []
    price = start_price
    base_year = 2015
    trading_day = 0
    for i in range(n):
        year = base_year + trading_day // 252
        day_in_year = trading_day % 252
        month = day_in_year // 21 + 1
        if month > 12:
            month = 12
        dom = day_in_year % 21 + 1
        if dom > 28:
            dom = 28
        date_str = f"{year}-{month:02d}-{dom:02d}"
        drift = 0.0003
        volatility = 0.015
        change = (drift + random.gauss(0, volatility)) * price
        open_p = price
        close_p = price + change
        intraday_range = abs(random.gauss(0, 0.008)) * price
        high_p = max(open_p, close_p) + intraday_range
        low_p = min(open_p, close_p) - intraday_range
        if low_p < 0.01:
            low_p = 0.01
        base_vol = 1500000
        vol_noise = random.gauss(0, 400000)
        vol_spike = 1.0
        if abs(change / price) > 0.02:
            vol_spike = 1.5 + random.random()
        volume = max(100000, int((base_vol + vol_noise) * vol_spike))
        bars.append({
            "date": date_str,
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume,
        })
        price = close_p
        trading_day += 1
    return bars


if __name__ == "__main__":
    ds = DataSource()
    synth = generate_synthetic_bars(500, ticker="TEST")
    print(f"generated {len(synth)} synthetic bars")
    print(f"  first: {synth[0]['date']} ${synth[0]['close']:.2f}")
    print(f"  last:  {synth[-1]['date']} ${synth[-1]['close']:.2f}")
    ds.cache_data("test_synth", synth)
    loaded = ds.load_cached("test_synth")
    if loaded:
        print(f"  cache round-trip ok: {len(loaded)} bars")
    csv_test = ds.fetch_from_csv("/tmp/nonexistent.csv")
    print(f"  missing csv returns: {csv_test}")
    normalized = ds.normalize(synth[:3])
    print(f"  normalized sample: {normalized[0]}")
