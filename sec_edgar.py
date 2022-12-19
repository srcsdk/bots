#!/usr/bin/env python3
"""sec edgar filing scraper for insider trades"""

import json
import os
import re

from urllib.request import urlopen, Request


SEC_BASE = "https://efts.sec.gov/LATEST/search-index"
HEADERS = {"User-Agent": "research-bot/1.0 research@example.com"}
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".sec_cache")


def fetch_filings(ticker, filing_type="4", count=20):
    """fetch recent sec filings for a ticker.

    filing_type 4 = insider transactions.
    returns list of filing metadata dicts.
    """
    url = (
        f"https://efts.sec.gov/LATEST/search-index?"
        f"q={ticker}&dateRange=custom&startdt=2020-01-01"
        f"&forms={filing_type}&hits.hits.total={count}"
    )
    try:
        req = Request(url, headers=HEADERS)
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get("hits", {}).get("hits", [])
    except (OSError, json.JSONDecodeError, KeyError):
        return []


def parse_form4(filing_text):
    """extract insider transaction details from form 4 text.

    returns dict with insider name, title, transaction type, shares, price.
    """
    result = {
        "insider": "",
        "title": "",
        "transaction_type": "",
        "shares": 0,
        "price": 0.0,
        "date": "",
    }
    name_match = re.search(r"REPORTING-OWNER.*?NAME.*?>(.*?)<", filing_text, re.DOTALL)
    if name_match:
        result["insider"] = name_match.group(1).strip()
    title_match = re.search(r"officerTitle>(.*?)<", filing_text)
    if title_match:
        result["title"] = title_match.group(1).strip()
    shares_match = re.search(r"sharesOwnedFollowingTransaction.*?value>(\d+)", filing_text)
    if shares_match:
        result["shares"] = int(shares_match.group(1))
    price_match = re.search(r"transactionPricePerShare.*?value>([\d.]+)", filing_text)
    if price_match:
        result["price"] = float(price_match.group(1))
    return result


def insider_summary(transactions):
    """summarize insider trading activity.

    returns dict with buy/sell counts, total value, net shares.
    """
    buys = [t for t in transactions if t.get("transaction_type") == "P"]
    sells = [t for t in transactions if t.get("transaction_type") == "S"]
    buy_value = sum(t.get("shares", 0) * t.get("price", 0) for t in buys)
    sell_value = sum(t.get("shares", 0) * t.get("price", 0) for t in sells)
    return {
        "total_transactions": len(transactions),
        "buys": len(buys),
        "sells": len(sells),
        "buy_value": round(buy_value, 2),
        "sell_value": round(sell_value, 2),
        "net_value": round(buy_value - sell_value, 2),
        "sentiment": "bullish" if buy_value > sell_value else "bearish",
    }


def cache_filing(ticker, filing_id, data):
    """cache a filing locally to avoid repeated requests."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{ticker}_{filing_id}.json")
    with open(path, "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
    print(f"sec edgar insider activity: {ticker}")
    sample = [
        {"insider": "Tim Cook", "transaction_type": "S", "shares": 50000, "price": 150.0},
        {"insider": "Luca Maestri", "transaction_type": "S", "shares": 20000, "price": 148.5},
        {"insider": "Deirdre O Brien", "transaction_type": "P", "shares": 5000, "price": 142.0},
    ]
    summary = insider_summary(sample)
    for k, v in summary.items():
        print(f"  {k}: {v}")
