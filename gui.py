#!/usr/bin/env python3
"""gui: matplotlib visualization for trading strategies with buy/sell alerts"""

import argparse
import sys

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle

from ohlc import fetch_ohlc
from indicators import sma, rsi, macd, bollinger_bands, volume_sma


STRATEGY_MODULES = {
    "gapup": ("gapup", "scan"),
    "bcross": ("bcross", "scan"),
    "across": ("across", "scan"),
    "nolo": ("across", "scan_nolo"),
    "movo": ("movo", "scan_movo"),
    "nobr": ("movo", "scan_nobr"),
    "mobr": ("movo", "scan_mobr"),
    "meanrev": ("meanrev", "scan"),
    "ichimoku": ("ichimoku", "scan"),
}


def load_strategy(name):
    """import a strategy module and return its scan function"""
    if name not in STRATEGY_MODULES:
        return None
    module_name, func_name = STRATEGY_MODULES[name]
    try:
        mod = __import__(module_name)
        return getattr(mod, func_name)
    except (ImportError, AttributeError) as e:
        print(f"could not load strategy '{name}': {e}", file=sys.stderr)
        return None


def run_strategy(name, ticker, period):
    """run a strategy and return its signals as a list of dicts"""
    scan_fn = load_strategy(name)
    if scan_fn is None:
        return []
    try:
        return scan_fn(ticker, period)
    except Exception as e:
        print(f"strategy '{name}' error: {e}", file=sys.stderr)
        return []


def draw_candlesticks(ax, rows):
    """draw candlestick bars using matplotlib rectangles"""
    for i, row in enumerate(rows):
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        color = "#26a69a" if c >= o else "#ef5350"
        body_bottom = min(o, c)
        body_height = abs(c - o)
        if body_height == 0:
            body_height = 0.01

        ax.plot([i, i], [l, h], color=color, linewidth=0.7)
        rect = Rectangle((i - 0.35, body_bottom), 0.7, body_height,
                         facecolor=color, edgecolor=color, linewidth=0.5)
        ax.add_patch(rect)


def draw_overlays(ax, closes, dates):
    """draw sma lines and bollinger bands on the price chart"""
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    bb_mid, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)

    def plot_series(series, **kwargs):
        xs = [i for i, v in enumerate(series) if v is not None]
        ys = [v for v in series if v is not None]
        if xs:
            ax.plot(xs, ys, **kwargs)

    plot_series(sma_20, color="#ff9800", linewidth=1, label="sma20", alpha=0.8)
    plot_series(sma_50, color="#2196f3", linewidth=1, label="sma50", alpha=0.8)

    bb_x = [i for i, v in enumerate(bb_upper) if v is not None]
    bb_u = [v for v in bb_upper if v is not None]
    bb_l = [bb_lower[i] for i in bb_x]
    if bb_x:
        ax.fill_between(bb_x, bb_l, bb_u, alpha=0.08, color="#9c27b0")
        ax.plot(bb_x, bb_u, color="#9c27b0", linewidth=0.5, alpha=0.5)
        ax.plot(bb_x, bb_l, color="#9c27b0", linewidth=0.5, alpha=0.5)


def draw_volume(ax, rows):
    """draw volume bars"""
    volumes = [r["volume"] for r in rows]
    vol_avg = volume_sma(volumes, 20)
    colors = []
    for r in rows:
        colors.append("#26a69a" if r["close"] >= r["open"] else "#ef5350")

    ax.bar(range(len(volumes)), volumes, color=colors, alpha=0.5, width=0.7)

    avg_x = [i for i, v in enumerate(vol_avg) if v is not None]
    avg_y = [v for v in vol_avg if v is not None]
    if avg_x:
        ax.plot(avg_x, avg_y, color="#ff9800", linewidth=1, alpha=0.7)


def draw_rsi(ax, closes):
    """draw rsi subplot with overbought/oversold zones"""
    rsi_vals = rsi(closes, 14)
    xs = [i for i, v in enumerate(rsi_vals) if v is not None]
    ys = [v for v in rsi_vals if v is not None]

    if not xs:
        return

    ax.plot(xs, ys, color="#7e57c2", linewidth=1)
    ax.axhline(70, color="#ef5350", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.axhline(30, color="#26a69a", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.fill_between(xs, 70, [min(y, 70) for y in ys], alpha=0.0)
    ax.set_ylim(0, 100)
    ax.set_ylabel("rsi", fontsize=8)


def draw_macd(ax, closes):
    """draw macd subplot with signal line and histogram"""
    macd_line, signal_line, histogram = macd(closes)

    def valid_pairs(series):
        xs = [i for i, v in enumerate(series) if v is not None]
        ys = [v for v in series if v is not None]
        return xs, ys

    mx, my = valid_pairs(macd_line)
    sx, sy = valid_pairs(signal_line)
    hx, hy = valid_pairs(histogram)

    if mx:
        ax.plot(mx, my, color="#2196f3", linewidth=1, label="macd")
    if sx:
        ax.plot(sx, sy, color="#ff9800", linewidth=1, label="signal")
    if hx:
        colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hy]
        ax.bar(hx, hy, color=colors, alpha=0.5, width=0.7)

    ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
    ax.set_ylabel("macd", fontsize=8)


def draw_signals(ax, rows, signals):
    """mark buy/sell signals on the price chart"""
    date_to_idx = {r["date"]: i for i, r in enumerate(rows)}

    for sig in signals:
        date = sig.get("date")
        if date not in date_to_idx:
            continue
        idx = date_to_idx[date]
        sig_type = sig.get("type", "buy")

        if sig_type in ("exit", "sell"):
            marker, color = "v", "#ef5350"
            offset = rows[idx]["high"] * 1.01
        else:
            marker, color = "^", "#26a69a"
            offset = rows[idx]["low"] * 0.99

        ax.scatter(idx, offset, marker=marker, color=color, s=80, zorder=5)


def build_info_text(rows, closes):
    """build current indicator values text for the data feed panel"""
    if not rows:
        return ""

    last = rows[-1]
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    rsi_vals = rsi(closes, 14)
    macd_line, signal_line, histogram = macd(closes)
    bb_mid, bb_upper, bb_lower = bollinger_bands(closes, 20, 2)

    lines = []
    lines.append(f"date:  {last['date']}")
    lines.append(f"close: ${last['close']:.2f}")
    lines.append(f"vol:   {last['volume']:,.0f}")

    if sma_20[-1] is not None:
        lines.append(f"sma20: ${sma_20[-1]:.2f}")
    if sma_50[-1] is not None:
        lines.append(f"sma50: ${sma_50[-1]:.2f}")
    if rsi_vals[-1] is not None:
        lines.append(f"rsi:   {rsi_vals[-1]:.1f}")
    if macd_line[-1] is not None:
        lines.append(f"macd:  {macd_line[-1]:.4f}")
    if signal_line[-1] is not None:
        lines.append(f"sig:   {signal_line[-1]:.4f}")
    if bb_upper[-1] is not None:
        lines.append(f"bb_u:  ${bb_upper[-1]:.2f}")
    if bb_lower[-1] is not None:
        lines.append(f"bb_l:  ${bb_lower[-1]:.2f}")

    return "\n".join(lines)


def make_date_labels(rows, max_labels=12):
    """generate evenly spaced date labels for the x axis"""
    n = len(rows)
    if n == 0:
        return [], []
    step = max(1, n // max_labels)
    positions = list(range(0, n, step))
    labels = [rows[i]["date"] for i in positions]
    return positions, labels


def plot_chart(ticker, rows, signals, strategy_name):
    """build and display the full chart with all subplots"""
    closes = [r["close"] for r in rows]
    dates = [r["date"] for r in rows]

    fig = plt.figure(figsize=(14, 9))
    fig.patch.set_facecolor("#1e1e1e")

    gs = gridspec.GridSpec(4, 5, height_ratios=[3, 1, 1, 1],
                           hspace=0.15, wspace=0.3)

    ax_price = fig.add_subplot(gs[0, :4])
    ax_vol = fig.add_subplot(gs[1, :4], sharex=ax_price)
    ax_rsi = fig.add_subplot(gs[2, :4], sharex=ax_price)
    ax_macd = fig.add_subplot(gs[3, :4], sharex=ax_price)
    ax_info = fig.add_subplot(gs[:, 4])

    for ax in [ax_price, ax_vol, ax_rsi, ax_macd, ax_info]:
        ax.set_facecolor("#1e1e1e")
        ax.tick_params(colors="#aaaaaa", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#333333")

    draw_candlesticks(ax_price, rows)
    draw_overlays(ax_price, closes, dates)
    draw_signals(ax_price, rows, signals)
    ax_price.set_ylabel("price", fontsize=8, color="#aaaaaa")
    ax_price.yaxis.label.set_color("#aaaaaa")
    ax_price.legend(fontsize=7, loc="upper left", framealpha=0.3)

    title = f"{ticker}"
    if strategy_name:
        title += f" [{strategy_name}]"
    if signals:
        title += f" ({len(signals)} signals)"
    ax_price.set_title(title, fontsize=10, color="#cccccc", pad=8)

    draw_volume(ax_vol, rows)
    ax_vol.set_ylabel("volume", fontsize=8, color="#aaaaaa")

    draw_rsi(ax_rsi, closes)

    draw_macd(ax_macd, closes)

    positions, labels = make_date_labels(rows)
    ax_macd.set_xticks(positions)
    ax_macd.set_xticklabels(labels, rotation=45, fontsize=6, color="#aaaaaa")
    ax_macd.set_xlabel("date", fontsize=8, color="#aaaaaa")

    for ax in [ax_price, ax_vol, ax_rsi]:
        plt.setp(ax.get_xticklabels(), visible=False)

    info_text = build_info_text(rows, closes)
    ax_info.text(0.05, 0.95, info_text, transform=ax_info.transAxes,
                 fontsize=8, color="#cccccc", verticalalignment="top",
                 fontfamily="monospace")
    ax_info.set_xticks([])
    ax_info.set_yticks([])
    ax_info.set_title("data feed", fontsize=8, color="#aaaaaa", pad=8)

    plt.tight_layout()
    plt.show()


def parse_args():
    """parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="trading chart visualization with strategy signals"
    )
    parser.add_argument("ticker", type=str, help="stock ticker symbol")
    parser.add_argument("--strategy", type=str, default=None,
                        choices=list(STRATEGY_MODULES.keys()),
                        help="strategy to run and overlay signals")
    parser.add_argument("--period", type=str, default="6mo",
                        choices=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
                        help="data period (default: 6mo)")
    return parser.parse_args()


def main():
    args = parse_args()
    ticker = args.ticker.upper()

    print(f"fetching {ticker} ({args.period})...")
    rows = fetch_ohlc(ticker, args.period)
    if not rows:
        print(f"no data for {ticker}", file=sys.stderr)
        sys.exit(1)

    print(f"loaded {len(rows)} bars ({rows[0]['date']} to {rows[-1]['date']})")

    signals = []
    if args.strategy:
        print(f"running {args.strategy} strategy...")
        signals = run_strategy(args.strategy, ticker, args.period)
        print(f"found {len(signals)} signals")

    plot_chart(ticker, rows, signals, args.strategy)


if __name__ == "__main__":
    main()
