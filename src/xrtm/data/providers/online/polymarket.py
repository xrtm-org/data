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

r"""Polymarket data provider.

Fetches prediction market data from the Polymarket Gamma API.
The API is free and public for read access.

API docs: https://docs.polymarket.com/
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Any

from xrtm.data.core.interfaces import DataSource, DataSourceError, ResolutionSource
from xrtm.data.core.schemas.forecast import ForecastQuestion, MetadataBase
from xrtm.data.core.schemas.resolution import ResolvedQuestion

logger = logging.getLogger(__name__)

POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com"


class PolymarketSource(DataSource, ResolutionSource):
    r"""Data source for Polymarket prediction markets.

    Fetches open binary markets from the Polymarket Gamma API.
    No authentication required for read access.

    Args:
        api_base: Override the API base URL.

    Example:
        >>> source = PolymarketSource()
        >>> questions = await source.fetch_questions(limit=5)
    """

    def __init__(self, api_base: str = POLYMARKET_GAMMA_API):
        self.api_base = api_base.rstrip("/")

    async def fetch_questions(
        self,
        limit: int = 10,
        offset: int = 0,
        **kwargs: Any,
    ) -> list[ForecastQuestion]:
        r"""Fetch open binary markets from Polymarket.

        Args:
            limit: Maximum number of markets to return.
            offset: Pagination offset.
            **kwargs: Additional filters.

        Returns:
            List of ``ForecastQuestion`` objects.
        """
        url = (
            f"{self.api_base}/markets?"
            f"limit={min(limit, 100)}&offset={offset}"
            f"&closed=false&order=volume24hr&ascending=false"
        )
        try:
            data = self._get_json(url)
        except DataSourceError:
            # Gamma API may return a list directly
            url = f"{self.api_base}/events?limit={min(limit, 50)}&closed=false"
            data = self._get_json(url)

        # Gamma API may wrap in "markets" key or return list directly
        items = data if isinstance(data, list) else data.get("markets", data.get("results", []))

        questions = []
        for item in items[:limit]:
            try:
                questions.append(self._to_forecast_question(item))
            except Exception as exc:
                logger.warning(f"Skipping Polymarket market {item.get('id')}: {exc}")
        return questions

    async def get_question_by_id(self, question_id: str) -> ForecastQuestion | None:
        r"""Fetch a single Polymarket market by ID."""
        # Strip prefix if present
        market_id = question_id.replace("polymarket-", "")
        try:
            url = f"{self.api_base}/markets/{market_id}"
            data = self._get_json(url)
            return self._to_forecast_question(data)
        except Exception as exc:
            logger.warning(f"Polymarket market {market_id} not found: {exc}")
            return None

    async def fetch_resolved(
        self, limit: int = 50, *, since: "datetime | None" = None
    ) -> list[ResolvedQuestion]:
        r"""Fetch recently closed Polymarket markets with their outcomes.

        A closed market's ``outcomePrices`` converge to ``["1","0"]`` (YES) or
        ``["0","1"]`` (NO); anything above 0.5 on the first outcome counts as YES.
        """
        url = (
            f"{self.api_base}/markets?"
            f"limit={min(max(limit * 2, 20), 100)}&closed=true&order=endDate&ascending=false"
        )
        data = self._get_json(url)
        items = data if isinstance(data, list) else data.get("markets", data.get("results", []))

        resolved: list[ResolvedQuestion] = []
        for item in items:
            prices = self._coerce_prices(item.get("outcomePrices"))
            if len(prices) < 2:
                continue
            outcome = 1.0 if prices[0] > 0.5 else 0.0
            resolved_at = self._parse_iso(item.get("endDate") or item.get("closedTime"))
            if since is not None and resolved_at < since:
                continue

            market_id = str(item.get("id", ""))
            resolved.append(
                ResolvedQuestion(
                    question_id=f"polymarket-{market_id}",
                    venue="polymarket",
                    title=str(item.get("question", ""))[:500],
                    outcome=outcome,
                    resolved_at=resolved_at,
                    url=f"https://polymarket.com/event/{item.get('slug', market_id)}",
                    metadata=MetadataBase(
                        source_version="polymarket",
                        tags=["polymarket", "binary", "prediction-market"],
                        raw_data={"polymarket_id": market_id, "outcome_prices": prices},
                    ),
                )
            )
            if len(resolved) >= limit:
                break
        return resolved

    @staticmethod
    def _coerce_prices(raw: Any) -> list[float]:
        r"""Coerce ``outcomePrices`` (JSON string or list) into floats."""
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (ValueError, TypeError):
                return []
        if not isinstance(raw, list):
            return []
        prices: list[float] = []
        for value in raw:
            try:
                prices.append(float(value))
            except (TypeError, ValueError):
                return []
        return prices

    @staticmethod
    def _parse_iso(value: Any) -> datetime:
        r"""Parse an ISO-8601 timestamp into UTC (now when missing/invalid)."""
        if value is None:
            return datetime.now(timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)

    def _get_json(self, url: str) -> Any:
        r"""Fetch JSON from a URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "xrtm/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise DataSourceError(f"Polymarket API error: {exc}") from exc

    @staticmethod
    def _to_forecast_question(item: dict[str, Any]) -> ForecastQuestion:
        r"""Convert a Polymarket API market dict to ``ForecastQuestion``."""
        market_id = str(item.get("id", ""))
        question_text = item.get("question", "") or item.get("title", "") or ""
        description = item.get("description", "") or ""

        # Extract outcome prices if available
        outcomes = item.get("outcomes", []) or []
        outcome_prices = item.get("outcomePrices", []) or []
        price_info = ""
        if outcomes and outcome_prices and len(outcomes) == len(outcome_prices):
            parts = [f"{o}: {float(p)*100:.1f}%" for o, p in zip(outcomes, outcome_prices)]
            price_info = "Current prices: " + ", ".join(parts)

        close_time = item.get("endDate") or item.get("closeTime")
        snapshot_time = datetime.now(timezone.utc)
        if close_time:
            try:
                snapshot_time = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return ForecastQuestion(
            id=f"polymarket-{market_id}",
            title=question_text[:500],
            description=(
                f"{description[:1000]}\n\n{price_info}" if description or price_info
                else f"Polymarket binary market {market_id}. {price_info}"
            ),
            metadata=MetadataBase(
                snapshot_time=snapshot_time,
                source_version="polymarket",
                tags=["polymarket", "binary", "prediction-market"],
                raw_data={
                    "polymarket_id": market_id,
                    "volume_24hr": item.get("volume24hr"),
                    "liquidity": item.get("liquidity"),
                    "outcome_prices": outcome_prices,
                },
            ),
        )


__all__ = ["PolymarketSource"]
