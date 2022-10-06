#!/usr/bin/env python3
"""fetch ohlc data from yahoo finance"""

import csv
import json
import sys
import time
import os
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError


def fetch_ohlc(ticker, period="1y", interval="1d"):
    """fetch ohlc data for a ticker from yahoo finance"""
    periods = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = periods.get(period, 365)

    end = int(time.time())
    start = end - (days * 86400)

    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={start}&period2={end}&interval={interval}")

    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (URLError, json.JSONDecodeError) as e:
        print(f"error fetching {ticker}: {e}", file=sys.stderr)
        return None

    result = data.get("chart", {}).get("result", [])
    if not result:
        return None

    chart = result[0]
    timestamps = chart.get("timestamp", [])
    quote = chart.get("indicators", {}).get("quote", [{}])[0]

    rows = []
    for i, ts in enumerate(timestamps):
        o = quote.get("open", [None])[i]
        h = quote.get("high", [None])[i]
        low = quote.get("low", [None])[i]
        c = quote.get("close", [None])[i]
        v = quote.get("volume", [None])[i]

        if None in (o, h, low, c):
            continue

        rows.append({
            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(low, 2),
            "close": round(c, 2),
            "volume": v or 0,
        })

    return rows


def save_csv(rows, filename):
    """save ohlc data to csv"""
    if not rows:
        return
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def save_json(rows, filename):
    """save ohlc data to json"""
    with open(filename, "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python ohlc.py <ticker> [period] [interval]")
        print("  period: 1mo, 3mo, 6mo, 1y, 2y, 5y")
        print("  interval: 1d, 1wk, 1mo")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    period = sys.argv[2] if len(sys.argv) > 2 else "1y"
    interval = sys.argv[3] if len(sys.argv) > 3 else "1d"

    print(f"fetching {ticker} ({period}, {interval})...")
    rows = fetch_ohlc(ticker, period, interval)

    if not rows:
        print("no data", file=sys.stderr)
        sys.exit(1)

    print(f"{'date':<12} {'open':>8} {'high':>8} {'low':>8} {'close':>8} {'volume':>12}")
    for r in rows[-10:]:
        print(f"{r['date']:<12} {r['open']:>8.2f} {r['high']:>8.2f} "
              f"{r['low']:>8.2f} {r['close']:>8.2f} {r['volume']:>12,}")

    print(f"\n{len(rows)} rows ({rows[0]['date']} to {rows[-1]['date']})")


_fetch_cache = {}


def cached_fetch(ticker, period, ttl=3600):
    """fetch ohlc data with in-memory cache and ttl expiry.

    caches results keyed by ticker+period, expires after ttl seconds.
    """
    key = f"{ticker}_{period}"
    now = time.time()
    if key in _fetch_cache:
        cached_time, cached_data = _fetch_cache[key]
        if now - cached_time < ttl:
            return cached_data
    rows = fetch_ohlc(ticker, period)
    if rows:
        _fetch_cache[key] = (now, rows)
    return rows


def fetch_intraday(ticker, interval="5m"):
    """fetch intraday ohlc data from yahoo finance.

    uses the same yahoo finance api with shorter intervals.
    valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m.
    intraday data limited to last 7 days by yahoo.
    """
    valid = {"1m", "2m", "5m", "15m", "30m", "60m", "90m"}
    if interval not in valid:
        interval = "5m"
    end = int(time.time())
    start = end - (7 * 86400)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={start}&period2={end}&interval={interval}"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, KeyError):
        return []
    result = data.get("chart", {}).get("result", [])
    if not result:
        return []
    timestamps = result[0].get("timestamp", [])
    quote = result[0].get("indicators", {}).get("quote", [{}])[0]
    rows = []
    for i, ts in enumerate(timestamps):
        o = quote.get("open", [None] * len(timestamps))[i]
        h = quote.get("high", [None] * len(timestamps))[i]
        low = quote.get("low", [None] * len(timestamps))[i]
        c = quote.get("close", [None] * len(timestamps))[i]
        v = quote.get("volume", [None] * len(timestamps))[i]
        if None in (o, h, low, c):
            continue
        rows.append({
            "datetime": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "open": round(o, 4),
            "high": round(h, 4),
            "low": round(low, 4),
            "close": round(c, 4),
            "volume": v or 0,
        })
    return rows


def cache_path(ticker, period, interval):
    """get cache file path for a ticker"""
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{ticker}_{period}_{interval}.json")


def fetch_cached(ticker, period="1y", interval="1d", max_age=3600):
    """fetch ohlc data with local file caching"""
    path = cache_path(ticker, period, interval)
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < max_age:
            with open(path, "r") as f:
                return json.load(f)
    rows = fetch_ohlc(ticker, period, interval)
    if rows:
        save_json(rows, path)
    return rows
