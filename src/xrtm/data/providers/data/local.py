# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

import json
import logging
from typing import List, Optional

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
        self._data = None

    def _load_data(self) -> List[dict]:
        if self._data is None:
            with open(self.file_path, "r") as f:
                self._data = json.load(f)
        return self._data

    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        try:
            data = self._load_data()

            questions = []
            for item in data:
                if not query or query.lower() in item.get("title", "").lower():
                    questions.append(ForecastQuestion(**item))

                if len(questions) >= limit:
                    break
            return questions
        except Exception as e:
            logger.error(f"Failed to read local questions from {self.file_path}: {e}")
            return []

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        try:
            data = self._load_data()

            for item in data:
                if item.get("id") == question_id:
                    return ForecastQuestion(**item)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve question {question_id} from {self.file_path}: {e}")
            return None
