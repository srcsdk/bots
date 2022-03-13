#!/usr/bin/env python3
"""configuration management for backtesting framework"""

import json
import os


DEFAULT_CONFIG = {
    "initial_capital": 100000,
    "commission": 1.0,
    "slippage_bps": 5,
    "risk_per_trade_pct": 1.0,
    "max_position_pct": 20.0,
    "max_daily_loss_pct": 2.0,
    "max_open_positions": 10,
    "data_dir": "data",
    "results_dir": "results",
    "log_level": "info",
}


def load_config(path="sim_config.json"):
    """load simulation config with defaults."""
    config = dict(DEFAULT_CONFIG)
    if os.path.isfile(path):
        with open(path) as f:
            user = json.load(f)
        config.update(user)
    return config


def save_config(config, path="sim_config.json"):
    """save simulation config."""
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def validate(config):
    """validate config values."""
    errors = []
    if config.get("initial_capital", 0) <= 0:
        errors.append("initial_capital must be positive")
    if config.get("commission", 0) < 0:
        errors.append("commission cannot be negative")
    if not 0 < config.get("risk_per_trade_pct", 0) <= 100:
        errors.append("risk_per_trade_pct must be 0-100")
    if not 0 < config.get("max_position_pct", 0) <= 100:
        errors.append("max_position_pct must be 0-100")
    return errors


if __name__ == "__main__":
    config = load_config()
    print("sim config:")
    for k, v in config.items():
        print(f"  {k}: {v}")
    errors = validate(config)
    if errors:
        print(f"errors: {errors}")
    else:
        print("config valid")
