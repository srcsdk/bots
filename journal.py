#!/usr/bin/env python3
"""trade journal with tagged entries and search"""

import json
import os
from datetime import datetime


JOURNAL_FILE = os.path.join(os.path.dirname(__file__), "trade_journal.json")


def load_journal():
    """load journal entries from file."""
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, "r") as f:
            return json.load(f)
    return []


def save_journal(entries):
    """save journal entries to file."""
    with open(JOURNAL_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def add_entry(ticker, action, price, shares, tags=None, notes=""):
    """add a new journal entry."""
    entries = load_journal()
    entry = {
        "id": len(entries) + 1,
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker.upper(),
        "action": action,
        "price": price,
        "shares": shares,
        "tags": tags or [],
        "notes": notes,
    }
    entries.append(entry)
    save_journal(entries)
    return entry


def search_by_tag(tag):
    """find all entries with a specific tag."""
    entries = load_journal()
    return [e for e in entries if tag in e.get("tags", [])]


def search_by_ticker(ticker):
    """find all entries for a ticker."""
    entries = load_journal()
    return [e for e in entries if e["ticker"] == ticker.upper()]


def search_by_date(start_date, end_date=None):
    """find entries within a date range."""
    entries = load_journal()
    if end_date is None:
        end_date = datetime.now().isoformat()
    return [
        e for e in entries
        if start_date <= e["timestamp"][:10] <= end_date[:10]
    ]


def journal_stats():
    """calculate journal statistics."""
    entries = load_journal()
    if not entries:
        return {}
    tickers = set(e["ticker"] for e in entries)
    all_tags = set()
    for e in entries:
        all_tags.update(e.get("tags", []))
    return {
        "total_entries": len(entries),
        "unique_tickers": len(tickers),
        "unique_tags": sorted(all_tags),
        "first_entry": entries[0]["timestamp"][:10],
        "last_entry": entries[-1]["timestamp"][:10],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python journal.py <add|search|stats>")
        print("  add <ticker> <buy|sell> <price> <shares> [tags] [notes]")
        print("  search <tag|ticker|date> <query>")
        print("  stats")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "stats":
        stats = journal_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
    elif cmd == "search" and len(sys.argv) >= 4:
        search_type = sys.argv[2]
        query = sys.argv[3]
        if search_type == "tag":
            results = search_by_tag(query)
        elif search_type == "ticker":
            results = search_by_ticker(query)
        else:
            results = search_by_date(query)
        print(f"found {len(results)} entries")
        for r in results:
            print(f"  {r['timestamp'][:10]} {r['action']} "
                  f"{r['shares']} {r['ticker']} @ ${r['price']}")
