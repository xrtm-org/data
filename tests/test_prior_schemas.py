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

r"""Unit tests for Prior schemas (BetaPrior, PriorState)."""

from datetime import datetime, timezone

import pytest

from xrtm.data.core.schemas import BetaPrior, PriorState


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

    def test_variance_calculation(self) -> None:
        r"""Verify variance formula: αβ / ((α+β)²(α+β+1))."""
        prior = BetaPrior(alpha=2.0, beta=2.0)
        # variance = 2*2 / (4*4*5) = 4/80 = 0.05
        assert prior.variance == pytest.approx(0.05)

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

    def test_credible_interval_90(self) -> None:
        r"""Verify 90% credible interval."""
        prior = BetaPrior(alpha=7.0, beta=3.0)
        low, high = prior.credible_interval(0.9)
        # 90% CI should contain the mean
        assert low < prior.mean < high
        # CI should be reasonably tight for concentrated distribution
        assert high - low < 0.6

    def test_credible_interval_50(self) -> None:
        r"""Verify 50% credible interval is tighter."""
        prior = BetaPrior(alpha=7.0, beta=3.0)
        low_90, high_90 = prior.credible_interval(0.9)
        low_50, high_50 = prior.credible_interval(0.5)
        # 50% CI should be tighter
        assert (high_50 - low_50) < (high_90 - low_90)

    def test_sample_mean_convergence(self) -> None:
        r"""Verify samples converge to distribution mean."""
        prior = BetaPrior(alpha=7.0, beta=3.0)
        samples = prior.sample(1000)
        sample_mean = sum(samples) / len(samples)
        assert sample_mean == pytest.approx(prior.mean, abs=0.05)

    def test_to_distribution_dict(self) -> None:
        r"""Verify governance schema format."""
        prior = BetaPrior(alpha=7.0, beta=3.0)
        d = prior.to_distribution_dict()
        assert d["family"] == "beta"
        assert d["alpha"] == 7.0
        assert d["beta"] == 3.0
        assert "credible_interval" in d
        assert d["credible_interval"]["level"] == 0.9

    def test_validation_alpha_positive(self) -> None:
        r"""Alpha must be positive."""
        with pytest.raises(ValueError):
            BetaPrior(alpha=-1.0, beta=1.0)

    def test_validation_beta_positive(self) -> None:
        r"""Beta must be positive."""
        with pytest.raises(ValueError):
            BetaPrior(alpha=1.0, beta=0.0)


class TestPriorState:
    r"""Tests for PriorState schema."""

    def test_uninformative_factory(self) -> None:
        r"""Verify uninformative prior state."""
        state = PriorState.uninformative()
        assert state.prior.alpha == 1.0
        assert state.prior.beta == 1.0
        assert state.silence_delta == 0.0
        assert state.deadline_delta == 1.0

    def test_full_state_creation(self) -> None:
        r"""Verify full state creation."""
        now = datetime.now(timezone.utc)
        state = PriorState(
            prior=BetaPrior(alpha=7.0, beta=3.0),
            silence_delta=0.5,
            deadline_delta=0.3,
            snapshot_time=now,
        )
        assert state.prior.mean == pytest.approx(0.7)
        assert state.silence_delta == 0.5
        assert state.deadline_delta == 0.3
        assert state.snapshot_time == now

    def test_silence_delta_range(self) -> None:
        r"""Silence delta must be in [0, 1]."""
        with pytest.raises(ValueError):
            PriorState(
                prior=BetaPrior.uniform(),
                silence_delta=1.5,
            )

    def test_deadline_delta_range(self) -> None:
        r"""Deadline delta must be in [0, 1]."""
        with pytest.raises(ValueError):
            PriorState(
                prior=BetaPrior.uniform(),
                deadline_delta=-0.1,
            )


class TestTradeEvent:
    r"""Tests for TradeEvent schema."""

    def test_trade_weights(self) -> None:
        r"""Verify yes/no weight calculations."""
        from xrtm.data.core.schemas import TradeEvent

        trade = TradeEvent(
            price=0.7,
            amount=100.0,
            timestamp=datetime.now(timezone.utc),
            maker="0xmaker",
            taker="0xtaker",
        )
        assert trade.yes_weight == pytest.approx(70.0)
        assert trade.no_weight == pytest.approx(30.0)

    def test_price_range_validation(self) -> None:
        r"""Price must be in [0, 1]."""
        from xrtm.data.core.schemas import TradeEvent

        with pytest.raises(ValueError):
            TradeEvent(
                price=1.5,
                amount=100.0,
                timestamp=datetime.now(timezone.utc),
                maker="0x",
                taker="0x",
            )


class TestTradeWindow:
    r"""Tests for TradeWindow schema."""

    def test_volume_weighted_price(self) -> None:
        r"""Verify VWAP calculation."""
        from xrtm.data.core.schemas import TradeEvent, TradeWindow

        now = datetime.now(timezone.utc)
        trades = [
            TradeEvent(price=0.6, amount=100, timestamp=now, maker="m", taker="t"),
            TradeEvent(price=0.8, amount=200, timestamp=now, maker="m", taker="t"),
        ]
        window = TradeWindow(
            trades=trades,
            start_time=now,
            end_time=now,
            market_id="test",
        )
        # VWAP = (0.6*100 + 0.8*200) / 300 = 220/300 = 0.733...
        assert window.volume_weighted_price == pytest.approx(0.7333, rel=0.01)
        assert window.total_volume == 300.0
        assert window.trade_count == 2
