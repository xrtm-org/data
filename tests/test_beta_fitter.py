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

r"""Unit tests for Beta distribution fitting."""

from datetime import datetime, timezone

import pytest

from xrtm.data.core.schemas import BetaPrior, TradeEvent
from xrtm.data.kit.processors import (
    fit_beta_exponential_decay,
    fit_beta_from_trades,
)


class TestBetaPrior:
    r"""Tests for BetaPrior schema."""

    def test_mean_calculation(self) -> None:
        r"""Verify mean = α / (α + β)."""
        prior = BetaPrior(alpha=7.0, beta=3.0)
        assert prior.mean == pytest.approx(0.7)

    def test_concentration_calculation(self) -> None:
        r"""Verify concentration = α + β."""
        prior = BetaPrior(alpha=7.0, beta=3.0)
        assert prior.concentration == 10.0

    def test_uniform_factory(self) -> None:
        r"""Verify uniform prior has α = β = 1."""
        prior = BetaPrior.uniform()
        assert prior.alpha == 1.0
        assert prior.beta == 1.0
        assert prior.mean == pytest.approx(0.5)

    def test_from_mean_concentration(self) -> None:
        r"""Verify factory from mean and concentration."""
        prior = BetaPrior.from_mean_concentration(0.7, 10.0)
        assert prior.alpha == pytest.approx(7.0)
        assert prior.beta == pytest.approx(3.0)


class TestFitBetaFromTrades:
    r"""Tests for fit_beta_from_trades function."""

    def _make_trade(self, price: float, amount: float, hours_ago: float = 0) -> TradeEvent:
        r"""Helper to create a trade event."""
        ts = datetime.now(timezone.utc)
        if hours_ago > 0:
            from datetime import timedelta
            ts = ts - timedelta(hours=hours_ago)
        return TradeEvent(
            price=price,
            amount=amount,
            timestamp=ts,
            maker="0xmaker",
            taker="0xtaker",
        )

    def test_empty_trades_returns_uniform(self) -> None:
        r"""Empty trade list should return uniform prior."""
        prior = fit_beta_from_trades([])
        assert prior.alpha == 1.0
        assert prior.beta == 1.0

    def test_single_trade_high_price(self) -> None:
        r"""Single high-price trade should favor Yes."""
        trades = [self._make_trade(price=0.9, amount=100)]
        prior = fit_beta_from_trades(trades)
        assert prior.mean > 0.5
        assert prior.alpha > prior.beta

    def test_single_trade_low_price(self) -> None:
        r"""Single low-price trade should favor No."""
        trades = [self._make_trade(price=0.1, amount=100)]
        prior = fit_beta_from_trades(trades)
        assert prior.mean < 0.5
        assert prior.beta > prior.alpha

    def test_volume_weighting(self) -> None:
        r"""Higher volume trades should have more influence."""
        # Small volume at 0.2, large volume at 0.8
        trades = [
            self._make_trade(price=0.2, amount=10),
            self._make_trade(price=0.8, amount=100),
        ]
        prior = fit_beta_from_trades(trades)
        # Should be closer to 0.8 due to volume weighting
        assert prior.mean > 0.5

    def test_minimum_concentration_enforced(self) -> None:
        r"""Should enforce minimum concentration."""
        trades = [self._make_trade(price=0.5, amount=1)]
        prior = fit_beta_from_trades(trades, scale=1000.0, min_concentration=10.0)
        assert prior.concentration >= 10.0


class TestFitBetaExponentialDecay:
    r"""Tests for exponential decay fitting."""

    def _make_trade(self, price: float, amount: float, hours_ago: float = 0) -> TradeEvent:
        r"""Helper to create a trade event."""
        from datetime import timedelta
        ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return TradeEvent(
            price=price,
            amount=amount,
            timestamp=ts,
            maker="0xmaker",
            taker="0xtaker",
        )

    def test_empty_trades_returns_uniform(self) -> None:
        r"""Empty trade list should return uniform prior."""
        prior = fit_beta_exponential_decay([])
        assert prior.alpha == 1.0
        assert prior.beta == 1.0

    def test_recent_trades_weighted_more(self) -> None:
        r"""Recent trades should have more influence than old ones."""
        # Old trade at 0.2, recent trade at 0.8
        trades = [
            self._make_trade(price=0.2, amount=100, hours_ago=48),  # Old
            self._make_trade(price=0.8, amount=100, hours_ago=0),   # Recent
        ]
        prior = fit_beta_exponential_decay(trades, half_life_hours=24.0)
        # Mean should be closer to 0.8 (recent trade weighted more)
        assert prior.mean > 0.5
