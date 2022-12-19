#!/usr/bin/env python3
# updated: sector and market cap filters
"""watchlist management with persistent storage and batch scanning"""

import json
import os
import sys
from ohlc import fetch_ohlc
from indicators import rsi, macd, sma


WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")


def load_watchlist():
    """load watchlist from file"""
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    return {"lists": {"default": []}, "active": "default"}


def save_watchlist(data):
    """save watchlist to file"""
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_ticker(ticker, list_name="default"):
    """add a ticker to a watchlist"""
    data = load_watchlist()
    if list_name not in data["lists"]:
        data["lists"][list_name] = []
    ticker = ticker.upper()
    if ticker not in data["lists"][list_name]:
        data["lists"][list_name].append(ticker)
        save_watchlist(data)
    return data


def remove_ticker(ticker, list_name="default"):
    """remove a ticker from a watchlist"""
    data = load_watchlist()
    ticker = ticker.upper()
    if list_name in data["lists"] and ticker in data["lists"][list_name]:
        data["lists"][list_name].remove(ticker)
        save_watchlist(data)
    return data


def create_list(list_name):
    """create a new watchlist"""
    data = load_watchlist()
    if list_name not in data["lists"]:
        data["lists"][list_name] = []
        save_watchlist(data)
    return data


def get_active_tickers():
    """get tickers from the active watchlist"""
    data = load_watchlist()
    active = data.get("active", "default")
    return data["lists"].get(active, [])


def auto_refresh(watchlist, interval=300):
    """return a refresh schedule dict with last_updated timestamps.

    sets up a schedule for periodic watchlist data refresh.
    interval is in seconds (default 5 minutes).
    """
    import time
    now = time.time()
    tickers = watchlist.get("lists", {}).get(
        watchlist.get("active", "default"), []
    )
    schedule = {
        "interval": interval,
        "last_updated": now,
        "next_update": now + interval,
        "tickers": {t: {"last_updated": None} for t in tickers},
    }
    return schedule


def quick_snapshot(tickers):
    """get a quick snapshot of current indicators for tickers"""
    results = []
    for ticker in tickers:
        rows = fetch_ohlc(ticker, "3mo")
        if not rows or len(rows) < 30:
            continue

        closes = [r["close"] for r in rows]
        rsi_vals = rsi(closes, 14)
        _, _, hist = macd(closes)
        sma_20 = sma(closes, 20)

        current_rsi = rsi_vals[-1] if rsi_vals[-1] is not None else None
        current_macd = hist[-1] if hist[-1] is not None else None
        above_sma = closes[-1] > sma_20[-1] if sma_20[-1] is not None else None

        change_1d = round((closes[-1] - closes[-2]) / closes[-2] * 100, 2) if len(closes) > 1 else 0
        change_5d = round((closes[-1] - closes[-6]) / closes[-6] * 100, 2) if len(closes) > 5 else 0

        results.append({
            "ticker": ticker,
            "price": closes[-1],
            "change_1d": change_1d,
            "change_5d": change_5d,
            "rsi": round(current_rsi, 1) if current_rsi else None,
            "macd_hist": round(current_macd, 4) if current_macd else None,
            "above_sma20": above_sma,
            "date": rows[-1]["date"],
        })

    return results


def watchlist_report(list_name="default"):
    """generate a full report for a watchlist"""
    data = load_watchlist()
    tickers = data["lists"].get(list_name, [])
    if not tickers:
        return None
    return quick_snapshot(tickers)


def sort_by_signal(watchlist_items):
    """sort watchlist items by signal strength.

    items with rsi < 30 or > 70 score higher, macd histogram magnitude adds weight.
    returns sorted list with signal_strength field added.
    """
    scored = []
    for item in watchlist_items:
        strength = 0
        rsi_val = item.get("rsi")
        if rsi_val is not None:
            if rsi_val < 30:
                strength += (30 - rsi_val) / 30
            elif rsi_val > 70:
                strength += (rsi_val - 70) / 30
        macd_hist = item.get("macd_hist")
        if macd_hist is not None:
            strength += min(abs(macd_hist) * 100, 1.0)
        item["signal_strength"] = round(strength, 4)
        scored.append(item)
    scored.sort(key=lambda x: x["signal_strength"], reverse=True)
    return scored


if __name__ == "__main__":
    if len(sys.argv) < 2:
        data = load_watchlist()
        for name, tickers in data["lists"].items():
            active = " *" if name == data["active"] else ""
            print(f"  {name}{active}: {', '.join(tickers) if tickers else '(empty)'}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "add":
        ticker = sys.argv[2].upper()
        list_name = sys.argv[3] if len(sys.argv) > 3 else "default"
        add_ticker(ticker, list_name)
        print(f"added {ticker} to {list_name}")
    elif cmd == "remove":
        ticker = sys.argv[2].upper()
        remove_ticker(ticker)
        print(f"removed {ticker}")
    elif cmd == "create":
        create_list(sys.argv[2])
        print(f"created list: {sys.argv[2]}")
    elif cmd == "scan":
        list_name = sys.argv[2] if len(sys.argv) > 2 else "default"
        data = load_watchlist()
        tickers = data["lists"].get(list_name, [])
        if not tickers:
            print(f"no tickers in {list_name}")
            sys.exit(1)
        print(f"scanning {list_name} ({len(tickers)} tickers)...")
        results = quick_snapshot(tickers)
        print(f"\n{'ticker':<7} {'price':>8} {'1d%':>7} {'5d%':>7} "
              f"{'rsi':>5} {'macd':>8} {'>sma20'}")
        for r in results:
            rsi_str = f"{r['rsi']:.1f}" if r["rsi"] else "n/a"
            macd_str = f"{r['macd_hist']:.4f}" if r["macd_hist"] else "n/a"
            sma_str = "yes" if r["above_sma20"] else "no"
            print(f"{r['ticker']:<7} {r['price']:>8.2f} {r['change_1d']:>+6.2f}% "
                  f"{r['change_5d']:>+6.2f}% {rsi_str:>5} {macd_str:>8} {sma_str}")
