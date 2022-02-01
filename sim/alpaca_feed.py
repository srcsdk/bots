#!/usr/bin/env python3
"""alpaca api data provider for minute and daily bars"""

import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError


ALPACA_BASE = "https://data.alpaca.markets/v2"
ALPACA_PAPER = "https://paper-api.alpaca.markets/v2"


def get_credentials():
    """load alpaca api credentials from environment."""
    return {
        "key": os.environ.get("APCA_API_KEY_ID", ""),
        "secret": os.environ.get("APCA_API_SECRET_KEY", ""),
    }


def _api_request(url, creds=None):
    """make authenticated request to alpaca api."""
    if creds is None:
        creds = get_credentials()
    headers = {
        "APCA-API-KEY-ID": creds["key"],
        "APCA-API-SECRET-KEY": creds["secret"],
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError) as e:
        return {"error": str(e)}


def get_bars(symbol, timeframe="1Day", start=None, end=None, limit=1000):
    """fetch historical bars from alpaca."""
    params = f"?timeframe={timeframe}&limit={limit}"
    if start:
        params += f"&start={start}"
    if end:
        params += f"&end={end}"
    url = f"{ALPACA_BASE}/stocks/{symbol}/bars{params}"
    return _api_request(url)


def get_account():
    """get paper trading account info."""
    url = f"{ALPACA_PAPER}/account"
    return _api_request(url)


def get_positions():
    """get current paper trading positions."""
    url = f"{ALPACA_PAPER}/positions"
    return _api_request(url)


def bars_to_ohlcv(response, symbol=None):
    """convert alpaca bars response to standard ohlcv format."""
    bars = response.get("bars", [])
    if not bars:
        return []
    result = []
    for bar in bars:
        entry = {
            "date": bar.get("t", "")[:10],
            "open": bar.get("o", 0),
            "high": bar.get("h", 0),
            "low": bar.get("l", 0),
            "close": bar.get("c", 0),
            "volume": bar.get("v", 0),
        }
        if symbol:
            entry["symbol"] = symbol
        result.append(entry)
    return result


if __name__ == "__main__":
    creds = get_credentials()
    if creds["key"]:
        print("alpaca credentials found")
    else:
        print("set APCA_API_KEY_ID and APCA_API_SECRET_KEY env vars")
    print(f"data endpoint: {ALPACA_BASE}")
    print(f"paper endpoint: {ALPACA_PAPER}")
