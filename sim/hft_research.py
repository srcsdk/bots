#!/usr/bin/env python3
"""hft research and market microstructure analysis"""

import math
import statistics


class OrderBookAnalyzer:
    """analyze order book data for microstructure signals."""

    def __init__(self, depth=10):
        self.depth = depth
        self.snapshots = []

    def add_snapshot(self, bids, asks, timestamp=None):
        """record order book snapshot.

        bids/asks: list of (price, size) tuples sorted by price.
        """
        snap = {
            "bids": bids[:self.depth],
            "asks": asks[:self.depth],
            "timestamp": timestamp,
        }
        self.snapshots.append(snap)
        return snap

    def bid_ask_spread(self, snapshot=None):
        """calculate bid-ask spread from snapshot."""
        snap = snapshot or (self.snapshots[-1] if self.snapshots else None)
        if not snap:
            return None
        bids = snap["bids"]
        asks = snap["asks"]
        if not bids or not asks:
            return None
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2
        return {
            "spread": round(spread, 6),
            "spread_bps": round(spread / mid * 10000, 2) if mid > 0 else 0,
            "mid": round(mid, 6),
            "best_bid": best_bid,
            "best_ask": best_ask,
        }

    def depth_imbalance(self, snapshot=None, levels=5):
        """calculate order book depth imbalance.

        positive = more bid volume (bullish pressure)
        negative = more ask volume (bearish pressure)
        """
        snap = snapshot or (self.snapshots[-1] if self.snapshots else None)
        if not snap:
            return 0
        bid_vol = sum(
            size for _, size in snap["bids"][:levels]
        )
        ask_vol = sum(
            size for _, size in snap["asks"][:levels]
        )
        total = bid_vol + ask_vol
        if total == 0:
            return 0
        return round((bid_vol - ask_vol) / total, 4)

    def spread_history(self):
        """get spread timeseries from all snapshots."""
        spreads = []
        for snap in self.snapshots:
            result = self.bid_ask_spread(snap)
            if result:
                spreads.append({
                    "timestamp": snap["timestamp"],
                    "spread_bps": result["spread_bps"],
                    "mid": result["mid"],
                })
        return spreads

    def vpin(self, trades, bucket_size=50):
        """calculate volume-synchronized probability of informed trading.

        trades: list of dicts with price, volume, direction (1=buy, -1=sell).
        bucket_size: number of shares per bucket.
        """
        if not trades:
            return []
        buckets = []
        current_buy = 0
        current_sell = 0
        current_vol = 0
        for trade in trades:
            vol = trade.get("volume", 0)
            direction = trade.get("direction", 0)
            remaining = vol
            while remaining > 0:
                needed = bucket_size - current_vol
                fill = min(remaining, needed)
                if direction > 0:
                    current_buy += fill
                else:
                    current_sell += fill
                current_vol += fill
                remaining -= fill
                if current_vol >= bucket_size:
                    order_imbalance = abs(current_buy - current_sell)
                    buckets.append(order_imbalance / bucket_size)
                    current_buy = 0
                    current_sell = 0
                    current_vol = 0
        n_window = min(50, len(buckets))
        if n_window == 0:
            return []
        vpins = []
        for i in range(n_window, len(buckets) + 1):
            window = buckets[i - n_window:i]
            vpins.append(round(statistics.mean(window), 4))
        return vpins


class LatencyModel:
    """simulate different latency tiers for strategy analysis."""

    TIERS = {
        "retail": {"latency_ms": 50, "jitter_ms": 20, "description": "standard retail broker"},
        "premium": {"latency_ms": 10, "jitter_ms": 5, "description": "premium broker with dma"},
        "colo": {"latency_ms": 1, "jitter_ms": 0.5, "description": "colocated server"},
        "direct": {"latency_ms": 0.1, "jitter_ms": 0.05, "description": "direct market access fpga"},
    }

    def __init__(self, tier="retail"):
        if tier not in self.TIERS:
            tier = "retail"
        self.tier = tier
        self.config = self.TIERS[tier]

    def effective_price(self, price, volatility, direction=1):
        """estimate effective execution price given latency.

        higher latency = more slippage in volatile markets.
        direction: 1 for buy, -1 for sell.
        """
        latency_sec = self.config["latency_ms"] / 1000
        expected_move = volatility * math.sqrt(latency_sec / 86400)
        slippage = expected_move * price * direction
        return round(price + slippage, 6)

    def simulate_fills(self, orders, volatility=0.02):
        """simulate order fills with latency effects.

        orders: list of dicts with price, size, direction.
        returns list of fill results with actual prices.
        """
        fills = []
        for order in orders:
            price = order["price"]
            direction = order.get("direction", 1)
            eff_price = self.effective_price(price, volatility, direction)
            slippage_bps = abs(eff_price - price) / price * 10000
            fills.append({
                "requested_price": price,
                "fill_price": eff_price,
                "slippage_bps": round(slippage_bps, 4),
                "latency_ms": self.config["latency_ms"],
                "size": order.get("size", 0),
            })
        return fills

    def compare_tiers(self, price, volatility=0.02):
        """compare execution quality across all latency tiers."""
        results = {}
        for tier_name, config in self.TIERS.items():
            model = LatencyModel(tier_name)
            buy_price = model.effective_price(price, volatility, 1)
            sell_price = model.effective_price(price, volatility, -1)
            roundtrip_cost = (buy_price - sell_price) / price * 10000
            results[tier_name] = {
                "latency_ms": config["latency_ms"],
                "buy_slip_bps": round(
                    abs(buy_price - price) / price * 10000, 4
                ),
                "sell_slip_bps": round(
                    abs(sell_price - price) / price * 10000, 4
                ),
                "roundtrip_cost_bps": round(roundtrip_cost, 4),
            }
        return results


class MarketMicrostructure:
    """tick-level market microstructure analysis."""

    def __init__(self):
        self.ticks = []

    def add_tick(self, price, volume, timestamp=None, direction=None):
        """record a trade tick."""
        if direction is None and self.ticks:
            direction = 1 if price >= self.ticks[-1]["price"] else -1
        elif direction is None:
            direction = 1
        self.ticks.append({
            "price": price,
            "volume": volume,
            "timestamp": timestamp,
            "direction": direction,
        })

    def price_impact(self, window=100):
        """estimate temporary and permanent price impact.

        uses recent ticks to calculate kyle's lambda (price sensitivity
        to order flow).
        """
        recent = self.ticks[-window:] if len(self.ticks) >= window else self.ticks
        if len(recent) < 10:
            return {"lambda": 0, "r_squared": 0}
        price_changes = []
        signed_volumes = []
        for i in range(1, len(recent)):
            dp = recent[i]["price"] - recent[i - 1]["price"]
            sv = recent[i]["volume"] * recent[i]["direction"]
            price_changes.append(dp)
            signed_volumes.append(sv)
        if not signed_volumes:
            return {"lambda": 0, "r_squared": 0}
        mean_sv = statistics.mean(signed_volumes)
        mean_dp = statistics.mean(price_changes)
        cov = sum(
            (signed_volumes[i] - mean_sv) * (price_changes[i] - mean_dp)
            for i in range(len(signed_volumes))
        )
        var_sv = sum((sv - mean_sv) ** 2 for sv in signed_volumes)
        if var_sv == 0:
            return {"lambda": 0, "r_squared": 0}
        kyle_lambda = cov / var_sv
        ss_res = sum(
            (price_changes[i] - kyle_lambda * signed_volumes[i]) ** 2
            for i in range(len(signed_volumes))
        )
        ss_tot = sum((dp - mean_dp) ** 2 for dp in price_changes)
        r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return {
            "lambda": round(kyle_lambda, 8),
            "r_squared": round(max(0, r_sq), 4),
            "n_ticks": len(recent),
        }

    def realized_spread(self, horizon=5):
        """calculate realized spread (post-trade price reversion).

        measures execution quality by looking at price horizon ticks later.
        """
        spreads = []
        for i in range(len(self.ticks) - horizon):
            tick = self.ticks[i]
            future = self.ticks[i + horizon]
            if tick["direction"] == 1:
                realized = 2 * (future["price"] - tick["price"])
            else:
                realized = 2 * (tick["price"] - future["price"])
            spreads.append(realized)
        if not spreads:
            return {"mean": 0, "median": 0, "count": 0}
        return {
            "mean": round(statistics.mean(spreads), 6),
            "median": round(statistics.median(spreads), 6),
            "count": len(spreads),
        }

    def tick_volatility(self, window=100):
        """estimate volatility from tick data."""
        recent = self.ticks[-window:] if len(self.ticks) >= window else self.ticks
        if len(recent) < 2:
            return 0
        log_returns = []
        for i in range(1, len(recent)):
            if recent[i - 1]["price"] > 0 and recent[i]["price"] > 0:
                lr = math.log(recent[i]["price"] / recent[i - 1]["price"])
                log_returns.append(lr)
        if not log_returns:
            return 0
        return round(statistics.pstdev(log_returns), 8)


class MakerTakerModel:
    """simulate maker vs taker execution strategies."""

    def __init__(self, maker_rebate=0.002, taker_fee=0.003):
        self.maker_rebate = maker_rebate
        self.taker_fee = taker_fee

    def maker_pnl(self, mid_price, spread, fill_rate, n_orders, hold_risk=0.01):
        """estimate maker strategy pnl.

        mid_price: current mid price
        spread: posted spread in price units
        fill_rate: fraction of orders that fill (0-1)
        n_orders: number of order pairs posted
        hold_risk: probability of adverse fill
        """
        half_spread = spread / 2
        gross_per_fill = half_spread
        rebate_per_fill = mid_price * self.maker_rebate
        adverse_cost = mid_price * hold_risk
        n_fills = int(n_orders * fill_rate)
        n_adverse = int(n_fills * hold_risk * 10)
        gross = n_fills * (gross_per_fill + rebate_per_fill)
        adverse = n_adverse * adverse_cost
        return {
            "gross_pnl": round(gross, 2),
            "adverse_cost": round(adverse, 2),
            "net_pnl": round(gross - adverse, 2),
            "fills": n_fills,
            "adverse_fills": n_adverse,
            "per_fill": round((gross - adverse) / n_fills, 4) if n_fills > 0 else 0,
        }

    def taker_pnl(self, entry_price, exit_price, size, holding_period_ms=100):
        """estimate taker strategy pnl for a single trade."""
        entry_cost = entry_price * self.taker_fee
        exit_cost = exit_price * self.taker_fee
        gross = (exit_price - entry_price) * size
        fees = (entry_cost + exit_cost) * size
        return {
            "gross_pnl": round(gross, 2),
            "fees": round(fees, 2),
            "net_pnl": round(gross - fees, 2),
            "holding_ms": holding_period_ms,
        }

    def compare_strategies(self, mid_price, spread, n_trades=1000):
        """compare maker vs taker profitability."""
        maker = self.maker_pnl(mid_price, spread, 0.3, n_trades)
        avg_move = spread * 2
        taker = self.taker_pnl(mid_price, mid_price + avg_move, 100, 500)
        taker_total = {
            "net_pnl": round(taker["net_pnl"] * n_trades * 0.4, 2),
            "win_rate": 0.4,
            "avg_pnl": taker["net_pnl"],
        }
        return {
            "maker": maker,
            "taker": taker_total,
            "spread_bps": round(spread / mid_price * 10000, 2),
            "recommendation": "maker" if maker["net_pnl"] > taker_total["net_pnl"] else "taker",
        }


if __name__ == "__main__":
    ob = OrderBookAnalyzer()
    bids = [(100.00, 500), (99.99, 300), (99.98, 800)]
    asks = [(100.01, 400), (100.02, 600), (100.03, 200)]
    ob.add_snapshot(bids, asks, "2022-04-15 10:00:00")
    print(f"spread: {ob.bid_ask_spread()}")
    print(f"imbalance: {ob.depth_imbalance()}")
    latency = LatencyModel("retail")
    print(f"tier comparison: {latency.compare_tiers(100.0)}")
    mt = MakerTakerModel()
    print(f"maker vs taker: {mt.compare_strategies(100.0, 0.02)}")
