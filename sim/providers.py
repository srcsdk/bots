#!/usr/bin/env python3
"""data providers for historical price data"""

import csv
import os


def fetch_yahoo_csv(symbol, period="1y"):
    """fetch historical data from yahoo finance csv endpoint.

    note: yahoo may rate limit or change endpoints.
    this provides the url pattern for manual download.
    """
    periods = {"1mo": 2592000, "3mo": 7776000, "6mo": 15552000, "1y": 31536000}
    import time
    end = int(time.time())
    start = end - periods.get(period, 31536000)
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
        f"?period1={start}&period2={end}&interval=1d"
    )
    return {"url": url, "symbol": symbol, "period": period}


def load_local_csv(filepath, symbol=None):
    """load price data from local csv file."""
    if not os.path.exists(filepath):
        return []
    rows = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                "date": row.get("Date", row.get("date", "")),
                "open": _safe_float(row.get("Open", row.get("open"))),
                "high": _safe_float(row.get("High", row.get("high"))),
                "low": _safe_float(row.get("Low", row.get("low"))),
                "close": _safe_float(row.get("Close", row.get("close"))),
                "volume": _safe_float(row.get("Volume", row.get("volume"))),
            }
            if symbol:
                entry["symbol"] = symbol
            rows.append(entry)
    return rows


def save_data(data, filepath):
    """save price data to csv."""
    if not data:
        return
    fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def merge_datasets(existing, new_data, date_col="date"):
    """merge two datasets, deduplicating by date."""
    dates = {row[date_col] for row in existing}
    merged = list(existing)
    for row in new_data:
        if row[date_col] not in dates:
            merged.append(row)
            dates.add(row[date_col])
    merged.sort(key=lambda r: r[date_col])
    return merged


def _safe_float(val):
    """convert value to float, returning 0 on failure."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    info = fetch_yahoo_csv("AAPL", "1y")
    print(f"yahoo url for {info['symbol']}:")
    print(f"  {info['url']}")
