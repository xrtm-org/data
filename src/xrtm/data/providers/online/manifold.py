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

r"""Manifold Markets data provider.

Fetches forecasting questions and resolutions from the Manifold Markets
public API. No API key is required for read access.

API docs: https://docs.manifold.markets/api
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

MANIFOLD_API_BASE = "https://api.manifold.markets/v0"


class ManifoldSource(DataSource, ResolutionSource):
    r"""Data source for Manifold Markets questions and resolutions.

    Example:
        >>> source = ManifoldSource()
        >>> questions = await source.fetch_questions(limit=5)
    """

    def __init__(self, api_base: str = MANIFOLD_API_BASE):
        self.api_base = api_base.rstrip("/")

    async def fetch_questions(
        self,
        query: Optional[str] = None,
        limit: int = 10,
        *,
        snapshot_time: Optional[datetime] = None,
    ) -> List[ForecastQuestion]:
        r"""Fetch open binary markets from Manifold."""
        del query, snapshot_time
        data = self._get_json(f"{self.api_base}/markets?limit={min(max(limit * 3, 50), 1000)}")
        items = data if isinstance(data, list) else data.get("markets", [])

        questions: List[ForecastQuestion] = []
        for item in items:
            if item.get("isResolved"):
                continue
            try:
                questions.append(self._to_forecast_question(item))
            except Exception as exc:  # noqa: BLE001 - skip malformed items
                logger.warning("Skipping Manifold market %s: %s", item.get("id"), exc)
            if len(questions) >= limit:
                break
        return questions

    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        r"""Fetch a single Manifold market by id."""
        del snapshot_time
        market_id = question_id.replace("manifold-", "")
        try:
            return self._to_forecast_question(self._get_json(f"{self.api_base}/market/{market_id}"))
        except Exception as exc:  # noqa: BLE001 - not found / network
            logger.warning("Manifold market %s not found: %s", market_id, exc)
            return None

    async def fetch_resolved(
        self, limit: int = 50, *, since: Optional[datetime] = None, max_pages: int = 5
    ) -> List[ResolvedQuestion]:
        r"""Fetch recently resolved binary markets from Manifold.

        Paginates with the ``before`` cursor until ``limit`` is reached, pages
        are exhausted, or ``max_pages`` is hit.
        """
        resolved: List[ResolvedQuestion] = []
        seen: set[str] = set()
        before: Optional[str] = None
        page_size = min(1000, max(limit * 2, 100))

        for _ in range(max(1, max_pages)):
            url = f"{self.api_base}/markets?limit={page_size}"
            if before:
                url += f"&before={before}"
            data = self._get_json(url)
            items = data if isinstance(data, list) else data.get("markets", [])
            if not items:
                break

            for item in items:
                if not item.get("isResolved"):
                    continue
                outcome = _manifold_outcome(item.get("resolution"))
                if outcome is None:
                    continue
                resolved_at = _parse_ts(item.get("resolutionTime"))
                if since is not None and resolved_at < since:
                    continue
                market_id = str(item.get("id", ""))
                if market_id in seen:
                    continue
                seen.add(market_id)
                resolved.append(
                    ResolvedQuestion(
                        question_id=f"manifold-{market_id}",
                        venue="manifold",
                        title=str(item.get("question", ""))[:500],
                        outcome=outcome,
                        resolved_at=resolved_at,
                        url=item.get("url"),
                        metadata=MetadataBase(
                            source_version="manifold",
                            tags=["manifold", "prediction-market"],
                            raw_data={
                                "manifold_id": market_id,
                                "resolution": item.get("resolution"),
                                "volume": item.get("volume"),
                            },
                        ),
                    )
                )
                if len(resolved) >= limit:
                    return resolved

            before = str(items[-1].get("id") or "") or None
            if not before:
                break

        return resolved

    def _get_json(self, url: str) -> Any:
        r"""Fetch JSON from a URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "xrtm/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise DataSourceError(f"Manifold API error: {exc}") from exc

    @staticmethod
    def _to_forecast_question(item: dict[str, Any]) -> ForecastQuestion:
        r"""Convert a Manifold market dict to ``ForecastQuestion``."""
        market_id = str(item.get("id", ""))
        probability = item.get("probability")
        price_info = f"Current probability: {float(probability)*100:.1f}%" if probability is not None else ""
        close_time = item.get("closeTime")

        return ForecastQuestion(
            id=f"manifold-{market_id}",
            title=str(item.get("question", ""))[:500],
            description=f"Manifold market {market_id}. {price_info}".strip(),
            metadata=MetadataBase(
                snapshot_time=_parse_ts(close_time) if close_time else datetime.now(timezone.utc),
                source_version="manifold",
                tags=["manifold", "binary", "prediction-market"],
                raw_data={
                    "manifold_id": market_id,
                    "probability": probability,
                    "volume": item.get("volume"),
                    "url": item.get("url"),
                },
            ),
        )


def _manifold_outcome(resolution: Any) -> Optional[float]:
    r"""Map a Manifold resolution string to an outcome on [0, 1]."""
    normalized = str(resolution or "").strip().upper()
    if normalized == "YES":
        return 1.0
    if normalized == "NO":
        return 0.0
    return None


def _parse_ts(value: Any) -> datetime:
    r"""Parse an ISO-8601 timestamp (or epoch millis) into UTC."""
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


__all__ = ["ManifoldSource"]
