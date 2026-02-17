#!/usr/bin/env python3
# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

r"""
Example: Fitting Beta Distributions from Trade Data.

This example demonstrates how to:
1. Create mock trade events
2. Fit a Beta distribution from the trades
3. Interpret the resulting prior state

Run:
    python examples/fit_beta_from_trades.py
"""

from datetime import datetime, timedelta, timezone

from xrtm.data.core.schemas import PriorState, TradeEvent, TradeWindow
from xrtm.data.kit.processors import fit_beta_exponential_decay, fit_beta_from_trades


def create_mock_trades() -> list[TradeEvent]:
    r"""Create mock trade data simulating market activity."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=24)

    # Simulate trades showing increasing confidence in YES outcome
    trades = [
        # Early trades: mixed signals
        TradeEvent(price=0.45, amount=50.0, timestamp=base_time, maker="0xa", taker="0xb"),
        TradeEvent(price=0.52, amount=75.0, timestamp=base_time + timedelta(hours=2), maker="0xc", taker="0xd"),
        # Mid trades: leaning YES
        TradeEvent(price=0.65, amount=100.0, timestamp=base_time + timedelta(hours=6), maker="0xe", taker="0xf"),
        TradeEvent(price=0.68, amount=150.0, timestamp=base_time + timedelta(hours=10), maker="0xg", taker="0xh"),
        # Recent trades: strong YES conviction
        TradeEvent(price=0.78, amount=200.0, timestamp=base_time + timedelta(hours=20), maker="0xi", taker="0xj"),
        TradeEvent(price=0.82, amount=250.0, timestamp=base_time + timedelta(hours=23), maker="0xk", taker="0xl"),
    ]
    return trades


def main() -> None:
    r"""Demonstrate Beta fitting from trade data."""
    print("=" * 60)
    print("Beta Distribution Fitting from Trade Data")
    print("=" * 60)

    # Create mock trades
    trades = create_mock_trades()
    print(f"\nCreated {len(trades)} mock trades")

    # Calculate some statistics
    total_volume = sum(t.amount for t in trades)
    vwap = sum(t.price * t.amount for t in trades) / total_volume
    print(f"Total volume: ${total_volume:.2f}")
    print(f"Volume-weighted avg price (VWAP): {vwap:.3f}")

    # Fit Beta distribution (uniform weighting)
    print("\n--- Standard Beta Fit (uniform time weighting) ---")
    prior = fit_beta_from_trades(trades)
    print(f"Fitted: α = {prior.alpha:.2f}, β = {prior.beta:.2f}")
    print(f"Mean (implied probability): {prior.mean:.3f}")
    print(f"Concentration (confidence): {prior.concentration:.2f}")

    # Fit with exponential decay (recent trades weighted more)
    print("\n--- Exponential Decay Fit (12h half-life) ---")
    prior_decay = fit_beta_exponential_decay(trades, half_life_hours=12.0)
    print(f"Fitted: α = {prior_decay.alpha:.2f}, β = {prior_decay.beta:.2f}")
    print(f"Mean (implied probability): {prior_decay.mean:.3f}")
    print(f"Concentration (confidence): {prior_decay.concentration:.2f}")

    # Create a full PriorState
    print("\n--- Full Prior State ---")
    state = PriorState(
        prior=prior_decay,
        silence_delta=0.1,  # Recent activity
        deadline_delta=0.3,  # 30% time remaining
        snapshot_time=datetime.now(timezone.utc),
    )
    print(f"Prior: Beta({state.prior.alpha:.2f}, {state.prior.beta:.2f})")
    print(f"Silence delta: {state.silence_delta} (recent activity)")
    print(f"Deadline delta: {state.deadline_delta} (30% time remaining)")

    # Demonstrate TradeWindow
    print("\n--- TradeWindow Summary ---")
    window = TradeWindow(
        trades=trades,
        start_time=trades[0].timestamp,
        end_time=trades[-1].timestamp,
        market_id="example_market",
    )
    print(f"Window: {window.trade_count} trades, ${window.total_volume:.2f} volume")
    print(f"VWAP from window: {window.volume_weighted_price:.3f}")

    print("\n" + "=" * 60)
    print("Example complete!")


if __name__ == "__main__":
    main()
