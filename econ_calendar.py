#!/usr/bin/env python3
"""economic calendar event parser for market data releases"""

import json
import os
from datetime import datetime


EVENTS_FILE = os.path.join(os.path.dirname(__file__), "econ_events.json")

RELEASE_TYPES = {
    "employment": ["nonfarm_payrolls", "unemployment_rate", "jobless_claims"],
    "inflation": ["cpi", "ppi", "pce"],
    "growth": ["gdp", "retail_sales", "industrial_production"],
    "housing": ["housing_starts", "existing_home_sales", "case_shiller"],
    "manufacturing": ["ism_manufacturing", "ism_services", "durable_goods"],
    "fed": ["fomc_minutes", "fed_funds_rate", "beige_book"],
}


def load_events():
    """load saved economic events from file."""
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "r") as f:
            return json.load(f)
    return []


def save_events(events):
    """save events to json file."""
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=2)


def classify_event(name):
    """classify an economic event by category."""
    name_lower = name.lower().replace(" ", "_")
    for category, items in RELEASE_TYPES.items():
        for item in items:
            if item in name_lower:
                return category
    return "other"


def impact_score(event):
    """estimate market impact score 1-10 based on event type and surprise."""
    base_scores = {
        "employment": 8, "inflation": 7, "growth": 6,
        "fed": 9, "housing": 4, "manufacturing": 5, "other": 3,
    }
    category = classify_event(event.get("name", ""))
    score = base_scores.get(category, 3)
    actual = event.get("actual")
    forecast = event.get("forecast")
    if actual is not None and forecast is not None and forecast != 0:
        surprise = abs(actual - forecast) / abs(forecast)
        if surprise > 0.1:
            score = min(10, score + 2)
        elif surprise > 0.05:
            score = min(10, score + 1)
    return score


def upcoming_events(events, after_date=None):
    """filter events occurring after a given date string (YYYY-MM-DD)."""
    if after_date is None:
        after_date = datetime.now().strftime("%Y-%m-%d")
    return [e for e in events if e.get("date", "") >= after_date]


def events_by_category(events):
    """group events by their category."""
    grouped = {}
    for event in events:
        cat = classify_event(event.get("name", ""))
        grouped.setdefault(cat, []).append(event)
    return grouped


def format_calendar(events, limit=20):
    """format events as a readable calendar string."""
    lines = []
    for e in events[:limit]:
        date = e.get("date", "unknown")
        name = e.get("name", "unknown")
        cat = classify_event(name)
        score = impact_score(e)
        lines.append(f"  {date} [{cat:>15}] {name} (impact: {score})")
    return "\n".join(lines)


if __name__ == "__main__":
    sample = [
        {"name": "Nonfarm Payrolls", "date": "2021-09-03", "forecast": 750, "actual": 235},
        {"name": "CPI", "date": "2021-09-14", "forecast": 5.3, "actual": 5.3},
        {"name": "FOMC Minutes", "date": "2021-09-22", "forecast": None, "actual": None},
        {"name": "GDP", "date": "2021-09-30", "forecast": 6.6, "actual": 6.7},
    ]
    print("economic calendar:")
    print(format_calendar(sample))
