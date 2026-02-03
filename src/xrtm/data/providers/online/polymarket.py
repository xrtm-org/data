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
from typing import Any, Dict, List, Optional

import aiohttp

from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase

logger = logging.getLogger(__name__)

__all__ = ["PolymarketSource"]


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

    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        r"""
        Fetch active forecast questions from Polymarket.

        Args:
            query: Optional search string to filter events.
            limit: Maximum number of questions to return.

        Returns:
            List of ForecastQuestion objects from active markets.
        """
        url = f"{self.API_BASE}/events?active=true&closed=false&limit={limit}"
        if query:
            url += f"&search={query}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Polymarket API returned status {resp.status}")
                        return []

                    data = await resp.json()
                    questions = []
                    for item in data:
                        questions.append(self._normalize(item))
                    return questions
        except Exception as e:
            logger.error(f"Failed to fetch questions from Polymarket: {e}")
            return []

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        r"""
        Retrieve a single Polymarket event by ID.

        Args:
            question_id: The unique event identifier.

        Returns:
            The ForecastQuestion if found, None otherwise.
        """
        url = f"{self.API_BASE}/events/{question_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return self._normalize(await resp.json())
                    return None
        except Exception as e:
            logger.error(f"Failed to retrieve Polymarket event {question_id}: {e}")
            return None

    def _normalize(self, item: Dict[str, Any]) -> ForecastQuestion:
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
                subject_type="binary",
                source_version="polymarket-gamma-v1",
                raw_data=item,
            ),
        )
