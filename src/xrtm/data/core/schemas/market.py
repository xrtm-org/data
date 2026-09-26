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

r"""Point-in-time market snapshot schema.

A shared contract for prediction-market state (price, book, liquidity) that
applications, evaluators, and backtests can all consume without re-inventing
venue-specific shapes.

Zero Leakage: every snapshot carries the ``snapshot_time`` at which the world
state was frozen; no data after that instant should influence a forecast.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = ["MarketSnapshot"]


class MarketSnapshot(BaseModel):
    r"""Point-in-time state of a prediction market.

    Attributes:
        market_id: Venue-specific market identifier.
        question_id: Optional link to the ``ForecastQuestion`` this market resolves.
        probability: Implied/mid probability of the primary outcome (0-1).
        best_bid: Best bid price (0-1).
        best_ask: Best ask price (0-1).
        spread: Bid/ask spread (0-1), derived from bid/ask when omitted.
        volume_24h: Trailing 24h volume, in the venue's currency.
        liquidity: Available liquidity, in the venue's currency.
        snapshot_time: The "Time T" at which the market state was frozen.
        source: Venue/source identifier (e.g. ``"polymarket"``).
        raw_data: Original venue payload for debugging/audit.
    """

    market_id: str = Field(..., description="Venue-specific market identifier")
    question_id: Optional[str] = Field(default=None, description="Linked ForecastQuestion id")
    probability: Optional[float] = Field(default=None, ge=0, le=1, description="Implied/mid probability")
    best_bid: Optional[float] = Field(default=None, ge=0, le=1, description="Best bid price")
    best_ask: Optional[float] = Field(default=None, ge=0, le=1, description="Best ask price")
    spread: Optional[float] = Field(default=None, ge=0, le=1, description="Bid/ask spread")
    volume_24h: Optional[float] = Field(default=None, ge=0, description="Trailing 24h volume")
    liquidity: Optional[float] = Field(default=None, ge=0, description="Available liquidity")
    snapshot_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Zero Leakage: the instant this market state was frozen",
    )
    source: Optional[str] = Field(default=None, description="Venue/source identifier")
    raw_data: Optional[Dict[str, Any]] = Field(default=None, description="Original venue payload")

    @field_validator("snapshot_time", mode="after")
    @classmethod
    def _normalize_snapshot_time(cls, value: datetime) -> datetime:
        r"""Store the snapshot boundary as a timezone-aware UTC datetime."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_book(self) -> "MarketSnapshot":
        r"""Derive the spread and reject crossed books."""
        if self.best_bid is not None and self.best_ask is not None:
            if self.best_bid > self.best_ask:
                raise ValueError("best_bid must not exceed best_ask")
            if self.spread is None:
                self.spread = round(self.best_ask - self.best_bid, 10)
        return self
