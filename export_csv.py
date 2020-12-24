#!/usr/bin/env python3
"""export ohlc price data to csv files"""

import csv
import os
import sys
from datetime import datetime


def export_to_csv(rows, filename, include_header=True):
    """write ohlc data rows to a csv file.

    rows: list of dicts with date, open, high, low, close, volume
    """
    if not rows:
        print("no data to export", file=sys.stderr)
        return False

    fieldnames = ["date", "open", "high", "low", "close", "volume"]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames,
                                extrasaction="ignore")
        if include_header:
            writer.writeheader()
        writer.writerows(rows)

    print(f"exported {len(rows)} rows to {filename}")
    return True


def export_multiple(ticker_data, output_dir):
    """export data for multiple tickers to separate csv files.

    ticker_data: dict of {ticker: [rows]}
    """
    os.makedirs(output_dir, exist_ok=True)

    for ticker, rows in ticker_data.items():
        filename = os.path.join(output_dir, f"{ticker.lower()}.csv")
        export_to_csv(rows, filename)


def append_to_csv(rows, filename):
    """append new rows to an existing csv file.

    skips rows with dates already present in the file.
    """
    existing_dates = set()
    if os.path.exists(filename):
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_dates.add(row.get("date", ""))

    new_rows = [r for r in rows if r.get("date", "") not in existing_dates]
    if not new_rows:
        print("no new rows to append")
        return 0

    write_header = not os.path.exists(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["date", "open", "high", "low", "close", "volume"],
            extrasaction="ignore"
        )
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"appended {len(new_rows)} new rows to {filename}")
    return len(new_rows)


if __name__ == "__main__":
    from ohlc import fetch_ohlc

    ticker = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    period = sys.argv[2] if len(sys.argv) > 2 else "6mo"

    rows = fetch_ohlc(ticker, period)
    if rows:
        filename = f"data/{ticker.lower()}_{period}.csv"
        os.makedirs("data", exist_ok=True)
        export_to_csv(rows, filename)
