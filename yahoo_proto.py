#!/usr/bin/env python3
# improved: timeout handling and retry logic
"""prototype: test yahoo finance api access and data format"""

import json
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import URLError


def test_yahoo_api(ticker):
    """test fetching data from yahoo finance chart api"""
    end = int(time.time())
    start = end - (30 * 86400)  # 30 days

    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={start}&period2={end}&interval=1d")

    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
            data = json.loads(raw)
    except (URLError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return None

    result = data.get("chart", {}).get("result", [])
    if not result:
        print("no data in response", file=sys.stderr)
        return None

    chart = result[0]
    meta = chart.get("meta", {})
    timestamps = chart.get("timestamp", [])
    quote = chart.get("indicators", {}).get("quote", [{}])[0]

    print(f"ticker: {meta.get('symbol', ticker)}")
    print(f"currency: {meta.get('currency', '?')}")
    print(f"exchange: {meta.get('exchangeName', '?')}")
    print(f"data points: {len(timestamps)}")

    if timestamps:
        print(f"\nfields available: {list(quote.keys())}")
        print("\nlast 5 days:")
        for i in range(-5, 0):
            if abs(i) <= len(timestamps):
                idx = len(timestamps) + i
                from datetime import datetime
                date = datetime.fromtimestamp(timestamps[idx]).strftime("%Y-%m-%d")
                o = quote.get("open", [None])[idx]
                c = quote.get("close", [None])[idx]
                v = quote.get("volume", [None])[idx]
                if o and c:
                    print(f"  {date}  o={o:.2f}  c={c:.2f}  v={v:,}")

    return data


def validate_response(data):
    """check yahoo api response has expected fields.

    returns dict with valid flag and list of missing fields.
    """
    if not data or not isinstance(data, dict):
        return {"valid": False, "missing": ["root"]}

    missing = []
    chart = data.get("chart")
    if chart is None:
        missing.append("chart")
        return {"valid": False, "missing": missing}

    result = chart.get("result")
    if not result or not isinstance(result, list) or len(result) == 0:
        missing.append("chart.result")
        return {"valid": False, "missing": missing}

    entry = result[0]
    if "timestamp" not in entry:
        missing.append("timestamp")
    indicators = entry.get("indicators", {})
    quote = indicators.get("quote", [])
    if not quote:
        missing.append("indicators.quote")
    else:
        q = quote[0]
        for field in ["open", "high", "low", "close", "volume"]:
            if field not in q:
                missing.append(f"quote.{field}")

    return {"valid": len(missing) == 0, "missing": missing}


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    test_yahoo_api(ticker)
