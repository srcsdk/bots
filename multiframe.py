#!/usr/bin/env python3
"""multi-timeframe analysis: align signals across daily/weekly/monthly"""

import sys
from ohlc import fetch_ohlc
from indicators import rsi, macd, sma


def aggregate_weekly(daily_rows):
    """aggregate daily bars into weekly bars"""
    if not daily_rows:
        return []
    weeks = []
    current_week = None
    for row in daily_rows:
        week_start = row["date"][:8]
        if current_week is None or week_start != current_week["date"][:8]:
            if current_week is not None:
                weeks.append(current_week)
            current_week = {
                "date": row["date"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            }
        else:
            current_week["high"] = max(current_week["high"], row["high"])
            current_week["low"] = min(current_week["low"], row["low"])
            current_week["close"] = row["close"]
            current_week["volume"] += row["volume"]
    if current_week:
        weeks.append(current_week)
    return weeks


def aggregate_monthly(daily_rows):
    """aggregate daily bars into monthly bars"""
    if not daily_rows:
        return []
    months = []
    current_month = None
    current_key = None
    for row in daily_rows:
        month_key = row["date"][:7]
        if month_key != current_key:
            if current_month is not None:
                months.append(current_month)
            current_key = month_key
            current_month = {
                "date": row["date"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            }
        else:
            current_month["high"] = max(current_month["high"], row["high"])
            current_month["low"] = min(current_month["low"], row["low"])
            current_month["close"] = row["close"]
            current_month["volume"] += row["volume"]
    if current_month:
        months.append(current_month)
    return months


def timeframe_bias(rows, label=""):
    """determine trend bias from indicator readings.

    returns dict with trend direction and strength
    """
    if not rows or len(rows) < 30:
        return {"trend": "neutral", "strength": 0, "label": label}

    closes = [r["close"] for r in rows]
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    sma_20 = sma(closes, 20)

    current_rsi = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    current_hist = hist[-1] if hist[-1] is not None else 0
    above_sma = closes[-1] > sma_20[-1] if sma_20[-1] is not None else False

    score = 0
    if current_rsi > 60:
        score += 1
    elif current_rsi < 40:
        score -= 1
    if current_hist > 0:
        score += 1
    elif current_hist < 0:
        score -= 1
    if above_sma:
        score += 1
    else:
        score -= 1

    if score >= 2:
        trend = "bullish"
    elif score <= -2:
        trend = "bearish"
    else:
        trend = "neutral"

    return {
        "trend": trend,
        "strength": abs(score),
        "rsi": round(current_rsi, 1) if current_rsi else None,
        "macd_hist": round(current_hist, 4) if current_hist else None,
        "above_sma20": above_sma,
        "label": label,
    }


def weekly_monthly_alignment(daily_rows):
    """resample daily data to weekly/monthly and check trend alignment.

    returns dict with trend direction per timeframe and whether
    all timeframes agree on direction.
    """
    if not daily_rows or len(daily_rows) < 30:
        return {"aligned": False, "direction": "neutral"}

    weekly = aggregate_weekly(daily_rows)
    monthly = aggregate_monthly(daily_rows)

    def trend_direction(rows):
        if len(rows) < 2:
            return "neutral"
        closes = [r["close"] for r in rows]
        sma_vals = sma(closes, min(10, len(closes)))
        last_sma = sma_vals[-1]
        if last_sma is None:
            return "neutral"
        if closes[-1] > last_sma:
            return "bullish"
        elif closes[-1] < last_sma:
            return "bearish"
        return "neutral"

    d_trend = trend_direction(daily_rows)
    w_trend = trend_direction(weekly)
    m_trend = trend_direction(monthly)

    aligned = (d_trend == w_trend == m_trend and d_trend != "neutral")
    return {
        "daily": d_trend,
        "weekly": w_trend,
        "monthly": m_trend,
        "aligned": aligned,
        "direction": d_trend if aligned else "mixed",
    }


def multi_timeframe_analysis(ticker, period="2y"):
    """analyze a ticker across daily, weekly, and monthly timeframes.

    returns alignment status and individual timeframe readings
    """
    daily = fetch_ohlc(ticker, period)
    if not daily or len(daily) < 60:
        return None

    weekly = aggregate_weekly(daily)
    monthly = aggregate_monthly(daily)

    daily_bias = timeframe_bias(daily, "daily")
    weekly_bias = timeframe_bias(weekly, "weekly")
    monthly_bias = timeframe_bias(monthly, "monthly")

    trends = [daily_bias["trend"], weekly_bias["trend"], monthly_bias["trend"]]
    bullish = trends.count("bullish")
    bearish = trends.count("bearish")

    if bullish == 3:
        alignment = "strong bullish"
    elif bearish == 3:
        alignment = "strong bearish"
    elif bullish >= 2:
        alignment = "bullish"
    elif bearish >= 2:
        alignment = "bearish"
    else:
        alignment = "mixed"

    return {
        "ticker": ticker,
        "alignment": alignment,
        "daily": daily_bias,
        "weekly": weekly_bias,
        "monthly": monthly_bias,
        "last_close": daily[-1]["close"],
        "last_date": daily[-1]["date"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python multiframe.py <ticker> [ticker2] ...")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    for ticker in tickers:
        result = multi_timeframe_analysis(ticker)
        if result is None:
            print(f"{ticker}: insufficient data")
            continue
        print(f"\n{ticker} ${result['last_close']:.2f} ({result['last_date']})")
        print(f"  alignment: {result['alignment']}")
        for tf in ["daily", "weekly", "monthly"]:
            bias = result[tf]
            print(f"  {tf:<8} {bias['trend']:<8} "
                  f"rsi={bias['rsi']}  macd={bias['macd_hist']}  "
                  f"above_sma20={bias['above_sma20']}")
