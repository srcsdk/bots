#!/usr/bin/env python3
"""store and query strategy performance data"""

import json
import sqlite3


class PerformanceDB:
    """sqlite database for strategy performance tracking."""

    def __init__(self, db_path="performance.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """create tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                config TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                strategy_id INTEGER,
                start_date TEXT,
                end_date TEXT,
                total_return REAL,
                sharpe REAL,
                max_drawdown REAL,
                win_rate REAL,
                total_trades INTEGER,
                run_at REAL,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id)
            );
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                run_id INTEGER,
                symbol TEXT,
                entry_date TEXT,
                exit_date TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );
        """)

    def add_strategy(self, name, config=None):
        """register a strategy."""
        import time
        self.conn.execute(
            "INSERT OR IGNORE INTO strategies (name, config, created_at) "
            "VALUES (?, ?, ?)",
            (name, json.dumps(config or {}), time.time()),
        )
        self.conn.commit()
        cursor = self.conn.execute(
            "SELECT id FROM strategies WHERE name=?", (name,)
        )
        return cursor.fetchone()[0]

    def record_run(self, strategy_id, results):
        """record a backtest run."""
        import time
        cursor = self.conn.execute(
            "INSERT INTO runs (strategy_id, start_date, end_date, "
            "total_return, sharpe, max_drawdown, win_rate, "
            "total_trades, run_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                strategy_id,
                results.get("start_date", ""),
                results.get("end_date", ""),
                results.get("total_return_pct", 0),
                results.get("sharpe", 0),
                results.get("max_drawdown_pct", 0),
                results.get("win_rate", 0),
                results.get("total_trades", 0),
                time.time(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_best_strategies(self, metric="total_return", limit=10):
        """get best performing strategies by metric."""
        query = f"""
            SELECT s.name, r.total_return, r.sharpe, r.max_drawdown,
                   r.win_rate, r.total_trades
            FROM runs r JOIN strategies s ON r.strategy_id = s.id
            ORDER BY r.{metric} DESC LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def strategy_history(self, strategy_name):
        """get run history for a strategy."""
        cursor = self.conn.execute(
            "SELECT r.* FROM runs r JOIN strategies s "
            "ON r.strategy_id = s.id WHERE s.name=? ORDER BY r.run_at",
            (strategy_name,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


if __name__ == "__main__":
    db = PerformanceDB(":memory:")
    db.connect()
    sid = db.add_strategy("test_rsi", config={"period": 14})
    db.record_run(sid, {
        "total_return_pct": 25.5, "sharpe": 1.8,
        "max_drawdown_pct": 12.0, "win_rate": 62.0, "total_trades": 150,
    })
    best = db.get_best_strategies()
    print(f"best strategies: {len(best)}")
    for s in best:
        print(f"  {s['name']}: {s['total_return']}%")
    db.close()
