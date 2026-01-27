# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

import abc
from typing import List, Optional

from xrtm.data.schemas.forecast import ForecastQuestion


class DataSource(abc.ABC):
    r"""
    Abstract interface for gathering or streaming forecasting workloads.
    """

    @abc.abstractmethod
    async def fetch_questions(self, query: Optional[str] = None, limit: int = 5) -> List[ForecastQuestion]:
        pass

    @abc.abstractmethod
    async def get_question_by_id(self, question_id: str) -> Optional[ForecastQuestion]:
        pass


__all__ = ["DataSource"]
