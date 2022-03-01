#!/usr/bin/env python3
"""detailed trade logging with entry/exit tracking"""



class TradeLog:
    """track individual trades with entry/exit details."""

    def __init__(self):
        self.open_trades = {}
        self.closed_trades = []

    def open_trade(self, symbol, shares, entry_price, date, strategy=""):
        """record a new trade entry."""
        trade = {
            "symbol": symbol,
            "shares": shares,
            "entry_price": entry_price,
            "entry_date": date,
            "strategy": strategy,
            "status": "open",
        }
        self.open_trades[symbol] = trade
        return trade

    def close_trade(self, symbol, exit_price, date):
        """close an open trade and calculate pnl."""
        trade = self.open_trades.pop(symbol, None)
        if trade is None:
            return None
        trade["exit_price"] = exit_price
        trade["exit_date"] = date
        trade["pnl"] = round(
            (exit_price - trade["entry_price"]) * trade["shares"], 2
        )
        trade["pnl_pct"] = round(
            (exit_price / trade["entry_price"] - 1) * 100, 2
        )
        trade["status"] = "closed"
        self.closed_trades.append(trade)
        return trade

    def summary(self):
        """generate trade log summary."""
        if not self.closed_trades:
            return {"total_trades": 0}
        pnls = [t["pnl"] for t in self.closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        return {
            "total_trades": len(self.closed_trades),
            "open_trades": len(self.open_trades),
            "total_pnl": round(sum(pnls), 2),
            "win_rate": round(len(wins) / len(pnls) * 100, 1),
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
            "best_trade": round(max(pnls), 2),
            "worst_trade": round(min(pnls), 2),
        }

    def by_strategy(self):
        """group trade results by strategy."""
        by_strat = {}
        for trade in self.closed_trades:
            strat = trade.get("strategy", "unknown")
            by_strat.setdefault(strat, []).append(trade)
        results = {}
        for strat, trades in by_strat.items():
            pnls = [t["pnl"] for t in trades]
            results[strat] = {
                "trades": len(trades),
                "total_pnl": round(sum(pnls), 2),
                "avg_pnl": round(sum(pnls) / len(pnls), 2),
            }
        return results


if __name__ == "__main__":
    log = TradeLog()
    log.open_trade("AAPL", 100, 150.0, "2022-01-03", "momentum")
    log.close_trade("AAPL", 158.0, "2022-01-15")
    log.open_trade("MSFT", 50, 300.0, "2022-01-05", "mean_rev")
    log.close_trade("MSFT", 295.0, "2022-01-20")
    summary = log.summary()
    print(f"total pnl: ${summary['total_pnl']}")
    print(f"win rate: {summary['win_rate']}%")
