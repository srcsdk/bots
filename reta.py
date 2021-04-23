#!/usr/bin/env python3
"""reta: short squeeze detection and alerts"""

import json
import re
import sys
from html.parser import HTMLParser
from urllib.request import urlopen, Request
from urllib.error import URLError

from ohlc import fetch_ohlc
from indicators import (
    sma, ema, rsi, macd, bollinger_bands, volume_sma, atr
)


class FinvizParser(HTMLParser):
    """minimal html parser to pull short float and other stats from finviz"""

    def __init__(self):
        super().__init__()
        self._capture = False
        self._last_label = ""
        self.stats = {}
        self._target_labels = {
            "short float", "short interest", "shs float",
            "shs outstand", "avg volume", "volume", "rel volume",
        }

    def handle_data(self, data):
        text = data.strip().lower()
        if text in self._target_labels:
            self._last_label = text
            self._capture = True
        elif self._capture and text:
            self.stats[self._last_label] = text
            self._capture = False


def fetch_finviz_stats(ticker):
    """scrape short interest data from finviz overview page"""
    url = f"https://finviz.com/quote.ashx?t={ticker}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except URLError as e:
        print(f"  finviz error for {ticker}: {e}", file=sys.stderr)
        return {}

    parser = FinvizParser()
    try:
        parser.feed(html)
    except Exception:
        return {}

    return parser.stats


def parse_percent(val):
    """parse '25.30%' to 25.3, returns None on failure"""
    if not val:
        return None
    cleaned = val.replace("%", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_number(val):
    """parse volume strings like '12.5M' or '1.2B' to float"""
    if not val:
        return None
    val = val.strip().replace(",", "")
    multipliers = {"K": 1e3, "M": 1e6, "B": 1e9}
    for suffix, mult in multipliers.items():
        if val.upper().endswith(suffix):
            try:
                return float(val[:-1]) * mult
            except ValueError:
                return None
    try:
        return float(val)
    except ValueError:
        return None


def detect_volume_spikes(volumes, threshold=3.0, lookback=20):
    """find days where volume exceeds threshold * average volume"""
    avg = volume_sma(volumes, lookback)
    spikes = []
    for i in range(len(volumes)):
        if avg[i] is not None and avg[i] > 0:
            ratio = volumes[i] / avg[i]
            if ratio >= threshold:
                spikes.append((i, round(ratio, 2)))
    return spikes


def measure_band_squeeze(closes, period=20, std_dev=2):
    """measure bollinger band width compression over time.
    returns list of (index, bandwidth_pct) for narrowing bands.
    """
    middle, upper, lower = bollinger_bands(closes, period, std_dev)
    widths = []
    for i in range(len(closes)):
        if upper[i] is not None and lower[i] is not None and middle[i]:
            bw = (upper[i] - lower[i]) / middle[i] * 100
            widths.append(round(bw, 4))
        else:
            widths.append(None)
    return widths


def find_compression_zones(band_widths, lookback=10, shrink_pct=0.4):
    """detect where bandwidth has narrowed significantly.
    returns indices where current width < shrink_pct * recent max width.
    """
    zones = []
    for i in range(lookback, len(band_widths)):
        window = [w for w in band_widths[i - lookback:i] if w is not None]
        if not window or band_widths[i] is None:
            continue
        max_width = max(window)
        if max_width > 0 and band_widths[i] < max_width * shrink_pct:
            zones.append(i)
    return zones


def estimate_days_to_cover(short_interest, avg_volume):
    """days to cover = short interest shares / avg daily volume"""
    if not short_interest or not avg_volume or avg_volume == 0:
        return None
    return round(short_interest / avg_volume, 2)


def get_hype_score(ticker):
    """try to get social media hype score from hype.py if available"""
    try:
        from hype import get_hype
        return get_hype(ticker)
    except ImportError:
        return None
    except Exception:
        return None


def score_squeeze_potential(ticker, rows, finviz_data):
    """score a ticker's squeeze potential 0-100 based on multiple factors.
    returns (score, breakdown_dict).
    """
    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]

    score = 0
    breakdown = {}

    # short float score (0-30 points)
    short_float = parse_percent(finviz_data.get("short float"))
    if short_float is not None:
        if short_float >= 40:
            pts = 30
        elif short_float >= 20:
            pts = 25
        elif short_float >= 15:
            pts = 20
        elif short_float >= 10:
            pts = 10
        else:
            pts = max(0, int(short_float))
        score += pts
        breakdown["short_float"] = (short_float, pts)
    else:
        breakdown["short_float"] = (None, 0)

    # volume surge pattern (0-25 points)
    spikes = detect_volume_spikes(volumes, threshold=2.0)
    recent_spikes = [s for s in spikes if s[0] >= len(rows) - 10]
    if recent_spikes:
        max_ratio = max(s[1] for s in recent_spikes)
        pts = min(25, int(max_ratio * 5))
        score += pts
        breakdown["volume_surge"] = (max_ratio, pts)
    else:
        breakdown["volume_surge"] = (0, 0)

    # price consolidation near support (0-20 points)
    band_widths = measure_band_squeeze(closes)
    compression_zones = find_compression_zones(band_widths)
    recent_compression = any(z >= len(rows) - 10 for z in compression_zones)
    if recent_compression and band_widths[-1] is not None:
        pts = 20
        score += pts
        breakdown["consolidation"] = (band_widths[-1], pts)
    else:
        last_bw = band_widths[-1] if band_widths else None
        breakdown["consolidation"] = (last_bw, 0)

    # days to cover (0-15 points)
    si_shares = parse_number(finviz_data.get("short interest"))
    avg_vol = parse_number(finviz_data.get("avg volume"))
    dtc = estimate_days_to_cover(si_shares, avg_vol)
    if dtc is not None:
        if dtc >= 10:
            pts = 15
        elif dtc >= 5:
            pts = 10
        elif dtc >= 3:
            pts = 5
        else:
            pts = 0
        score += pts
        breakdown["days_to_cover"] = (dtc, pts)
    else:
        breakdown["days_to_cover"] = (None, 0)

    # social hype bonus (0-10 points)
    hype = get_hype_score(ticker)
    if hype is not None:
        pts = min(10, int(hype))
        score += pts
        breakdown["hype"] = (hype, pts)
    else:
        breakdown["hype"] = (None, 0)

    return min(100, score), breakdown


def find_entry_signals(rows, min_score=40):
    """detect entry signals: volume spike + compression + rising momentum.
    call after scoring confirms squeeze potential.
    """
    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]

    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)
    vol_avg = volume_sma(volumes, 20)
    band_widths = measure_band_squeeze(closes)

    signals = []
    for i in range(2, len(rows)):
        if rsi_vals[i] is None or hist[i] is None or hist[i - 1] is None:
            continue
        if vol_avg[i] is None or vol_avg[i] == 0:
            continue

        vol_ratio = volumes[i] / vol_avg[i]
        volume_surge = vol_ratio >= 2.0
        macd_turning_up = hist[i] > hist[i - 1]
        rsi_not_extreme = 30 < rsi_vals[i] < 70
        compressed = (
            band_widths[i] is not None
            and band_widths[i - 1] is not None
            and band_widths[i] > band_widths[i - 1]
        )

        if volume_surge and macd_turning_up and rsi_not_extreme:
            signals.append({
                "type": "entry",
                "date": rows[i]["date"],
                "price": closes[i],
                "vol_ratio": round(vol_ratio, 2),
                "rsi": rsi_vals[i],
                "macd_hist": hist[i],
                "band_expanding": compressed,
            })

    return signals


def find_exit_signals(rows):
    """detect exit signals: peak momentum divergence.
    price making new highs while rsi/macd diverge downward.
    """
    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]

    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)

    signals = []
    lookback = 5

    for i in range(lookback, len(rows)):
        if rsi_vals[i] is None or hist[i] is None:
            continue

        recent_closes = closes[i - lookback:i + 1]
        recent_rsi = [r for r in rsi_vals[i - lookback:i + 1] if r is not None]
        recent_hist = [h for h in hist[i - lookback:i + 1] if h is not None]

        if len(recent_rsi) < 3 or len(recent_hist) < 3:
            continue

        price_at_high = closes[i] >= max(recent_closes)
        rsi_declining = recent_rsi[-1] < max(recent_rsi[:-1])
        macd_declining = recent_hist[-1] < max(recent_hist[:-1])
        rsi_overbought = rsi_vals[i] > 70

        if price_at_high and rsi_declining and macd_declining and rsi_overbought:
            signals.append({
                "type": "exit",
                "date": rows[i]["date"],
                "price": closes[i],
                "rsi": rsi_vals[i],
                "macd_hist": hist[i],
                "divergence": "bearish",
            })

    return signals


def analyze_ticker(ticker, period="6mo"):
    """full squeeze analysis for a single ticker"""
    print(f"\n{'=' * 50}")
    print(f"  {ticker} squeeze analysis")
    print(f"{'=' * 50}")

    rows = fetch_ohlc(ticker, period)
    if not rows or len(rows) < 40:
        print(f"  insufficient data for {ticker}")
        return None

    print(f"  data: {rows[0]['date']} to {rows[-1]['date']} ({len(rows)} bars)")
    print(f"  last close: ${rows[-1]['close']:.2f}")

    print(f"  fetching short interest data...")
    finviz_data = fetch_finviz_stats(ticker)

    total_score, breakdown = score_squeeze_potential(ticker, rows, finviz_data)

    print(f"\n  squeeze score: {total_score}/100")
    print(f"  breakdown:")
    for factor, (val, pts) in breakdown.items():
        if val is not None:
            print(f"    {factor:<20} value={val:<10} pts={pts}")
        else:
            print(f"    {factor:<20} value=n/a       pts={pts}")

    entries = find_entry_signals(rows)
    exits = find_exit_signals(rows)

    if entries:
        recent_entries = entries[-5:]
        print(f"\n  entry signals ({len(entries)} total, showing last {len(recent_entries)}):")
        for s in recent_entries:
            print(f"    {s['date']} ${s['price']:.2f} "
                  f"vol={s['vol_ratio']}x rsi={s['rsi']:.1f} "
                  f"hist={s['macd_hist']:.4f}")
    else:
        print(f"\n  no entry signals found")

    if exits:
        recent_exits = exits[-5:]
        print(f"\n  exit signals ({len(exits)} total, showing last {len(recent_exits)}):")
        for s in recent_exits:
            print(f"    {s['date']} ${s['price']:.2f} "
                  f"rsi={s['rsi']:.1f} hist={s['macd_hist']:.4f} "
                  f"[{s['divergence']}]")
    else:
        print(f"\n  no exit signals found")

    verdict = "neutral"
    if total_score >= 70:
        verdict = "high squeeze potential"
    elif total_score >= 50:
        verdict = "moderate squeeze potential"
    elif total_score >= 30:
        verdict = "low squeeze potential"

    if entries and entries[-1]["date"] == rows[-1]["date"]:
        verdict += " (active entry signal)"
    if exits and exits[-1]["date"] == rows[-1]["date"]:
        verdict += " (exit signal - take profits)"

    print(f"\n  verdict: {verdict}")

    return {
        "ticker": ticker,
        "score": total_score,
        "breakdown": breakdown,
        "entries": entries,
        "exits": exits,
        "verdict": verdict,
        "last_close": rows[-1]["close"],
        "last_date": rows[-1]["date"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python reta.py <ticker> [ticker2] [ticker3] ...")
        print("  checks tickers for short squeeze setup")
        print("  example: python reta.py AMC GME BB")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    results = []

    for ticker in tickers:
        result = analyze_ticker(ticker)
        if result:
            results.append(result)

    if len(results) > 1:
        print(f"\n{'=' * 50}")
        print(f"  summary (ranked by squeeze score)")
        print(f"{'=' * 50}")
        results.sort(key=lambda r: r["score"], reverse=True)
        for r in results:
            print(f"  {r['ticker']:<6} score={r['score']:>3}/100  "
                  f"${r['last_close']:>8.2f}  {r['verdict']}")
