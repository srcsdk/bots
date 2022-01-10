#!/usr/bin/env python3
"""historical and live data feed for backtesting"""

import csv
import os
from datetime import datetime


def load_csv(filepath, date_col="date", ohlcv=None):
    """load ohlcv data from csv file.

    returns list of dicts with date, open, high, low, close, volume.
    """
    if ohlcv is None:
        ohlcv = ["open", "high", "low", "close", "volume"]
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {"date": row[date_col]}
            for col in ohlcv:
                if col in row:
                    entry[col] = float(row[col])
            rows.append(entry)
    return rows


def filter_date_range(data, start=None, end=None, date_col="date"):
    """filter data to date range (inclusive)."""
    filtered = []
    for row in data:
        d = row.get(date_col, "")
        if start and d < start:
            continue
        if end and d > end:
            continue
        filtered.append(row)
    return filtered


def normalize_volume(data, window=20):
    """add relative volume (vs rolling average)."""
    for i, row in enumerate(data):
        if i < window:
            row["rel_volume"] = 1.0
            continue
        avg_vol = sum(data[j]["volume"] for j in range(i - window, i)) / window
        row["rel_volume"] = round(row["volume"] / avg_vol, 2) if avg_vol > 0 else 0
    return data


def resample_to_weekly(data):
    """resample daily data to weekly bars."""
    weeks = {}
    for row in data:
        dt = datetime.strptime(row["date"], "%Y-%m-%d")
        week_start = dt.strftime("%Y-W%W")
        if week_start not in weeks:
            weeks[week_start] = {
                "date": row["date"], "open": row["open"],
                "high": row["high"], "low": row["low"],
                "close": row["close"], "volume": row["volume"],
            }
        else:
            w = weeks[week_start]
            w["high"] = max(w["high"], row["high"])
            w["low"] = min(w["low"], row["low"])
            w["close"] = row["close"]
            w["volume"] += row["volume"]
    return list(weeks.values())


def generate_random_data(symbol, days=252, start_price=100):
    """generate random ohlcv data for testing."""
    import random
    data = []
    price = start_price
    base_date = datetime(2021, 1, 4)
    for i in range(days):
        from datetime import timedelta
        dt = base_date + timedelta(days=i)
        if dt.weekday() >= 5:
            continue
        change = random.gauss(0.0003, 0.02)
        price *= (1 + change)
        high = price * (1 + abs(random.gauss(0, 0.005)))
        low = price * (1 - abs(random.gauss(0, 0.005)))
        data.append({
            "date": dt.strftime("%Y-%m-%d"),
            "symbol": symbol,
            "open": round(price * (1 + random.gauss(0, 0.002)), 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(price, 2),
            "volume": random.randint(500000, 5000000),
        })
    return data


if __name__ == "__main__":
    data = generate_random_data("TEST", 50)
    print(f"generated {len(data)} bars")
    filtered = filter_date_range(data, "2021-01-10", "2021-02-10")
    print(f"filtered: {len(filtered)} bars")
    data = normalize_volume(data)
    print(f"first bar rel_volume: {data[0]['rel_volume']}")
