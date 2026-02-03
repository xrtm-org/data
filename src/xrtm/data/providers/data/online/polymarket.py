# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

import logging
from typing import Any, Dict, List, Optional

import aiohttp

from xrtm.data.providers.data.base import DataSource
from xrtm.data.schemas.forecast import ForecastQuestion, MetadataBase

logger = logging.getLogger(__name__)

__all__ = ["PolymarketSource"]


class PolymarketSource(DataSource):
    r"""
    DataSource implementation that fetches from the Polymarket Gamma API.
    """

    API_BASE = "https://gamma-api.polymarket.com"

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        super().__init__()
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def close(self):
        if self._session and not self._session.closed and self._owns_session:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        url = f"{self.API_BASE}/events?active=true&closed=false&limit={limit}"
        if query:
            url += f"&search={query}"

        try:
            session = await self._get_session()
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
        url = f"{self.API_BASE}/events/{question_id}"
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return self._normalize(await resp.json())
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve Polymarket event {question_id}: {e}")
            return None

    def _normalize(self, item: Dict[str, Any]) -> ForecastQuestion:
        return ForecastQuestion(
            id=str(item.get("id", "")),
            title=item.get("title", "Untitled Event"),
            content=item.get("description", ""),
            metadata=MetadataBase(
                tags=item.get("tags", []),
                subject_type="binary",
                source_version="polymarket-gamma-v1",
                raw_data=item,
            ),
        )
