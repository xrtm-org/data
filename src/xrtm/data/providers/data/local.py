# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

import json
import logging
from typing import Dict, List, Optional

from xrtm.data.providers.data.base import DataSource
from xrtm.data.schemas.forecast import ForecastQuestion

logger = logging.getLogger(__name__)

__all__ = ["LocalDataSource"]


class LocalDataSource(DataSource):
    r"""
    DataSource implementation that reads from a local JSON file.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._questions: Optional[List[ForecastQuestion]] = None
        self._question_index: Optional[Dict[str, ForecastQuestion]] = None

    def _ensure_loaded(self) -> None:
        if self._questions is not None:
            return

        self._questions = []
        self._question_index = {}

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)

            for item in data:
                try:
                    question = ForecastQuestion(**item)
                    self._questions.append(question)
                    self._question_index[question.id] = question
                except Exception as e:
                    logger.warning(f"Skipping invalid item in {self.file_path}: {e}")

        except Exception as e:
            logger.error(f"Failed to load local questions from {self.file_path}: {e}")
            # Ensure empty state on failure
            self._questions = []
            self._question_index = {}

    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        self._ensure_loaded()

        questions = self._questions or []
        filtered = []
        for q in questions:
            if not query or query.lower() in q.title.lower():
                filtered.append(q)

            if len(filtered) >= limit:
                break
        return filtered

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        self._ensure_loaded()
        index = self._question_index or {}
        return index.get(question_id)
