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
Abstract interfaces for xrtm-data providers.

This module defines the protocols that all data sources must implement.
These are domain-agnostic abstractions that can be used for any forecasting
data provider, regardless of the source.

Example:
    >>> from xrtm.data.core import DataSource
    >>> class MySource(DataSource):
    ...     async def fetch_questions(self, query=None, limit=5, *, snapshot_time=None):
    ...         return []
    ...     async def get_question_by_id(self, question_id):
    ...         return None
"""

import abc
from datetime import datetime
from typing import List, Optional

from xrtm.data.core.schemas.forecast import ForecastQuestion


class DataSourceError(RuntimeError):
    r"""Base exception for data source failures."""


class SourceFetchError(DataSourceError):
    r"""Raised when a provider cannot fetch or decode source data."""


class SourceTemporalIntegrityError(DataSourceError):
    r"""Raised when a provider cannot satisfy a requested snapshot safely."""


class DataSource(abc.ABC):
    r"""
    Abstract interface for gathering or streaming forecasting workloads.

    All data providers (local, online, subgraph) must implement this interface
    to ensure consistent access patterns across the ecosystem.

    Attributes:
        None. This is a pure protocol.

    Example:
        >>> class LocalSource(DataSource):
        ...     async def fetch_questions(self, query=None, limit=5, *, snapshot_time=None):
        ...         return [ForecastQuestion(id="1", title="Test")]
    """

    @abc.abstractmethod
    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[ForecastQuestion]:
        r"""
        Fetch a list of forecast questions from the data source.

        Args:
            query: Optional search/filter string.
            limit: Maximum number of questions to return.
            snapshot_time: Optional end-of-history timestamp. Providers that cannot
                satisfy historical snapshots must surface a temporal integrity error.

        Returns:
            List of ForecastQuestion objects matching the criteria.
        """
        pass

    @abc.abstractmethod
    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[ForecastQuestion]:
        r"""
        Retrieve a single question by its unique identifier.

        Args:
            question_id: The unique identifier of the question.
            snapshot_time: Optional end-of-history timestamp. Providers that cannot
                satisfy historical snapshots must surface a temporal integrity error.

        Returns:
            The ForecastQuestion if found, None otherwise.
        """
        pass


__all__ = ["DataSource", "DataSourceError", "SourceFetchError", "SourceTemporalIntegrityError"]
