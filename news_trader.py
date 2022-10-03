#!/usr/bin/env python3
"""news-driven trading strategy using newk sentiment feed.

reads ticker sentiment from newk research pipeline and generates
trade signals based on conviction levels and sentiment momentum.
combines headline sentiment with price confirmation for entries.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ohlc import fetch_ohlc  # noqa: E402
from indicators import sma, rsi  # noqa: E402


NEWK_DATA_DIR = os.path.expanduser("~/src/newk/data")

CONVICTION_THRESHOLDS = {
    "strong_entry": 0.6,
    "entry": 0.3,
    "lean": 0.1,
    "exit_reversal": -0.2,
}

DEFAULT_POSITION_SCALE = {
    3: 1.0,
    2: 0.7,
    1: 0.4,
    -1: 0.0,
    -2: 0.0,
    -3: 0.0,
}


def load_newk_sentiment(ticker, data_dir=None):
    """load cached sentiment data from newk for a ticker.

    reads from newk data directory where ticker_sentiment results
    are stored as json. returns list of daily sentiment entries.
    """
    base = data_dir or NEWK_DATA_DIR
    paths = [
        os.path.join(base, "sentiment", f"{ticker}.json"),
        os.path.join(base, f"ticker_sentiment_{ticker}.json"),
        os.path.join(base, "sentiment.json"),
    ]

    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict) and ticker in data:
                return data[ticker]
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, IOError):
            continue

    return []


def sentiment_to_signal(sentiment_entries, lookback=5):
    """convert sentiment entries to daily trading signals.

    aggregates recent sentiment scores and computes momentum.
    returns dict mapping date -> signal dict.
    """
    if not sentiment_entries:
        return {}

    signals = {}
    scores = []

    for entry in sentiment_entries:
        date = entry.get("date", "")
        score = entry.get("score", entry.get("avg_score", 0))
        tier = entry.get("tier", 0)

        if not date:
            continue

        scores.append(score)

        if len(scores) < 2:
            signals[date] = {
                "score": score, "tier": tier,
                "momentum": 0, "signal": "hold",
            }
            continue

        recent = scores[-lookback:] if len(scores) >= lookback else scores
        avg = sum(recent) / len(recent)
        momentum = score - scores[-2]

        if avg >= CONVICTION_THRESHOLDS["strong_entry"]:
            signal = "strong_buy"
        elif avg >= CONVICTION_THRESHOLDS["entry"]:
            signal = "buy"
        elif avg >= CONVICTION_THRESHOLDS["lean"]:
            signal = "lean_buy"
        elif avg <= -CONVICTION_THRESHOLDS["strong_entry"]:
            signal = "strong_sell"
        elif avg <= -CONVICTION_THRESHOLDS["entry"]:
            signal = "sell"
        elif avg <= -CONVICTION_THRESHOLDS["lean"]:
            signal = "lean_sell"
        else:
            signal = "hold"

        if abs(momentum) > 0.4:
            signal = "momentum_" + ("buy" if momentum > 0 else "sell")

        signals[date] = {
            "score": round(avg, 4),
            "raw_score": score,
            "tier": tier,
            "momentum": round(momentum, 4),
            "signal": signal,
        }

    return signals


def news_trade_strategy(bars, positions, sentiment_data=None,
                        rsi_confirm=True):
    """trading strategy that combines news sentiment with price action.

    bars: list of ohlc bar dicts
    positions: current position dict
    sentiment_data: pre-loaded sentiment signal dict (date -> signal)
    rsi_confirm: require rsi confirmation for entries

    returns signal dict or None.
    """
    if len(bars) < 20:
        return None

    current = bars[-1]
    date = current.get("date", "")[:10]

    if sentiment_data is None:
        return None

    news_signal = sentiment_data.get(date)
    if news_signal is None:
        for offset in range(1, 4):
            if len(bars) > offset:
                prev_date = bars[-1 - offset].get("date", "")[:10]
                news_signal = sentiment_data.get(prev_date)
                if news_signal:
                    break

    if news_signal is None:
        return None

    closes = [b["close"] for b in bars]
    rsi_vals = rsi(closes, 14)
    current_rsi = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    sma_20 = sma(closes, 20)
    above_sma = closes[-1] > sma_20[-1] if sma_20[-1] is not None else True

    has_position = bool(positions)
    signal_type = news_signal["signal"]
    score = news_signal["score"]

    if not has_position:
        if signal_type in ("strong_buy", "buy", "momentum_buy"):
            if rsi_confirm and current_rsi > 70:
                return None
            if signal_type == "strong_buy" or above_sma:
                size = int(100 * DEFAULT_POSITION_SCALE.get(
                    news_signal.get("tier", 2), 0.5
                ))
                return {
                    "action": "buy",
                    "size": max(size, 10),
                    "reason": f"news {signal_type} score={score:+.3f}",
                }
    else:
        if signal_type in ("strong_sell", "sell", "momentum_sell"):
            return {
                "action": "sell",
                "size": 0,
                "reason": f"news {signal_type} score={score:+.3f}",
            }
        if score <= CONVICTION_THRESHOLDS["exit_reversal"]:
            return {
                "action": "sell",
                "size": 0,
                "reason": f"sentiment reversal score={score:+.3f}",
            }
        if current_rsi > 75 and score < CONVICTION_THRESHOLDS["lean"]:
            return {
                "action": "sell",
                "size": 0,
                "reason": f"overbought + weak sentiment rsi={current_rsi:.0f}",
            }

    return None


def backtest_news_strategy(ticker, sentiment_entries, period="10y"):
    """backtest news trading strategy on historical data.

    loads ohlc data and runs news_trade_strategy against it.
    returns performance dict with trades, returns, equity curve.
    """
    bars = fetch_ohlc(ticker, period)
    if not bars or len(bars) < 50:
        return None

    signals = sentiment_to_signal(sentiment_entries)
    if not signals:
        return None

    capital = 100000.0
    position = 0
    avg_price = 0.0
    trades = []
    equity = []

    for i in range(20, len(bars)):
        bar_slice = bars[:i + 1]
        positions = {}
        if position > 0:
            positions["default"] = {"size": position, "avg_price": avg_price}

        signal = news_trade_strategy(bar_slice, positions, signals)

        if signal:
            price = bars[i]["close"]
            action = signal["action"]
            cost = price * abs(signal.get("size", 100)) * 0.001

            if action == "buy" and position == 0:
                size = signal.get("size", 100)
                if capital >= price * size + cost:
                    capital -= price * size + cost
                    position = size
                    avg_price = price
                    trades.append({
                        "date": bars[i]["date"],
                        "action": "buy",
                        "price": price,
                        "size": size,
                        "reason": signal.get("reason", ""),
                    })
            elif action == "sell" and position > 0:
                revenue = price * position - cost
                pnl = revenue - avg_price * position
                capital += revenue
                trades.append({
                    "date": bars[i]["date"],
                    "action": "sell",
                    "price": price,
                    "size": position,
                    "pnl": round(pnl, 2),
                    "reason": signal.get("reason", ""),
                })
                position = 0
                avg_price = 0.0

        total = capital + position * bars[i]["close"]
        equity.append(round(total, 2))

    final_value = capital + position * bars[-1]["close"]
    return_pct = (final_value - 100000) / 100000 * 100

    winning = [t for t in trades if t.get("pnl", 0) > 0]
    losing = [t for t in trades if t.get("pnl", 0) < 0]

    return {
        "ticker": ticker,
        "final_value": round(final_value, 2),
        "return_pct": round(return_pct, 2),
        "trade_count": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round(len(winning) / max(len(trades), 1) * 100, 1),
        "equity_curve": equity,
        "trades": trades[-20:],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python news_trader.py <ticker>")
        print("  trades based on newk research sentiment signals")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    print(f"news trader: {ticker}")

    sentiment = load_newk_sentiment(ticker)
    if sentiment:
        print(f"  loaded {len(sentiment)} sentiment entries")
        signals = sentiment_to_signal(sentiment)
        buy_signals = sum(1 for s in signals.values()
                          if "buy" in s["signal"])
        sell_signals = sum(1 for s in signals.values()
                           if "sell" in s["signal"])
        print(f"  signals: {buy_signals} buy, {sell_signals} sell")

        result = backtest_news_strategy(ticker, sentiment)
        if result:
            print(f"\n  return: {result['return_pct']:+.2f}%")
            print(f"  trades: {result['trade_count']} "
                  f"(win rate: {result['win_rate']:.1f}%)")
    else:
        print("  no sentiment data available")
        print("  run newk ticker_sentiment first to generate data")
