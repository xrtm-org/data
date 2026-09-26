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

r"""Kalshi data provider.

Fetches forecasting markets and settlements from the Kalshi public read API.
No authentication is required for market data.

API docs: https://trading-api.readme.io/
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Any, List, Optional

from xrtm.data.core.interfaces import DataSource, DataSourceError, ResolutionSource
from xrtm.data.core.schemas.forecast import ForecastQuestion, MetadataBase
from xrtm.data.core.schemas.resolution import ResolvedQuestion

logger = logging.getLogger(__name__)

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiSource(DataSource, ResolutionSource):
    r"""Data source for Kalshi markets and settlements.

    Example:
        >>> source = KalshiSource()
        >>> questions = await source.fetch_questions(limit=5)
    """

    def __init__(self, api_base: str = KALSHI_API_BASE):
        self.api_base = api_base.rstrip("/")

    async def fetch_questions(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        *,
        snapshot_time: Optional[datetime] = None,
    ) -> List[ForecastQuestion]:
        r"""Fetch open markets from Kalshi."""
        del query, snapshot_time
        data = self._get_json(f"{self.api_base}/markets?limit={min(max(limit * 2, 20), 200)}&status=open")
        items = data.get("markets", []) if isinstance(data, dict) else data

        questions: List[ForecastQuestion] = []
        for item in items:
            try:
                questions.append(self._to_forecast_question(item))
            except Exception as exc:  # noqa: BLE001 - skip malformed items
                logger.warning("Skipping Kalshi market %s: %s", item.get("ticker"), exc)
            if len(questions) >= limit:
                break
        return questions

    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        r"""Fetch a single Kalshi market by ticker."""
        del snapshot_time
        ticker = question_id.replace("kalshi-", "")
        try:
            data = self._get_json(f"{self.api_base}/markets/{ticker}")
            market = data.get("market", data)
            return self._to_forecast_question(market)
        except Exception as exc:  # noqa: BLE001 - not found / network
            logger.warning("Kalshi market %s not found: %s", ticker, exc)
            return None

    async def fetch_resolved(
        self, limit: int = 50, *, since: Optional[datetime] = None, max_pages: int = 5
    ) -> List[ResolvedQuestion]:
        r"""Fetch settled markets from Kalshi.

        Paginates with the API ``cursor`` until ``limit`` is reached, pages are
        exhausted, or ``max_pages`` is hit.
        """
        page_size = min(200, max(limit, 50))
        cursor = ""
        resolved: List[ResolvedQuestion] = []
        seen: set[str] = set()

        for _ in range(max(1, max_pages)):
            url = f"{self.api_base}/markets?limit={page_size}&status=settled"
            if cursor:
                url += f"&cursor={cursor}"
            data = self._get_json(url)
            items = data.get("markets", []) if isinstance(data, dict) else data
            if not items:
                break

            for item in items:
                outcome = _kalshi_outcome(item.get("result"))
                if outcome is None:
                    continue
                resolved_at = _parse_ts(item.get("close_time") or item.get("expiration_time"))
                if since is not None and resolved_at < since:
                    continue
                ticker = str(item.get("ticker", ""))
                if ticker in seen:
                    continue
                seen.add(ticker)
                resolved.append(
                    ResolvedQuestion(
                        question_id=f"kalshi-{ticker}",
                        venue="kalshi",
                        title=str(item.get("title", ""))[:500],
                        outcome=outcome,
                        resolved_at=resolved_at,
                        url=f"https://kalshi.com/markets/{ticker}",
                        metadata=MetadataBase(
                            source_version="kalshi",
                            tags=["kalshi", "prediction-market"],
                            raw_data={
                                "ticker": ticker,
                                "event_ticker": item.get("event_ticker"),
                                "result": item.get("result"),
                                "volume": item.get("volume"),
                            },
                        ),
                    )
                )
                if len(resolved) >= limit:
                    return resolved

            cursor = str(data.get("cursor") or "") if isinstance(data, dict) else ""
            if not cursor:
                break

        return resolved

    def _get_json(self, url: str) -> Any:
        r"""Fetch JSON from a URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "xrtm/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise DataSourceError(f"Kalshi API error: {exc}") from exc

    @staticmethod
    def _to_forecast_question(item: dict[str, Any]) -> ForecastQuestion:
        r"""Convert a Kalshi market dict to ``ForecastQuestion``."""
        ticker = str(item.get("ticker", ""))
        title = str(item.get("title", "") or item.get("subtitle", ""))
        subtitle = str(item.get("subtitle", "") or "")

        yes_bid = item.get("yes_bid")
        yes_ask = item.get("yes_ask")
        price_info = ""
        if yes_bid is not None or yes_ask is not None:
            mid = None
            if yes_bid is not None and yes_ask is not None:
                mid = (float(yes_bid) + float(yes_ask)) / 200.0
            price_info = f"Current yes price: {mid*100:.1f}%" if mid is not None else f"yes bid/ask: {yes_bid}/{yes_ask}"

        return ForecastQuestion(
            id=f"kalshi-{ticker}",
            title=title[:500] or ticker,
            description=f"{subtitle[:500]}\n\n{price_info}".strip(),
            metadata=MetadataBase(
                snapshot_time=_parse_ts(item.get("close_time")) if item.get("close_time") else datetime.now(timezone.utc),
                source_version="kalshi",
                tags=["kalshi", "binary", "prediction-market"],
                raw_data={
                    "ticker": ticker,
                    "event_ticker": item.get("event_ticker"),
                    "volume": item.get("volume"),
                    "open_interest": item.get("open_interest"),
                },
            ),
        )


def _kalshi_outcome(result: Any) -> Optional[float]:
    r"""Map a Kalshi settlement result to an outcome on [0, 1]."""
    normalized = str(result or "").strip().lower()
    if normalized == "yes":
        return 1.0
    if normalized == "no":
        return 0.0
    return None


def _parse_ts(value: Any) -> datetime:
    r"""Parse an ISO-8601 timestamp into UTC."""
    if value is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


__all__ = ["KalshiSource"]
