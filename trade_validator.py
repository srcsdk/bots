#!/usr/bin/env python3
"""validate trades before execution"""


class TradeValidator:
    """enforce position limits and risk constraints on trades."""

    def __init__(self, max_position_pct=0.25, max_positions=10,
                 max_daily_trades=50):
        self.max_position_pct = max_position_pct
        self.max_positions = max_positions
        self.max_daily_trades = max_daily_trades
        self.daily_trade_count = 0

    def validate(self, trade, portfolio_value, current_positions):
        """check if trade passes all validation rules.

        returns (is_valid, reason) tuple.
        """
        if not trade:
            return False, "empty trade"

        action = trade.get("action", "")
        if action not in ("buy", "sell"):
            return False, f"invalid action: {action}"

        size = trade.get("size", 0)
        if not isinstance(size, (int, float)) or size <= 0:
            return False, f"invalid size: {size}"

        price = trade.get("price", 0)
        if price <= 0:
            return False, f"invalid price: {price}"

        if self.daily_trade_count >= self.max_daily_trades:
            return False, "daily trade limit reached"

        if action == "buy":
            trade_value = size * price
            if portfolio_value > 0:
                position_pct = trade_value / portfolio_value
                if position_pct > self.max_position_pct:
                    return False, (
                        f"position too large: {position_pct:.1%} "
                        f"> {self.max_position_pct:.1%}"
                    )

            if len(current_positions) >= self.max_positions:
                return False, f"max positions reached: {self.max_positions}"

        elif action == "sell":
            ticker = trade.get("ticker", trade.get("symbol", ""))
            if ticker and ticker not in current_positions:
                return False, f"no position in {ticker}"

        return True, "ok"

    def record_trade(self):
        """increment daily trade counter."""
        self.daily_trade_count += 1

    def reset_daily(self):
        """reset daily counters."""
        self.daily_trade_count = 0


if __name__ == "__main__":
    v = TradeValidator()
    valid, reason = v.validate(
        {"action": "buy", "size": 100, "price": 150.0},
        100000, {},
    )
    print(f"valid: {valid}, reason: {reason}")
