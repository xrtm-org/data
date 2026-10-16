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
async def test_manifold_snapshot_time_is_fetch_time(monkeypatch):
    from datetime import datetime, timedelta, timezone

    source = ManifoldSource()
    monkeypatch.setattr(
        source,
        "_get_json",
        lambda url: [
            {"id": "abc", "question": "Will X?", "isResolved": False, "closeTime": 4102444800000},  # year 2100
        ],
    )

    questions = await source.fetch_questions(limit=1)

    assert questions
    snapshot = questions[0].metadata.snapshot_time
    assert snapshot is not None
    # Snapshot must be the fetch time, never the (future) close time.
    assert snapshot <= datetime.now(timezone.utc) + timedelta(seconds=5)


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


@pytest.mark.asyncio
async def test_polymarket_fetch_resolved_paginates(monkeypatch):
    source = PolymarketSource()

    def fake(url: str):
        page_size = int(url.split("limit=")[1].split("&")[0])
        offset = int(url.split("offset=")[1].split("&")[0])
        return [
            {
                "id": str(index),
                "question": f"Q{index}",
                "outcomePrices": '["1", "0"]',
                "endDate": "2026-09-20T12:00:00Z",
            }
            for index in range(offset, offset + page_size)
        ]

    monkeypatch.setattr(source, "_get_json", fake)
    resolved = await source.fetch_resolved(limit=150)

    assert len(resolved) == 150
    assert resolved[0].question_id == "polymarket-0"
    assert resolved[-1].question_id == "polymarket-149"


@pytest.mark.asyncio
async def test_kalshi_fetch_resolved_paginates_cursor(monkeypatch):
    source = KalshiSource()
    calls = {"count": 0}

    def fake(url: str):
        calls["count"] += 1
        if "cursor=" in url:
            start, cursor = 200, ""
        else:
            start, cursor = 0, "next-page"
        return {
            "markets": [
                {
                    "ticker": f"T{index}",
                    "title": f"Q{index}",
                    "result": "yes",
                    "close_time": "2026-09-20T12:00:00Z",
                }
                for index in range(start, start + 200)
            ],
            "cursor": cursor,
        }

    monkeypatch.setattr(source, "_get_json", fake)
    resolved = await source.fetch_resolved(limit=250)

    assert len(resolved) == 250
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_polymarket_fetch_questions_fallback_uses_markets(monkeypatch):
    from xrtm.data.core import DataSourceError

    source = PolymarketSource()
    calls = {"urls": []}

    def _get_json(url):
        calls["urls"].append(url)
        if "order=volume24hr" in url:
            raise DataSourceError("volume ordering unsupported")
        return [
            {
                "id": "m1",
                "question": "Will X happen?",
                "description": "d",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.6", "0.4"]',
                "volume": 1000,
                "liquidity": 500,
                "endDate": "2026-12-31T00:00:00Z",
                "slug": "will-x",
                "closed": False,
            }
        ]

    monkeypatch.setattr(source, "_get_json", _get_json)

    questions = await source.fetch_questions(limit=1)

    assert len(calls["urls"]) == 2
    assert "/markets?" in calls["urls"][1]
    assert questions and questions[0].id == "polymarket-m1"


def test_fetch_json_retries_transient_failures(monkeypatch):
    from xrtm.data.providers.online import _http

    calls = {"n": 0}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def _urlopen(request, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("connection reset")
        return _Response()

    monkeypatch.setattr(_http.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(_http.time, "sleep", lambda _seconds: None)

    assert _http.fetch_json("https://example.test/x") == {"ok": True}
    assert calls["n"] == 3


def test_fetch_json_does_not_retry_client_errors(monkeypatch):
    import urllib.error

    from xrtm.data import DataSourceError
    from xrtm.data.providers.online import _http

    calls = {"n": 0}

    def _urlopen(request, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(_http.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(_http.time, "sleep", lambda _seconds: None)

    with pytest.raises(DataSourceError):
        _http.fetch_json("https://example.test/x")
    assert calls["n"] == 1
