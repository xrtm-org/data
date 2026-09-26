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

r"""Hermetic tests for online venue sources (mocked HTTP)."""

from datetime import timezone

import pytest

from xrtm.data.core.interfaces import DataSourceError, ResolutionSource
from xrtm.data.providers.online import KalshiSource, ManifoldSource, MetaculusSource, PolymarketSource


def test_sources_implement_resolution_interface():
    for source in (ManifoldSource(), KalshiSource(), PolymarketSource(), MetaculusSource(api_key="x")):
        assert isinstance(source, ResolutionSource)


@pytest.mark.asyncio
async def test_manifold_fetch_resolved_maps_yes_no(monkeypatch):
    source = ManifoldSource()
    monkeypatch.setattr(
        source,
        "_get_json",
        lambda url: [
            {
                "id": "abc",
                "question": "Will X?",
                "isResolved": True,
                "resolution": "YES",
                "resolutionTime": 1758888000000,
                "url": "https://manifold.markets/x",
            },
            {"id": "def", "question": "Will Y?", "isResolved": True, "resolution": "CANCEL"},
            {"id": "ghi", "question": "Open?", "isResolved": False},
        ],
    )

    resolved = await source.fetch_resolved(limit=10)

    assert len(resolved) == 1
    assert resolved[0].question_id == "manifold-abc"
    assert resolved[0].outcome == 1.0
    assert resolved[0].resolved_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_kalshi_fetch_resolved_maps_result(monkeypatch):
    source = KalshiSource()
    monkeypatch.setattr(
        source,
        "_get_json",
        lambda url: {
            "markets": [
                {
                    "ticker": "KXTEST-26",
                    "title": "Will Z?",
                    "status": "settled",
                    "result": "no",
                    "close_time": "2026-09-20T12:00:00Z",
                },
                {"ticker": "KXOPEN", "title": "Open", "status": "open", "result": ""},
            ]
        },
    )

    resolved = await source.fetch_resolved(limit=10)

    assert len(resolved) == 1
    assert resolved[0].question_id == "kalshi-KXTEST-26"
    assert resolved[0].outcome == 0.0


@pytest.mark.asyncio
async def test_polymarket_fetch_resolved_uses_outcome_prices(monkeypatch):
    source = PolymarketSource()
    monkeypatch.setattr(
        source,
        "_get_json",
        lambda url: [
            {
                "id": "123",
                "question": "Will A?",
                "outcomePrices": '["1", "0"]',
                "endDate": "2026-09-20T12:00:00Z",
            },
            {
                "id": "456",
                "question": "Will B?",
                "outcomePrices": ["0.02", "0.98"],
                "endDate": "2026-09-20T12:00:00Z",
            },
        ],
    )

    resolved = await source.fetch_resolved(limit=10)

    assert [r.outcome for r in resolved] == [1.0, 0.0]
    assert resolved[0].question_id == "polymarket-123"


@pytest.mark.asyncio
async def test_metaculus_fetch_resolved_requires_api_key():
    source = MetaculusSource(api_key="")
    with pytest.raises(DataSourceError):
        await source.fetch_resolved(limit=5)
