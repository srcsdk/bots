#!/usr/bin/env python3
"""alert system with configurable thresholds and conditions"""

import json
import os
import sys
import time
from ohlc import fetch_ohlc
from indicators import rsi, macd, sma, bollinger_bands


ALERTS_FILE = os.path.join(os.path.dirname(__file__), "alerts.json")
ALERT_LOG_FILE = os.path.join(os.path.dirname(__file__), "alert_log.json")


def load_alert_log():
    """load alert fire history from log file"""
    if os.path.exists(ALERT_LOG_FILE):
        with open(ALERT_LOG_FILE, "r") as f:
            return json.load(f)
    return []


def load_alerts():
    """load saved alerts from file"""
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    return []


def save_alerts(alerts):
    """save alerts to file"""
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def create_alert(ticker, condition, value, comparison="below"):
    """create a new price/indicator alert.

    condition: price, rsi, macd, sma20, bb_upper, bb_lower
    comparison: above, below, cross_above, cross_below
    """
    alert = {
        "ticker": ticker.upper(),
        "condition": condition,
        "value": value,
        "comparison": comparison,
        "active": True,
        "triggered": False,
    }
    alerts = load_alerts()
    alerts.append(alert)
    save_alerts(alerts)
    return alert


def check_condition(current, previous, target, comparison):
    """check if an alert condition is met"""
    if current is None:
        return False
    if comparison == "above":
        return current >= target
    elif comparison == "below":
        return current <= target
    elif comparison == "cross_above":
        return previous is not None and previous < target and current >= target
    elif comparison == "cross_below":
        return previous is not None and previous > target and current <= target
    return False


def evaluate_alert(alert, rows):
    """evaluate a single alert against current data"""
    if not rows or len(rows) < 30:
        return False

    closes = [r["close"] for r in rows]
    condition = alert["condition"]
    target = alert["value"]
    comp = alert["comparison"]

    if condition == "price":
        current = closes[-1]
        previous = closes[-2] if len(closes) > 1 else None
    elif condition == "rsi":
        vals = rsi(closes, 14)
        current = vals[-1]
        previous = vals[-2] if len(vals) > 1 else None
    elif condition == "macd":
        _, _, hist = macd(closes)
        current = hist[-1]
        previous = hist[-2] if len(hist) > 1 else None
    elif condition == "sma20":
        vals = sma(closes, 20)
        current = closes[-1] - vals[-1] if vals[-1] is not None else None
        previous = closes[-2] - vals[-2] if len(vals) > 1 and vals[-2] is not None else None
        target = 0
    elif condition == "bb_upper":
        _, bb_u, _ = bollinger_bands(closes)
        current = closes[-1]
        previous = closes[-2] if len(closes) > 1 else None
        target = bb_u[-1] if bb_u[-1] is not None else target
    elif condition == "bb_lower":
        _, _, bb_l = bollinger_bands(closes)
        current = closes[-1]
        previous = closes[-2] if len(closes) > 1 else None
        target = bb_l[-1] if bb_l[-1] is not None else target
    else:
        return False

    return check_condition(current, previous, target, comp)


def export_alerts_json(alerts, filepath):
    """write alert history to a json file.

    exports all alerts including triggered and inactive ones.
    """
    with open(filepath, "w") as f:
        json.dump(alerts, f, indent=2)
    return len(alerts)


def ma_crossover_alert(ticker, fast=10, slow=30):
    """check for moving average crossover conditions.

    returns dict with crossover type if detected, none otherwise.
    """
    rows = fetch_ohlc(ticker, "3mo")
    if not rows or len(rows) < slow + 2:
        return None

    closes = [r["close"] for r in rows]
    fast_ma = sma(closes, fast)
    slow_ma = sma(closes, slow)

    curr_fast = fast_ma[-1]
    curr_slow = slow_ma[-1]
    prev_fast = fast_ma[-2]
    prev_slow = slow_ma[-2]

    if any(v is None for v in [curr_fast, curr_slow, prev_fast, prev_slow]):
        return None

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return {"ticker": ticker, "type": "golden_cross",
                "fast": fast, "slow": slow, "date": rows[-1]["date"]}
    elif prev_fast >= prev_slow and curr_fast < curr_slow:
        return {"ticker": ticker, "type": "death_cross",
                "fast": fast, "slow": slow, "date": rows[-1]["date"]}

    return None


def check_alerts():
    """check all active alerts and return triggered ones"""
    alerts = load_alerts()
    triggered = []

    for alert in alerts:
        if not alert["active"] or alert["triggered"]:
            continue
        rows = fetch_ohlc(alert["ticker"], "3mo")
        if evaluate_alert(alert, rows):
            alert["triggered"] = True
            alert["active"] = False
            triggered.append(alert)

    save_alerts(alerts)
    return triggered


def monitor(interval=300):
    """continuously monitor alerts at specified interval (seconds)"""
    print(f"monitoring alerts every {interval}s... (ctrl+c to stop)")
    while True:
        triggered = check_alerts()
        for t in triggered:
            print(f"  ALERT: {t['ticker']} {t['condition']} "
                  f"{t['comparison']} {t['value']}")
        active = [a for a in load_alerts() if a["active"]]
        print(f"  {len(active)} active alerts, {len(triggered)} triggered")
        time.sleep(interval)


def alert_cooldown(ticker, alert_type, cooldown_mins=60):
    """check if an alert is in cooldown period to prevent duplicates.

    reads recent alerts from log and returns True if safe to fire.
    """
    log = load_alert_log()
    now = time.time()
    cooldown_secs = cooldown_mins * 60
    for entry in reversed(log):
        if entry.get("ticker") != ticker:
            continue
        if entry.get("type") != alert_type:
            continue
        fired_at = entry.get("timestamp", 0)
        if now - fired_at < cooldown_secs:
            return False
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage:")
        print("  alerts.py add <ticker> <condition> <value> [comparison]")
        print("  alerts.py check")
        print("  alerts.py list")
        print("  alerts.py monitor [interval_sec]")
        print("  conditions: price, rsi, macd, sma20, bb_upper, bb_lower")
        print("  comparisons: above, below, cross_above, cross_below")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "add":
        ticker = sys.argv[2].upper()
        condition = sys.argv[3]
        value = float(sys.argv[4])
        comp = sys.argv[5] if len(sys.argv) > 5 else "below"
        alert = create_alert(ticker, condition, value, comp)
        print(f"alert created: {ticker} {condition} {comp} {value}")
    elif cmd == "check":
        triggered = check_alerts()
        if triggered:
            for t in triggered:
                print(f"  TRIGGERED: {t['ticker']} {t['condition']} "
                      f"{t['comparison']} {t['value']}")
        else:
            print("no alerts triggered")
    elif cmd == "list":
        alerts = load_alerts()
        for a in alerts:
            status = "active" if a["active"] else ("triggered" if a["triggered"] else "inactive")
            print(f"  {a['ticker']:<6} {a['condition']:<10} "
                  f"{a['comparison']:<13} {a['value']:>8}  [{status}]")
    elif cmd == "monitor":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        monitor(interval)
