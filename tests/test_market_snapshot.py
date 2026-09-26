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

r"""Tests for the MarketSnapshot schema."""

from datetime import datetime, timezone

import pytest

from xrtm.data import MarketSnapshot


def test_snapshot_normalizes_naive_time_to_utc():
    snapshot = MarketSnapshot(market_id="m1", snapshot_time=datetime(2026, 9, 26, 12, 0))
    assert snapshot.snapshot_time.tzinfo == timezone.utc


def test_spread_is_derived_from_book():
    snapshot = MarketSnapshot(market_id="m2", best_bid=0.40, best_ask=0.44)
    assert snapshot.spread == pytest.approx(0.04)


def test_explicit_spread_is_preserved():
    snapshot = MarketSnapshot(market_id="m3", best_bid=0.40, best_ask=0.44, spread=0.05)
    assert snapshot.spread == pytest.approx(0.05)


def test_crossed_book_is_rejected():
    with pytest.raises(ValueError, match="best_bid"):
        MarketSnapshot(market_id="m4", best_bid=0.60, best_ask=0.50)


def test_snapshot_serializes_and_round_trips():
    snapshot = MarketSnapshot(
        market_id="m5",
        question_id="q5",
        probability=0.42,
        best_bid=0.41,
        best_ask=0.43,
        volume_24h=150_000,
        liquidity=20_000,
        source="polymarket",
        raw_data={"token_id": "123"},
    )
    payload = snapshot.model_dump(mode="json")
    assert payload["spread"] == pytest.approx(0.02)

    reloaded = MarketSnapshot.model_validate(payload)
    assert reloaded.market_id == "m5"
    assert reloaded.question_id == "q5"
    assert reloaded.raw_data == {"token_id": "123"}
