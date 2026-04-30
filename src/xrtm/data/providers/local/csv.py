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
import threading
from typing import Any, List, Optional

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
        self._questions_by_id: dict[str, ForecastQuestion] = {}
        self._load_lock = threading.Lock()

    def _ensure_data_loaded(self) -> None:
        r"""Load and validate the JSON cache exactly once."""
        if self._questions is not None:
            return

        with self._load_lock:
            if self._questions is not None:
                return

            try:
                with open(self.file_path, "r") as f:
                    raw_data = json.load(f)
            except Exception as e:
                logger.error("Failed to read local questions from %s: %s", self.file_path, e)
                self._questions = []
                self._questions_by_id = {}
                return

            if not isinstance(raw_data, list):
                logger.error("Invalid local questions file %s: JSON root must be a list.", self.file_path)
                self._questions = []
                self._questions_by_id = {}
                return

            questions: list[ForecastQuestion] = []
            questions_by_id: dict[str, ForecastQuestion] = {}
            for idx, item in enumerate(raw_data):
                if not isinstance(item, dict):
                    logger.warning("Skipping local question %s from %s: item must be an object.", idx, self.file_path)
                    continue
                try:
                    question = ForecastQuestion(**item)
                except Exception as e:
                    logger.warning("Skipping invalid local question %s from %s: %s", idx, self.file_path, e)
                    continue

                if question.id not in questions_by_id:
                    questions.append(question)
                    questions_by_id[question.id] = question
                else:
                    logger.warning("Duplicate local question id %s in %s; keeping first occurrence.", question.id, self.file_path)

            self._questions = questions
            self._questions_by_id = questions_by_id

    def _fetch_questions_sync(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        r"""Synchronous implementation of question fetching."""
        self._ensure_data_loaded()
        if self._questions is None:
            return []

        questions = []
        query_lower = query.lower() if query else None
        for question in self._questions:
            if not query_lower or query_lower in question.title.lower():
                questions.append(question.model_copy(deep=True))

            if len(questions) >= limit:
                break
        return questions

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
        self._ensure_data_loaded()
        question = self._questions_by_id.get(question_id)
        if question is not None:
            return question.model_copy(deep=True)
        return None

    def _raw_questions_for_tests(self) -> list[dict[str, Any]]:
        r"""Return cached question data for tests and diagnostics."""
        self._ensure_data_loaded()
        if self._questions is None:
            return []
        return [question.model_dump(mode="json") for question in self._questions]

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        r"""
        Retrieve a single question by ID from the local file.

        Args:
            question_id: The unique identifier of the question.

        Returns:
            The ForecastQuestion if found, None otherwise.
        """
        return await asyncio.to_thread(self._get_question_by_id_sync, question_id)
