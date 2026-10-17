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

r"""Shared JSON fetching with retry/backoff for online providers.

A single transient network blip used to fail an entire collection pass; these
providers now retry idempotent GETs a bounded number of times.
"""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from xrtm.data.core import DataSourceError

logger = logging.getLogger(__name__)

__all__ = ["fetch_json"]

DEFAULT_USER_AGENT = "xrtm/0.1"
RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def fetch_json(
    url: str,
    *,
    timeout: float = 15.0,
    retries: int = 2,
    headers: Optional[Dict[str, str]] = None,
    provider: str = "API",
) -> Any:
    r"""GET *url* and parse JSON, retrying transient failures with backoff.

    Client errors (4xx other than 408/409/425/429) are not retried — they will
    fail again and retrying them just burns time.
    """
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, **(headers or {})})
    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_STATUS or attempt >= retries:
                raise DataSourceError(f"{provider} API error: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            # The body was read in full but does not parse: deterministic, so
            # retrying only multiplies the damage (e.g. an HTML maintenance
            # page served with HTTP 200).
            raise DataSourceError(f"{provider} API returned unparseable JSON: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - connection/timeout errors are transient
            last_error = exc
            if attempt >= retries:
                raise DataSourceError(f"{provider} API error: {exc}") from exc

        wait = (0.5 * (2**attempt)) + random.uniform(0.0, 0.25)
        logger.warning(
            "%s request failed (attempt %d/%d), retrying in %.1fs: %s",
            provider,
            attempt + 1,
            retries,
            wait,
            last_error,
        )
        time.sleep(wait)

    raise DataSourceError(f"{provider} API error: {last_error}")  # pragma: no cover - loop raises
