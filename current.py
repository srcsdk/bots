#!/usr/bin/env python3
"""current: market data from official free apis"""

import json
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError


def safe_request(url, timeout=10):
    """wrapper around urllib that catches exceptions and returns None on failure"""
    req = Request(url, headers={"User-Agent": "market-scanner/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, OSError, ValueError):
        return None


FRED_BASE = "https://api.stlouisfed.org/fred"
SEC_BASE = "https://efts.sec.gov/LATEST/search-index"


def fetch_json(url, timeout=15):
    req = Request(url, headers={"User-Agent": "market-scanner/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (URLError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return None


def get_treasury_yields():
    """10yr treasury yield from treasury.gov"""
    url = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
           "/v2/accounting/od/avg_interest_rates?sort=-record_date&page[size]=5")
    data = fetch_json(url)
    if not data:
        return []
    return data.get("data", [])


def get_sec_filings(ticker, filing_type="10-K"):
    """recent sec filings for a company"""
    url = (f"https://efts.sec.gov/LATEST/search-index?"
           f"q=%22{ticker}%22&dateRange=custom"
           f"&forms={filing_type}&from=0&size=10")
    data = fetch_json(url)
    if not data:
        return []
    hits = data.get("hits", {}).get("hits", [])
    return [
        {
            "date": h.get("_source", {}).get("file_date", ""),
            "form": h.get("_source", {}).get("form_type", ""),
            "company": h.get("_source", {}).get("display_names", [""])[0],
        }
        for h in hits
    ]


def get_economic_calendar():
    """upcoming economic data releases"""
    releases = [
        {"name": "cpi", "desc": "consumer price index", "freq": "monthly"},
        {"name": "ppi", "desc": "producer price index", "freq": "monthly"},
        {"name": "nfp", "desc": "non-farm payrolls", "freq": "monthly"},
        {"name": "gdp", "desc": "gross domestic product", "freq": "quarterly"},
        {"name": "fomc", "desc": "fed rate decision", "freq": "8x/year"},
        {"name": "ism_mfg", "desc": "ism manufacturing", "freq": "monthly"},
        {"name": "retail", "desc": "retail sales", "freq": "monthly"},
        {"name": "housing", "desc": "housing starts", "freq": "monthly"},
        {"name": "claims", "desc": "initial jobless claims", "freq": "weekly"},
    ]
    return releases


def get_fear_greed():
    """cnn fear and greed index approximation from vix"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range=5d&interval=1d"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        vix = closes[-1] if closes else None
        if vix is None:
            return None
        if vix < 15:
            sentiment = "extreme greed"
        elif vix < 20:
            sentiment = "greed"
        elif vix < 25:
            sentiment = "neutral"
        elif vix < 30:
            sentiment = "fear"
        else:
            sentiment = "extreme fear"
        return {"vix": round(vix, 2), "sentiment": sentiment}
    except (URLError, json.JSONDecodeError, KeyError):
        return None


if __name__ == "__main__":
    print("market data feed\n")

    print("fear/greed (vix-based):")
    fg = get_fear_greed()
    if fg:
        print(f"  vix: {fg['vix']} ({fg['sentiment']})")

    print("\ntreasury rates:")
    yields = get_treasury_yields()
    for y in yields[:3]:
        print(f"  {y.get('record_date', 'n/a')}: "
              f"{y.get('avg_interest_rate_amt', 'n/a')}%")

    print("\neconomic calendar:")
    for r in get_economic_calendar():
        print(f"  {r['name']:<12} {r['desc']:<30} ({r['freq']})")

    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        print(f"\nsec filings for {ticker}:")
        filings = get_sec_filings(ticker)
        for f in filings[:5]:
            print(f"  {f['date']} {f['form']} {f['company']}")
