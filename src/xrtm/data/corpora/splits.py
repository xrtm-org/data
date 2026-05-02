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

r"""Corpus splitting utilities for train/eval/held-out partitions.

This module provides deterministic splitting strategies for benchmark corpora,
ensuring reproducible train/eval partitions across runs and environments.

Design principles:
- Deterministic: Same split configuration always yields same partitions
- Reproducible: Splits are keyed by corpus version and split config
- Temporal integrity: Respect snapshot_time for temporal holdouts
- Flexible: Support percentage-based, count-based, and time-based splits

Example:
    >>> from xrtm.data.corpora.splits import CorpusSplitter, SplitConfig
    >>> config = SplitConfig(train_ratio=0.7, eval_ratio=0.2, held_out_ratio=0.1)
    >>> splitter = CorpusSplitter(config, seed=42)
    >>> splits = splitter.split_corpus(questions)
    >>> print(len(splits["train"]), len(splits["eval"]), len(splits["held-out"]))
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from xrtm.data.core.schemas import ForecastQuestion


@dataclass
class SplitConfig:
    """Configuration for corpus splitting."""

    train_ratio: float = 0.7
    eval_ratio: float = 0.2
    held_out_ratio: float = 0.1
    seed: int = 42
    temporal_split: bool = False
    temporal_cutoff: Optional[datetime] = None

    def __post_init__(self):
        total = self.train_ratio + self.eval_ratio + self.held_out_ratio
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"split ratios must sum to 1.0, got {total}")

    def to_dict(self) -> dict[str, Any]:
        """Convert config to a JSON-serializable dict."""
        return {
            "train_ratio": self.train_ratio,
            "eval_ratio": self.eval_ratio,
            "held_out_ratio": self.held_out_ratio,
            "seed": self.seed,
            "temporal_split": self.temporal_split,
            "temporal_cutoff": self.temporal_cutoff.isoformat() if self.temporal_cutoff else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SplitConfig:
        """Load config from a dict."""
        cutoff = data.get("temporal_cutoff")
        return cls(
            train_ratio=data["train_ratio"],
            eval_ratio=data["eval_ratio"],
            held_out_ratio=data["held_out_ratio"],
            seed=data["seed"],
            temporal_split=data.get("temporal_split", False),
            temporal_cutoff=datetime.fromisoformat(cutoff) if cutoff else None,
        )


class CorpusSplitter:
    """Deterministic corpus splitter for train/eval/held-out partitions."""

    def __init__(self, config: SplitConfig):
        self.config = config

    def split_corpus(
        self,
        questions: List[ForecastQuestion],
    ) -> Dict[str, List[ForecastQuestion]]:
        """Split a list of questions into train/eval/held-out partitions.

        Args:
            questions: List of ForecastQuestion objects to split

        Returns:
            Dictionary mapping split names to question lists
        """
        if self.config.temporal_split:
            if self.config.temporal_cutoff is None:
                raise ValueError("temporal_cutoff required for temporal splits")
            return self._temporal_split(questions)
        return self._random_split(questions)

    def _random_split(
        self,
        questions: List[ForecastQuestion],
    ) -> Dict[str, List[ForecastQuestion]]:
        """Perform deterministic random splitting."""
        questions = list(questions)

        # Sort by ID for deterministic ordering
        questions.sort(key=lambda q: q.id)

        # Deterministic shuffle based on config seed
        rng = random.Random(self.config.seed)
        rng.shuffle(questions)

        total = len(questions)
        train_end = int(total * self.config.train_ratio)
        eval_end = train_end + int(total * self.config.eval_ratio)

        return {
            "train": questions[:train_end],
            "eval": questions[train_end:eval_end],
            "held-out": questions[eval_end:],
        }

    def _temporal_split(
        self,
        questions: List[ForecastQuestion],
    ) -> Dict[str, List[ForecastQuestion]]:
        """Perform temporal splitting based on snapshot_time."""
        cutoff = self.config.temporal_cutoff
        if cutoff is None:
            raise ValueError("temporal_cutoff required for temporal splits")

        # Make cutoff timezone-aware if it's not already
        if cutoff.tzinfo is None:
            from datetime import timezone
            cutoff = cutoff.replace(tzinfo=timezone.utc)

        before_cutoff = []
        after_cutoff = []

        for question in questions:
            snapshot_time = question.metadata.snapshot_time
            if snapshot_time:
                # Make snapshot_time timezone-aware if needed
                if snapshot_time.tzinfo is None:
                    from datetime import timezone
                    snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)

                if snapshot_time < cutoff:
                    before_cutoff.append(question)
                else:
                    after_cutoff.append(question)
            else:
                after_cutoff.append(question)

        # Split the pre-cutoff data into train/eval
        rng = random.Random(self.config.seed)
        before_cutoff.sort(key=lambda q: q.id)
        rng.shuffle(before_cutoff)

        total_before = len(before_cutoff)
        train_ratio_adjusted = self.config.train_ratio / (self.config.train_ratio + self.config.eval_ratio)
        train_end = int(total_before * train_ratio_adjusted)

        return {
            "train": before_cutoff[:train_end],
            "eval": before_cutoff[train_end:],
            "held-out": after_cutoff,
        }

    def get_split_signature(self, questions: List[ForecastQuestion]) -> str:
        """Generate a deterministic signature for a split configuration.

        This can be used to cache split indices or verify split reproducibility.
        """
        question_ids = sorted(q.id for q in questions)
        config_str = str(self.config.to_dict())
        combined = f"{config_str}::{','.join(question_ids)}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


class SplitAwareCorpusSource:
    """Wrapper that provides split-aware access to a corpus DataSource.

    This class wraps an existing DataSource and provides filtered access
    based on pre-computed splits.
    """

    def __init__(
        self,
        source: Any,
        splits: Dict[str, List[ForecastQuestion]],
        default_split: str = "train",
    ):
        self._source = source
        self._splits = splits
        self._default_split = default_split
        self._question_id_to_split = {}
        for split_name, questions in splits.items():
            for question in questions:
                self._question_id_to_split[question.id] = split_name

    def get_split(self, split_name: str) -> List[ForecastQuestion]:
        """Get all questions for a specific split."""
        if split_name not in self._splits:
            raise ValueError(f"unknown split: {split_name}")
        return list(self._splits[split_name])

    def get_question_split(self, question_id: str) -> Optional[str]:
        """Determine which split a question belongs to."""
        return self._question_id_to_split.get(question_id)

    async def fetch_questions(
        self,
        query: Optional[str] = None,
        limit: int = 5,
        *,
        snapshot_time: Optional[datetime] = None,
        split: Optional[str] = None,
    ) -> List[ForecastQuestion]:
        """Fetch questions from the underlying source, filtered by split."""
        split = split or self._default_split
        available = self.get_split(split)

        if query:
            available = [q for q in available if query.lower() in q.title.lower() or query.lower() in q.description.lower()]

        if snapshot_time:
            available = [q for q in available if q.metadata.snapshot_time and q.metadata.snapshot_time <= snapshot_time]

        return available[:limit]

    async def get_question_by_id(
        self,
        question_id: str,
        *,
        snapshot_time: Optional[datetime] = None,
        split: Optional[str] = None,
    ) -> Optional[Any]:
        """Get a question by ID, verifying it belongs to the requested split."""
        if split and self.get_question_split(question_id) != split:
            return None
        return await self._source.get_question_by_id(question_id, snapshot_time=snapshot_time)


__all__ = [
    "SplitConfig",
    "CorpusSplitter",
    "SplitAwareCorpusSource",
]
