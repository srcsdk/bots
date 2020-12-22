#!/usr/bin/env python3
"""fetch ohlc data from yahoo finance"""

import csv
import json
import sys
import time
from datetime import datetime, timedelta
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
        l = quote.get("low", [None])[i]
        c = quote.get("close", [None])[i]
        v = quote.get("volume", [None])[i]

        if None in (o, h, l, c):
            continue

        rows.append({
            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
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
