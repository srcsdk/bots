#!/usr/bin/env python3
"""autore: reverse engineer successful trades to find indicator patterns

takes a known successful trade (ticker, entry date, exit date), fetches
historical data, computes all indicators at entry/exit, scores which
indicators correctly predicted the move, and builds a fingerprint of
what makes a successful trade for that ticker. also supports options
trade analysis.
"""

import importlib
import json
import math
import sys
from datetime import datetime

from ohlc import fetch_ohlc
from indicators import (
    sma, ema, rsi, macd, bollinger_bands, atr,
    fifty_two_week_low, fifty_two_week_high, volume_sma, gap_percent,
)

_lambda = importlib.import_module("lambda")


def find_date_index(rows, date_str):
    """find the index of a date in ohlc rows. returns closest match."""
    for i, r in enumerate(rows):
        if r["date"] == date_str:
            return i
        if r["date"] > date_str:
            return max(0, i - 1)
    return len(rows) - 1


def compute_all_indicators(closes, opens, highs, lows, volumes):
    """compute every available indicator, return dict of named series."""
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    bb_mid, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)
    atr_vals = atr(highs, lows, closes, 14)
    low_52 = fifty_two_week_low(closes)
    high_52 = fifty_two_week_high(closes)
    vol_sma_20 = volume_sma(volumes, 20)
    sma_10 = sma(closes, 10)
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)
    ema_9 = ema(closes, 9)
    ema_12 = ema(closes, 12)
    ema_20 = ema(closes, 20)
    ema_50 = ema(closes, 50)
    gaps = gap_percent(opens, closes)
    rsi_7 = rsi(closes, 7)
    bb_mid_10, bb_upper_10, bb_lower_10 = bollinger_bands(closes, 10, 2)

    return {
        "rsi_14": rsi_vals,
        "rsi_7": rsi_7,
        "macd_line": macd_line,
        "macd_signal": signal_line,
        "macd_hist": hist,
        "bb_mid": bb_mid,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid_10": bb_mid_10,
        "bb_upper_10": bb_upper_10,
        "bb_lower_10": bb_lower_10,
        "atr": atr_vals,
        "low_52": low_52,
        "high_52": high_52,
        "vol_sma_20": vol_sma_20,
        "sma_10": sma_10,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "ema_9": ema_9,
        "ema_12": ema_12,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "gaps": gaps,
    }


def snapshot_at(idx, closes, volumes, indicators):
    """capture indicator values at a specific index."""
    snap = {"price": closes[idx], "volume": volumes[idx]}
    for name, series in indicators.items():
        if idx < len(series) and series[idx] is not None:
            val = series[idx]
            snap[name] = round(val, 4) if isinstance(val, float) else val
    return snap


def score_entry_indicators(entry_idx, exit_idx, closes, volumes, indicators):
    """score how well each indicator predicted the successful trade at entry.

    checks each indicator's value at entry and whether it correctly suggested
    the direction of the subsequent move.
    """
    if entry_idx >= exit_idx:
        return {}

    direction = "long" if closes[exit_idx] > closes[entry_idx] else "short"
    gain_pct = (closes[exit_idx] - closes[entry_idx]) / closes[entry_idx] * 100
    scores = {}

    rsi_val = indicators["rsi_14"][entry_idx]
    if rsi_val is not None:
        if direction == "long" and rsi_val < 35:
            scores["rsi_oversold_entry"] = round(min((35 - rsi_val) / 35, 1.0), 3)
        elif direction == "short" and rsi_val > 65:
            scores["rsi_overbought_entry"] = round(min((rsi_val - 65) / 35, 1.0), 3)
        else:
            scores["rsi_neutral_entry"] = 0

    bb_lower = indicators["bb_lower"][entry_idx]
    bb_upper = indicators["bb_upper"][entry_idx]
    if bb_lower is not None and bb_upper is not None:
        if direction == "long" and closes[entry_idx] <= bb_lower:
            scores["bb_lower_touch"] = round(
                min(abs(bb_lower - closes[entry_idx]) / closes[entry_idx] * 50, 1.0), 3
            )
        elif direction == "short" and closes[entry_idx] >= bb_upper:
            scores["bb_upper_touch"] = round(
                min(abs(closes[entry_idx] - bb_upper) / closes[entry_idx] * 50, 1.0), 3
            )

    macd_h = indicators["macd_hist"][entry_idx]
    macd_h_prev = indicators["macd_hist"][entry_idx - 1] if entry_idx > 0 else None
    if macd_h is not None and macd_h_prev is not None:
        if direction == "long" and macd_h > macd_h_prev and macd_h_prev < 0:
            scores["macd_bullish_turn"] = 0.8
        elif direction == "short" and macd_h < macd_h_prev and macd_h_prev > 0:
            scores["macd_bearish_turn"] = 0.8
        elif direction == "long" and macd_h > 0:
            scores["macd_positive"] = 0.3
        elif direction == "short" and macd_h < 0:
            scores["macd_negative"] = 0.3

    sma_50 = indicators["sma_50"][entry_idx]
    sma_200 = indicators["sma_200"][entry_idx]
    if sma_50 is not None and sma_200 is not None:
        if direction == "long" and closes[entry_idx] < sma_200:
            scores["below_sma200"] = round(
                min((sma_200 - closes[entry_idx]) / closes[entry_idx] * 10, 1.0), 3
            )
        if direction == "long" and sma_50 > sma_200:
            scores["golden_cross"] = 0.7
        elif direction == "long" and sma_50 < sma_200:
            scores["death_cross_reversal"] = 0.5

    low_52 = indicators["low_52"][entry_idx]
    high_52 = indicators["high_52"][entry_idx]
    if low_52 is not None and direction == "long":
        pct_above = (closes[entry_idx] - low_52) / low_52
        if pct_above < 0.1:
            scores["near_52w_low"] = round(1.0 - pct_above * 10, 3)
    if high_52 is not None and high_52 > 0 and direction == "long":
        drawdown = (high_52 - closes[entry_idx]) / high_52
        if drawdown > 0.2:
            scores["deep_drawdown"] = round(min(drawdown, 1.0), 3)

    vol_sma = indicators["vol_sma_20"][entry_idx]
    if vol_sma is not None and vol_sma > 0:
        vol_ratio = volumes[entry_idx] / vol_sma
        if vol_ratio > 2.0:
            scores["volume_spike"] = round(min((vol_ratio - 1) / 4, 1.0), 3)
        elif vol_ratio < 0.5:
            scores["volume_dry"] = round(min((1 - vol_ratio) * 0.5, 0.5), 3)

    atr_val = indicators["atr"][entry_idx]
    if atr_val is not None and closes[entry_idx] > 0:
        atr_pct = atr_val / closes[entry_idx]
        if atr_pct > 0.04:
            scores["high_atr"] = round(min(atr_pct * 10, 1.0), 3)

    lookback = min(5, entry_idx)
    for j in range(entry_idx - lookback, entry_idx):
        gap = indicators["gaps"][j]
        if gap is not None and direction == "long" and gap < -3:
            scores["gap_down_recovery"] = round(min(abs(gap) / 10, 1.0), 3)
            break

    scores["trade_gain_pct"] = round(gain_pct, 2)
    scores["direction"] = direction
    return scores


def build_fingerprint(scores):
    """build a fingerprint from scored indicators, keeping strong signals."""
    fingerprint = {}
    for name, val in scores.items():
        if name in ("trade_gain_pct", "direction"):
            continue
        if isinstance(val, (int, float)) and val >= 0.3:
            fingerprint[name] = val
    return dict(sorted(fingerprint.items(), key=lambda x: -x[1]))


def analyze_options_trade(ticker, entry_date, exit_date, option_type,
                          strike, expiry, rows):
    """reverse engineer a successful options trade.

    computes greeks at entry and exit, evaluates what made the trade work.
    """
    entry_idx = find_date_index(rows, entry_date)
    exit_idx = find_date_index(rows, exit_date)
    closes = [r["close"] for r in rows]

    entry_spot = closes[entry_idx]
    exit_spot = closes[exit_idx]

    hvol_entry = _lambda.historical_volatility(closes[:entry_idx + 1])
    hvol_exit = _lambda.historical_volatility(closes[:exit_idx + 1])
    if hvol_entry is None:
        hvol_entry = 0.3
    if hvol_exit is None:
        hvol_exit = 0.3

    rate = 0.05

    entry_expiry_dt = datetime.strptime(expiry, "%Y-%m-%d")
    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
    exit_dt = datetime.strptime(exit_date, "%Y-%m-%d")

    t_entry = max((entry_expiry_dt - entry_dt).days / 365.0, 0.001)
    t_exit = max((entry_expiry_dt - exit_dt).days / 365.0, 0.001)

    entry_greeks = _lambda.calc_greeks(entry_spot, strike, rate, hvol_entry,
                                       t_entry, option_type)
    exit_greeks = _lambda.calc_greeks(exit_spot, strike, rate, hvol_exit,
                                      t_exit, option_type)

    entry_price = entry_greeks["price"]
    exit_price = exit_greeks["price"]
    if entry_price > 0:
        options_gain_pct = (exit_price - entry_price) / entry_price * 100
    else:
        options_gain_pct = 0

    spot_move = (exit_spot - entry_spot) / entry_spot * 100
    vol_change = hvol_exit - hvol_entry
    time_decay_days = (exit_dt - entry_dt).days

    factors = []
    if abs(spot_move) > 20:
        factors.append(f"large underlying move: {spot_move:+.1f}%")
    if abs(vol_change) > 0.1:
        direction = "expansion" if vol_change > 0 else "contraction"
        factors.append(f"vol {direction}: {vol_change:+.3f}")
    if abs(entry_greeks["delta"]) > 0.5:
        factors.append(f"high delta at entry: {entry_greeks['delta']:.3f}")
    if entry_greeks["gamma"] > 0.01:
        factors.append(f"high gamma at entry: {entry_greeks['gamma']:.4f}")

    return {
        "option_type": option_type,
        "strike": strike,
        "expiry": expiry,
        "entry_spot": round(entry_spot, 2),
        "exit_spot": round(exit_spot, 2),
        "spot_move_pct": round(spot_move, 2),
        "entry_hvol": round(hvol_entry, 4),
        "exit_hvol": round(hvol_exit, 4),
        "vol_change": round(vol_change, 4),
        "entry_greeks": entry_greeks,
        "exit_greeks": exit_greeks,
        "entry_price": round(entry_price, 4),
        "exit_price": round(exit_price, 4),
        "options_gain_pct": round(options_gain_pct, 2),
        "time_decay_days": time_decay_days,
        "key_factors": factors,
    }


def run_analysis(ticker, entry_date, exit_date, options_args=None):
    """run full reverse engineering analysis on a trade.

    fetches data, computes indicators at entry/exit, scores them,
    builds fingerprint. optionally analyzes options component.
    """
    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
    exit_dt = datetime.strptime(exit_date, "%Y-%m-%d")
    total_days = (exit_dt - entry_dt).days

    buffer_days = max(365, total_days + 300)
    if buffer_days <= 365:
        period = "2y"
    elif buffer_days <= 730:
        period = "2y"
    else:
        period = "5y"

    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 60:
        print(f"error: insufficient data for {ticker}", file=sys.stderr)
        return None

    entry_idx = find_date_index(rows, entry_date)
    exit_idx = find_date_index(rows, exit_date)

    if entry_idx >= exit_idx:
        print(f"error: entry date must be before exit date", file=sys.stderr)
        return None

    closes = [r["close"] for r in rows]
    opens = [r["open"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    volumes = [r["volume"] for r in rows]

    indicators = compute_all_indicators(closes, opens, highs, lows, volumes)

    entry_snap = snapshot_at(entry_idx, closes, volumes, indicators)
    exit_snap = snapshot_at(exit_idx, closes, volumes, indicators)

    entry_scores = score_entry_indicators(
        entry_idx, exit_idx, closes, volumes, indicators
    )
    fingerprint = build_fingerprint(entry_scores)

    gain_pct = (closes[exit_idx] - closes[entry_idx]) / closes[entry_idx] * 100

    result = {
        "ticker": ticker,
        "entry_date": rows[entry_idx]["date"],
        "exit_date": rows[exit_idx]["date"],
        "entry_price": closes[entry_idx],
        "exit_price": closes[exit_idx],
        "gain_pct": round(gain_pct, 2),
        "hold_days": (exit_dt - entry_dt).days,
        "entry_snapshot": entry_snap,
        "exit_snapshot": exit_snap,
        "indicator_scores": entry_scores,
        "fingerprint": fingerprint,
    }

    if options_args:
        opt_type, strike, expiry = options_args
        options_analysis = analyze_options_trade(
            ticker, entry_date, exit_date, opt_type, strike, expiry, rows
        )
        result["options"] = options_analysis

    return result


def save_analysis(result, output_dir="."):
    """save analysis result as ticker-date.json."""
    ticker = result["ticker"].lower()
    entry = result["entry_date"].replace("-", "")
    filename = f"{output_dir}/{ticker}-{entry}.json"
    with open(filename, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return filename


def print_analysis(result):
    """print formatted analysis to stdout."""
    print(f"\n{result['ticker']}  {result['entry_date']} -> {result['exit_date']}")
    print(f"  entry: ${result['entry_price']:.2f}  exit: ${result['exit_price']:.2f}"
          f"  gain: {result['gain_pct']:+.2f}%  days: {result['hold_days']}")

    print(f"\nentry indicators:")
    snap = result["entry_snapshot"]
    for key in sorted(snap.keys()):
        if key in ("price", "volume"):
            continue
        print(f"  {key:<20s} {snap[key]}")

    scores = result["indicator_scores"]
    direction = scores.pop("direction", "long")
    trade_gain = scores.pop("trade_gain_pct", 0)
    print(f"\nindicator scores (direction: {direction}, gain: {trade_gain:+.2f}%):")
    for name, val in sorted(scores.items(), key=lambda x: -x[1] if isinstance(x[1], (int, float)) else 0):
        if isinstance(val, (int, float)):
            bar = "#" * int(val * 20)
            print(f"  {name:<25s} {val:.3f} {bar}")
    scores["direction"] = direction
    scores["trade_gain_pct"] = trade_gain

    fp = result["fingerprint"]
    if fp:
        print(f"\nfingerprint ({len(fp)} strong signals):")
        for name, val in fp.items():
            print(f"  {name}: {val:.3f}")

    if "options" in result:
        opt = result["options"]
        print(f"\noptions analysis: {opt['option_type']} ${opt['strike']:.0f}"
              f" exp {opt['expiry']}")
        print(f"  underlying: ${opt['entry_spot']:.2f} -> ${opt['exit_spot']:.2f}"
              f"  ({opt['spot_move_pct']:+.2f}%)")
        print(f"  option: ${opt['entry_price']:.2f} -> ${opt['exit_price']:.2f}"
              f"  ({opt['options_gain_pct']:+.2f}%)")
        print(f"  vol: {opt['entry_hvol']:.4f} -> {opt['exit_hvol']:.4f}"
              f"  ({opt['vol_change']:+.4f})")
        eg = opt["entry_greeks"]
        print(f"  entry greeks: d={eg['delta']:.3f} g={eg['gamma']:.4f}"
              f" t={eg['theta']:.4f} v={eg['vega']:.3f}")
        if opt["key_factors"]:
            print(f"  key factors:")
            for f in opt["key_factors"]:
                print(f"    {f}")


def main():
    if len(sys.argv) < 4:
        print("usage: python autore.py TICKER ENTRY_DATE EXIT_DATE [--options TYPE STRIKE EXPIRY]")
        print("  example: python autore.py NVDA 2020-03-23 2021-02-12")
        print("  options: python autore.py NVDA 2020-03-23 2021-02-12 --options call 500 2021-03-19")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    entry_date = sys.argv[2]
    exit_date = sys.argv[3]

    for d in (entry_date, exit_date):
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            print(f"error: invalid date format '{d}', use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

    options_args = None
    if "--options" in sys.argv:
        opt_idx = sys.argv.index("--options")
        if opt_idx + 3 >= len(sys.argv):
            print("error: --options requires TYPE STRIKE EXPIRY", file=sys.stderr)
            sys.exit(1)
        opt_type = sys.argv[opt_idx + 1].lower()
        if opt_type not in ("call", "put"):
            print("error: option type must be 'call' or 'put'", file=sys.stderr)
            sys.exit(1)
        try:
            opt_strike = float(sys.argv[opt_idx + 2])
        except ValueError:
            print("error: strike must be a number", file=sys.stderr)
            sys.exit(1)
        opt_expiry = sys.argv[opt_idx + 3]
        try:
            datetime.strptime(opt_expiry, "%Y-%m-%d")
        except ValueError:
            print(f"error: invalid expiry date '{opt_expiry}'", file=sys.stderr)
            sys.exit(1)
        options_args = (opt_type, opt_strike, opt_expiry)

    print(f"autore: reverse engineering {ticker}"
          f" {entry_date} -> {exit_date}")

    result = run_analysis(ticker, entry_date, exit_date, options_args)
    if not result:
        sys.exit(1)

    print_analysis(result)

    filename = save_analysis(result)
    print(f"\nsaved: {filename}")


if __name__ == "__main__":
    main()
