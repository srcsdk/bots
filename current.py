#!/usr/bin/env python3
"""current: market data from official free apis"""

import json
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError


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
    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates?sort=-record_date&page[size]=5"
    data = fetch_json(url)
    if not data:
        return []
    return data.get("data", [])


def get_economic_calendar():
    """upcoming economic data releases"""
    releases = [
        {"name": "cpi", "desc": "consumer price index", "freq": "monthly"},
        {"name": "ppi", "desc": "producer price index", "freq": "monthly"},
        {"name": "nfp", "desc": "non-farm payrolls", "freq": "monthly"},
        {"name": "gdp", "desc": "gross domestic product", "freq": "quarterly"},
        {"name": "fomc", "desc": "fed rate decision", "freq": "8x/year"},
    ]
    return releases


if __name__ == "__main__":
    print("market data feed\n")

    print("treasury rates:")
    yields = get_treasury_yields()
    for y in yields[:3]:
        print(f"  {y.get('record_date', 'n/a')}: "
              f"{y.get('avg_interest_rate_amt', 'n/a')}%")

    print("\neconomic calendar:")
    for r in get_economic_calendar():
        print(f"  {r['name']:<12} {r['desc']:<30} ({r['freq']})")
