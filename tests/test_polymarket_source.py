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

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from xrtm.data.core import SourceFetchError, SourceTemporalIntegrityError
from xrtm.data.providers.online.polymarket import PolymarketSource


class FakeResponse:
    def __init__(self, payload, status: int = 200):
        self._payload = payload
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload=None, status: int = 200):
        self.payload = payload or [{"id": "p1", "title": "Will local tests pass?", "description": "Smoke"}]
        self.status = status
        self.closed = False
        self.get_calls = 0

    def get(self, url):
        self.get_calls += 1
        if url.endswith("/events/p1"):
            return FakeResponse(self.payload[0], self.status)
        return FakeResponse(self.payload, self.status)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.close()

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_external_session_is_reused_and_not_closed():
    session = FakeSession()
    source = PolymarketSource(session=session)

    questions = await source.fetch_questions(limit=1)
    question = await source.get_question_by_id("p1")

    assert len(questions) == 1
    assert question is not None
    assert question.id == "p1"
    assert session.get_calls == 2
    assert session.closed is False


@pytest.mark.asyncio
async def test_context_manager_owns_and_closes_session():
    session = FakeSession()

    with patch("aiohttp.ClientSession", return_value=session):
        async with PolymarketSource() as source:
            questions = await source.fetch_questions(limit=1)
            assert len(questions) == 1
            assert session.closed is False

    assert session.closed is True


@pytest.mark.asyncio
async def test_closed_external_session_falls_back_to_one_off_session():
    closed_session = FakeSession()
    closed_session.closed = True
    replacement = FakeSession()

    source = PolymarketSource(session=closed_session)
    with patch("aiohttp.ClientSession", return_value=replacement):
        questions = await source.fetch_questions(limit=1)

    assert len(questions) == 1
    assert closed_session.get_calls == 0
    assert replacement.get_calls == 1
    assert replacement.closed is True


@pytest.mark.asyncio
async def test_successful_fetch_uses_one_snapshot_for_all_questions():
    payload = [
        {"id": "p1", "title": "Question 1", "description": "Smoke"},
        {"id": "p2", "title": "Question 2", "description": "Smoke"},
    ]
    source = PolymarketSource(session=FakeSession(payload=payload))

    questions = await source.fetch_questions(limit=2)

    assert len(questions) == 2
    assert questions[0].metadata.snapshot_time == questions[1].metadata.snapshot_time
    assert questions[0].metadata.snapshot_time.tzinfo == timezone.utc
    assert source.last_error is None


@pytest.mark.asyncio
async def test_historical_snapshot_is_rejected_without_live_fetch():
    session = FakeSession()
    source = PolymarketSource(session=session)

    questions = await source.fetch_questions(snapshot_time=datetime.now(timezone.utc) - timedelta(hours=1))

    assert questions == []
    assert session.get_calls == 0
    assert isinstance(source.last_error, SourceTemporalIntegrityError)


@pytest.mark.asyncio
async def test_source_failure_is_recorded_for_compatibility():
    source = PolymarketSource(session=FakeSession(status=503))

    questions = await source.fetch_questions(limit=1)

    assert questions == []
    assert isinstance(source.last_error, SourceFetchError)


@pytest.mark.asyncio
async def test_raise_on_error_surfaces_source_failure():
    source = PolymarketSource(session=FakeSession(status=503), raise_on_error=True)

    with pytest.raises(SourceFetchError):
        await source.fetch_questions(limit=1)
