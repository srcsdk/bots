#!/usr/bin/env python3
"""price adjustment for splits and dividends in historical data"""


def adjust_for_split(data, split_date, ratio):
    """adjust historical prices for stock split.

    adjusts all prices before split_date by 1/ratio.
    """
    adjusted = []
    for bar in data:
        if bar["date"] < split_date:
            adjusted.append({
                "date": bar["date"],
                "open": round(bar["open"] / ratio, 4),
                "high": round(bar["high"] / ratio, 4),
                "low": round(bar["low"] / ratio, 4),
                "close": round(bar["close"] / ratio, 4),
                "volume": int(bar["volume"] * ratio),
            })
        else:
            adjusted.append(dict(bar))
    return adjusted


def adjust_for_dividend(data, ex_date, dividend):
    """adjust historical prices for dividend.

    subtracts dividend from all prices before ex-date.
    """
    adjusted = []
    for bar in data:
        if bar["date"] < ex_date:
            factor = 1 - dividend / bar["close"]
            adjusted.append({
                "date": bar["date"],
                "open": round(bar["open"] * factor, 4),
                "high": round(bar["high"] * factor, 4),
                "low": round(bar["low"] * factor, 4),
                "close": round(bar["close"] * factor, 4),
                "volume": bar["volume"],
            })
        else:
            adjusted.append(dict(bar))
    return adjusted


def apply_adjustments(data, events):
    """apply multiple adjustment events chronologically.

    events: list of {"type": "split"/"dividend", "date": ..., ...}.
    """
    result = list(data)
    for event in sorted(events, key=lambda e: e["date"], reverse=True):
        if event["type"] == "split":
            result = adjust_for_split(result, event["date"], event["ratio"])
        elif event["type"] == "dividend":
            result = adjust_for_dividend(result, event["date"], event["amount"])
    return result


if __name__ == "__main__":
    data = [
        {"date": "2022-01-03", "open": 400, "high": 410, "low": 395, "close": 405, "volume": 1000000},
        {"date": "2022-01-04", "open": 405, "high": 415, "low": 400, "close": 410, "volume": 1200000},
        {"date": "2022-01-10", "open": 100, "high": 105, "low": 98, "close": 103, "volume": 4000000},
    ]
    adjusted = adjust_for_split(data, "2022-01-10", 4)
    print("split-adjusted:")
    for bar in adjusted:
        print(f"  {bar['date']}: close={bar['close']} vol={bar['volume']}")
