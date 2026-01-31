# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

import asyncio
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
        self._questions: Optional[List[dict]] = None

    def _fetch_questions_sync(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        try:
            if self._questions is None:
                with open(self.file_path, "r") as f:
                    self._questions = json.load(f)

            questions = []
            for item in self._questions:
                if not query or query.lower() in item.get("title", "").lower():
                    questions.append(ForecastQuestion(**item))

                if len(questions) >= limit:
                    break
            return questions
        except Exception as e:
            logger.error(f"Failed to read local questions from {self.file_path}: {e}")
            return []

    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        return await asyncio.to_thread(self._fetch_questions_sync, query, limit)

    def _get_question_by_id_sync(self, question_id: str) -> Optional[ForecastQuestion]:
        try:
            if self._questions is None:
                with open(self.file_path, "r") as f:
                    self._questions = json.load(f)

            for item in self._questions:
                if item.get("id") == question_id:
                    return ForecastQuestion(**item)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve question {question_id} from {self.file_path}: {e}")
            return None

    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        return await asyncio.to_thread(self._get_question_by_id_sync, question_id)
