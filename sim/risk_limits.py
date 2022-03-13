#!/usr/bin/env python3
"""enforce risk limits and circuit breakers"""


class RiskLimits:
    """enforce trading risk limits."""

    def __init__(self, max_daily_loss_pct=2.0, max_position_pct=20.0,
                 max_open_positions=10, max_daily_trades=50):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_position_pct = max_position_pct
        self.max_open_positions = max_open_positions
        self.max_daily_trades = max_daily_trades
        self.daily_pnl = 0
        self.daily_trades = 0
        self.circuit_breaker = False
        self.violations = []

    def check_order(self, order, portfolio_value, open_positions):
        """check if an order violates risk limits."""
        if self.circuit_breaker:
            return False, "circuit breaker active"
        if self.daily_trades >= self.max_daily_trades:
            self._add_violation("max daily trades exceeded")
            return False, "max daily trades exceeded"
        if len(open_positions) >= self.max_open_positions:
            if order.get("action") == "buy":
                return False, "max open positions reached"
        order_value = order.get("shares", 0) * order.get("price", 0)
        if portfolio_value > 0:
            order_pct = (order_value / portfolio_value) * 100
            if order_pct > self.max_position_pct:
                self._add_violation("position size too large")
                return False, "position exceeds max percentage"
        return True, "ok"

    def update_pnl(self, pnl, portfolio_value):
        """update daily pnl and check for circuit breaker."""
        self.daily_pnl += pnl
        if portfolio_value > 0:
            loss_pct = abs(min(0, self.daily_pnl)) / portfolio_value * 100
            if loss_pct >= self.max_daily_loss_pct:
                self.circuit_breaker = True
                self._add_violation("daily loss limit hit")

    def record_trade(self):
        """record a completed trade."""
        self.daily_trades += 1

    def reset_daily(self):
        """reset daily counters."""
        self.daily_pnl = 0
        self.daily_trades = 0
        self.circuit_breaker = False

    def _add_violation(self, message):
        self.violations.append(message)

    def status(self):
        """return current risk status."""
        return {
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_trades": self.daily_trades,
            "circuit_breaker": self.circuit_breaker,
            "violations": len(self.violations),
        }


if __name__ == "__main__":
    limits = RiskLimits(max_daily_loss_pct=2.0, max_daily_trades=5)
    portfolio = 100000
    order = {"action": "buy", "shares": 100, "price": 150.0}
    allowed, reason = limits.check_order(order, portfolio, [])
    print(f"order check: {allowed} ({reason})")
    limits.update_pnl(-2100, portfolio)
    print(f"status: {limits.status()}")
