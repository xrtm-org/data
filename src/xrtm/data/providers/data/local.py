# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

import json
import logging
from typing import List, Optional, Dict

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
        self._questions: List[ForecastQuestion] = []
        self._question_index: Dict[str, ForecastQuestion] = {}
        self._load_data()

    def _load_data(self):
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
        filtered = []
        for q in self._questions:
            if not query or query.lower() in q.title.lower():
                filtered.append(q)

            if len(filtered) >= limit:
                break
        return filtered

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        return self._question_index.get(question_id)
