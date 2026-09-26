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

r"""Resolved-question schema for ground-truth tracking.

A ``ResolvedQuestion`` is the post-forecast ground truth for a question: the
outcome and the moment it was decided. Keeping resolutions in a first-class
schema lets evaluation and calibration pipelines consume them uniformly
across venues (Polymarket, Manifold, Kalshi, Metaculus, ...).
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from xrtm.data.core.schemas.forecast import MetadataBase

__all__ = ["ResolvedQuestion"]


class ResolvedQuestion(BaseModel):
    r"""A question that has resolved, with its outcome.

    Attributes:
        question_id: Canonical question identifier (e.g. ``"polymarket-123"``).
        venue: Venue/source identifier (e.g. ``"polymarket"``).
        title: Question text as published by the venue.
        outcome: Resolved outcome on [0, 1]: 1.0 = yes, 0.0 = no.
        resolved_at: UTC timestamp when the question resolved.
        url: Optional canonical URL for the question.
        metadata: Source metadata (raw payload, tags, version).
    """

    question_id: str = Field(..., description="Canonical question identifier")
    venue: str = Field(..., description="Venue/source identifier")
    title: str = Field(default="", description="Question text as published by the venue")
    outcome: float = Field(..., ge=0, le=1, description="Resolved outcome: 1.0 = yes, 0.0 = no")
    resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the question resolved",
    )
    url: Optional[str] = Field(default=None, description="Canonical URL for the question")
    metadata: MetadataBase = Field(default_factory=MetadataBase)  # type: ignore[arg-type]

    @field_validator("resolved_at", mode="after")
    @classmethod
    def _normalize_resolved_at(cls, value: datetime) -> datetime:
        r"""Store resolution timestamps as timezone-aware UTC datetimes."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
