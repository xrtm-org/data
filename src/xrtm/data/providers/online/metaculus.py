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

r"""Metaculus data provider.

Fetches forecasting questions from the Metaculus API.
Requires a Metaculus API key (free account). Set ``METACULUS_API_KEY``
environment variable or pass ``api_key`` to the constructor.

Get a key: https://www.metaculus.com/accounts/signup/
API docs: https://www.metaculus.com/api2/
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

METACULUS_API_BASE = "https://www.metaculus.com/api2"


class MetaculusSource(DataSource, ResolutionSource):
    r"""Data source for Metaculus forecasting questions.

    Fetches open binary questions from the Metaculus API.
    Requires a Metaculus API key. Set ``METACULUS_API_KEY`` env var
    or pass ``api_key`` to the constructor.
    (Free account at https://www.metaculus.com/accounts/signup/)

    Example:
        >>> source = MetaculusSource(api_key="...")
        >>> questions = await source.fetch_questions(limit=5)
    """

    def __init__(self, api_base: str = METACULUS_API_BASE, api_key: str | None = None):
        import os
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key or os.environ.get("METACULUS_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "MetaculusSource: No METACULUS_API_KEY set. API calls will fail. "
                "Get a free key at https://www.metaculus.com/accounts/signup/"
            )

    async def fetch_questions(
        self,
        limit: int = 10,
        offset: int = 0,
        **kwargs: Any,
    ) -> list[ForecastQuestion]:
        r"""Fetch open binary questions from Metaculus.

        Args:
            limit: Maximum number of questions to return.
            offset: Pagination offset.
            **kwargs: Additional filters (ignored).

        Returns:
            List of ``ForecastQuestion`` objects.
        """
        url = (
            f"{self.api_base}/questions/?"
            f"limit={min(limit, 100)}&offset={offset}"
            f"&order_by=-activity&status=open&type=binary"
        )
        data = self._get_json(url)
        results = data.get("results", [])

        questions = []
        for item in results[:limit]:
            try:
                questions.append(self._to_forecast_question(item))
            except Exception as exc:
                logger.warning(f"Skipping Metaculus question {item.get('id')}: {exc}")
        return questions

    async def get_question_by_id(self, question_id: str) -> ForecastQuestion | None:
        r"""Fetch a single Metaculus question by ID."""
        try:
            url = f"{self.api_base}/questions/{question_id}/"
            data = self._get_json(url)
            return self._to_forecast_question(data)
        except Exception as exc:
            logger.warning(f"Metaculus question {question_id} not found: {exc}")
            return None

    async def fetch_resolved(
        self, limit: int = 50, *, since: "datetime | None" = None, max_pages: int = 5
    ) -> list[ResolvedQuestion]:
        r"""Fetch recently resolved binary questions from Metaculus.

        Requires an API key. Paginates with ``offset`` until ``limit`` is
        reached, pages are exhausted, or ``max_pages`` is hit. Metaculus binary
        resolutions are 1.0 (yes) or 0.0 (no); annulled/ambiguous ones are skipped.
        """
        if not self.api_key:
            raise DataSourceError("Metaculus API key required for resolutions")

        page_size = min(100, max(limit, 20))
        resolved: list[ResolvedQuestion] = []
        seen: set[str] = set()

        for page in range(max(1, max_pages)):
            url = (
                f"{self.api_base}/questions/?"
                f"limit={page_size}&offset={page * page_size}"
                f"&order_by=-resolve_time&status=resolved&type=binary"
            )
            data = self._get_json(url)
            results = data.get("results", [])
            if not results:
                break

            for item in results:
                outcome = self._metaculus_outcome(item.get("resolution"))
                if outcome is None:
                    continue
                resolved_at = self._parse_iso(item.get("resolve_time") or item.get("close_time"))
                if since is not None and resolved_at < since:
                    continue
                qid = str(item.get("id", ""))
                if qid in seen:
                    continue
                seen.add(qid)
                resolved.append(
                    ResolvedQuestion(
                        question_id=f"metaculus-{qid}",
                        venue="metaculus",
                        title=str(item.get("title", ""))[:500],
                        outcome=outcome,
                        resolved_at=resolved_at,
                        url=f"https://www.metaculus.com/questions/{qid}/",
                        metadata=MetadataBase(
                            source_version="metaculus",
                            tags=["metaculus", "binary"],
                            raw_data={"metaculus_id": qid, "resolution": item.get("resolution")},
                        ),
                    )
                )
                if len(resolved) >= limit:
                    return resolved

            if len(results) < page_size:
                break

        return resolved

    @staticmethod
    def _metaculus_outcome(resolution: Any) -> "float | None":
        r"""Map a Metaculus resolution value to 1.0 (yes) / 0.0 (no) / None."""
        if resolution is None:
            return None
        if isinstance(resolution, bool):
            return 1.0 if resolution else 0.0
        if isinstance(resolution, (int, float)):
            if float(resolution) == 1.0:
                return 1.0
            if float(resolution) == 0.0:
                return 0.0
            return None
        normalized = str(resolution).strip().lower()
        if normalized in ("yes", "true", "1"):
            return 1.0
        if normalized in ("no", "false", "0"):
            return 0.0
        return None

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

    def _get_json(self, url: str) -> dict[str, Any]:
        r"""Fetch JSON from a URL."""
        headers = {"User-Agent": "xrtm/0.1"}
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise DataSourceError(f"Metaculus API error: {exc}") from exc

    @staticmethod
    def _to_forecast_question(item: dict[str, Any]) -> ForecastQuestion:
        r"""Convert a Metaculus API question dict to ``ForecastQuestion``."""
        qid = str(item.get("id", ""))
        title = item.get("title", "") or item.get("name", "")
        description = item.get("description", "") or ""
        resolution_criteria = item.get("resolution_criteria", "") or ""

        publish_time = item.get("publish_time") or item.get("created_at")
        close_time = item.get("close_time") or item.get("resolve_time")
        snapshot_time = datetime.now(timezone.utc)

        if close_time:
            try:
                snapshot_time = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return ForecastQuestion(
            id=f"metaculus-{qid}",
            title=title[:500],
            description=description[:2000] if description else f"Metaculus binary question {qid}",
            resolution_criteria=resolution_criteria[:1000] if resolution_criteria else "",
            metadata=MetadataBase(
                snapshot_time=snapshot_time,
                source_version="metaculus",
                tags=["metaculus", "binary"],
                raw_data={
                    "metaculus_id": qid,
                    "publish_time": publish_time,
                    "community_prediction": item.get("community_prediction"),
                },
            ),
        )


__all__ = ["MetaculusSource"]
