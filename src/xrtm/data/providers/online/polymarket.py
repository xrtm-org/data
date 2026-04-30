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
Polymarket Gamma API data source.

This module provides a DataSource implementation that fetches forecast
questions from the Polymarket Gamma API.

Example:
    >>> from xrtm.data.providers.online import PolymarketSource
    >>> source = PolymarketSource()
    >>> questions = await source.fetch_questions(query="election", limit=5)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import TracebackType
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from xrtm.data.core import DataSource, DataSourceError, SourceFetchError, SourceTemporalIntegrityError
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase

logger = logging.getLogger(__name__)

__all__ = ["PolymarketSource"]

_LIVE_SNAPSHOT_TOLERANCE = timedelta(seconds=60)


class PolymarketSource(DataSource):
    r"""
    DataSource implementation that fetches from the Polymarket Gamma API.

    This provider connects to Polymarket's public Gamma API to retrieve
    event metadata for forecasting. For trade history with OrderFilled
    events, see the subgraph provider (to be added).

    Attributes:
        API_BASE: Base URL for the Polymarket Gamma API.

    Example:
        >>> source = PolymarketSource()
        >>> questions = await source.fetch_questions(limit=10)
        >>> print(f"Fetched {len(questions)} questions")
    """

    API_BASE = "https://gamma-api.polymarket.com"

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        *,
        raise_on_error: bool = False,
    ) -> None:
        self._session = session
        self._owns_session = False
        self.raise_on_error = raise_on_error
        self.last_error: Optional[DataSourceError] = None

    async def __aenter__(self) -> "PolymarketSource":
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None
            self._owns_session = False

    @asynccontextmanager
    async def _get_session(self):
        if self._session is not None and not self._session.closed:
            yield self._session
            return

        session = aiohttp.ClientSession()
        try:
            yield session
        finally:
            await session.close()

    def _fail(self, error: DataSourceError) -> None:
        self.last_error = error
        logger.error("%s", error)
        if self.raise_on_error:
            raise error

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _live_snapshot_time(self, snapshot_time: Optional[datetime]) -> datetime:
        request_time = datetime.now(timezone.utc)
        if snapshot_time is None:
            return request_time

        snapshot_utc = self._as_utc(snapshot_time)
        if snapshot_utc < request_time - _LIVE_SNAPSHOT_TOLERANCE:
            raise SourceTemporalIntegrityError(
                "Polymarket Gamma is a live-only API and cannot satisfy historical "
                f"snapshot_time={snapshot_utc.isoformat()} without future leakage."
            )
        if snapshot_utc > request_time + _LIVE_SNAPSHOT_TOLERANCE:
            raise SourceTemporalIntegrityError(
                f"snapshot_time={snapshot_utc.isoformat()} is in the future for a live Polymarket request."
            )
        return snapshot_utc

    async def fetch_questions(
        self,
        query: Optional[str] = None,
        limit: int = 5,
        *,
        snapshot_time: Optional[datetime] = None,
    ) -> List[ForecastQuestion]:
        r"""
        Fetch active forecast questions from Polymarket.

        Args:
            query: Optional search string to filter events.
            limit: Maximum number of questions to return.

        Returns:
            List of ForecastQuestion objects from active markets.
        """
        try:
            effective_snapshot_time = self._live_snapshot_time(snapshot_time)
        except SourceTemporalIntegrityError as e:
            self._fail(e)
            return []

        params = {"active": "true", "closed": "false", "limit": str(limit)}
        if query:
            params["search"] = query
        url = f"{self.API_BASE}/events?{urlencode(params)}"

        try:
            async with self._get_session() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        self._fail(SourceFetchError(f"Polymarket API returned status {resp.status} for events request."))
                        return []

                    data = await resp.json()
                    if not isinstance(data, list):
                        self._fail(SourceFetchError("Polymarket API returned a non-list events payload."))
                        return []

                    questions: list[ForecastQuestion] = []
                    for idx, item in enumerate(data):
                        if not isinstance(item, dict):
                            logger.warning("Skipping Polymarket event %s: item must be an object.", idx)
                            continue
                        try:
                            questions.append(self._normalize(item, effective_snapshot_time))
                        except (TypeError, ValueError) as e:
                            logger.warning("Skipping invalid Polymarket event %s: %s", idx, e)
                    self.last_error = None
                    return questions
        except (aiohttp.ClientError, TimeoutError, TypeError, ValueError) as e:
            self._fail(SourceFetchError(f"Failed to fetch questions from Polymarket: {e}"))
            return []

    async def get_question_by_id(
        self,
        question_id: str,
        *,
        snapshot_time: Optional[datetime] = None,
    ) -> Optional[ForecastQuestion]:
        r"""
        Retrieve a single Polymarket event by ID.

        Args:
            question_id: The unique event identifier.

        Returns:
            The ForecastQuestion if found, None otherwise.
        """
        try:
            effective_snapshot_time = self._live_snapshot_time(snapshot_time)
        except SourceTemporalIntegrityError as e:
            self._fail(e)
            return None

        url = f"{self.API_BASE}/events/{question_id}"
        try:
            async with self._get_session() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not isinstance(data, dict):
                            self._fail(SourceFetchError(f"Polymarket event {question_id} payload is not an object."))
                            return None
                        question = self._normalize(data, effective_snapshot_time)
                        self.last_error = None
                        return question
                    if resp.status != 404:
                        self._fail(
                            SourceFetchError(
                                f"Polymarket API returned status {resp.status} for event {question_id} request."
                            )
                        )
                    return None
        except (aiohttp.ClientError, TimeoutError, TypeError, ValueError) as e:
            self._fail(SourceFetchError(f"Failed to retrieve Polymarket event {question_id}: {e}"))
            return None

    def _normalize(self, item: Dict[str, Any], snapshot_time: datetime) -> ForecastQuestion:
        r"""
        Normalize Polymarket API response to ForecastQuestion schema.

        Args:
            item: Raw API response dict.

        Returns:
            Normalized ForecastQuestion instance.
        """
        return ForecastQuestion(
            id=str(item.get("id", "")),
            title=item.get("title", "Untitled Event"),
            description=item.get("description", ""),
            metadata=MetadataBase(
                tags=item.get("tags", []),
                snapshot_time=snapshot_time,
                subject_type="binary",
                source_version="polymarket-gamma-v1",
                raw_data=item,
                fetched_at=datetime.now(timezone.utc),
            ),
        )
