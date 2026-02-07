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
Local file-based data source.

This module provides a DataSource implementation that reads forecast
questions from local JSON files.

Example:
    >>> from xrtm.data.providers.local import LocalDataSource
    >>> source = LocalDataSource("./questions.json")
    >>> questions = await source.fetch_questions(limit=10)
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion

logger = logging.getLogger(__name__)

__all__ = ["LocalDataSource"]


class LocalDataSource(DataSource):
    r"""
    DataSource implementation that reads from a local JSON file.

    This provider is useful for testing, development, and offline scenarios
    where data has been pre-fetched and stored locally.

    Args:
        file_path: Path to the JSON file containing forecast questions.

    Attributes:
        file_path: The path to the local JSON file.

    Example:
        >>> source = LocalDataSource("./test_questions.json")
        >>> questions = await source.fetch_questions(query="weather", limit=5)
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._questions: Optional[List[ForecastQuestion]] = None
        self._questions_by_id: Optional[Dict[str, ForecastQuestion]] = None

    def _ensure_data_loaded(self) -> None:
        r"""Ensure that the local data file is loaded and parsed."""
        if self._questions is not None:
            return

        with open(self.file_path, "r") as f:
            raw_data = json.load(f)

        questions = []
        questions_by_id = {}

        for item in raw_data:
            try:
                q = ForecastQuestion(**item)
                questions.append(q)
                questions_by_id[q.id] = q
            except Exception as e:
                logger.warning(f"Skipping invalid question in {self.file_path}: {e}")
                continue

        self._questions = questions
        self._questions_by_id = questions_by_id

    def _fetch_questions_sync(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        r"""Synchronous implementation of question fetching."""
        try:
            self._ensure_data_loaded()

            if self._questions is None:
                return []

            questions = []
            for q in self._questions:
                if not query or query.lower() in q.title.lower():
                    questions.append(q)

                if len(questions) >= limit:
                    break
            return questions
        except Exception as e:
            logger.error(f"Failed to read local questions from {self.file_path}: {e}")
            return []

    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        r"""
        Fetch questions from the local JSON file.

        Args:
            query: Optional search string to filter questions by title.
            limit: Maximum number of questions to return.

        Returns:
            List of ForecastQuestion objects matching the criteria.
        """
        return await asyncio.to_thread(self._fetch_questions_sync, query, limit)

    def _get_question_by_id_sync(self, question_id: str) -> Optional[ForecastQuestion]:
        r"""Synchronous implementation of single question retrieval."""
        try:
            self._ensure_data_loaded()

            if self._questions_by_id is None:
                return None

            return self._questions_by_id.get(question_id)
        except Exception as e:
            logger.error(f"Failed to retrieve question {question_id} from {self.file_path}: {e}")
            return None

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        r"""
        Retrieve a single question by ID from the local file.

        Args:
            question_id: The unique identifier of the question.

        Returns:
            The ForecastQuestion if found, None otherwise.
        """
        return await asyncio.to_thread(self._get_question_by_id_sync, question_id)
