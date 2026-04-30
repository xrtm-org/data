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
Trade event schemas for market data ingestion.

This module defines schemas for representing executed trades from
prediction market subgraphs. These trade events are used to fit
Beta distributions for prior state estimation.

Example:
    >>> from xrtm.data.core.schemas import TradeEvent
    >>> trade = TradeEvent(
    ...     price=0.75,
    ...     amount=100.0,
    ...     timestamp=datetime.now(timezone.utc),
    ...     maker="0x123...",
    ...     taker="0x456...",
    ... )
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _as_utc(value: datetime) -> datetime:
    r"""Normalize datetimes to timezone-aware UTC without rejecting legacy naive inputs."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TradeEvent(BaseModel):
    r"""
    A single executed trade from a prediction market subgraph.

    Trade events capture the fundamental market activity: a price (belief),
    an amount (weight/confidence), and a timestamp (temporal position).
    Collections of trades are used to fit Beta distributions.

    Attributes:
        price: Execution price representing the implied probability [0, 1].
        amount: Trade size in USD or base currency (confidence weight).
        timestamp: When the trade occurred (UTC).
        maker: Address of the liquidity provider.
        taker: Address of the liquidity taker.
        market_id: Optional identifier for the market/question.
        tx_hash: Optional transaction hash for verification.

    Example:
        >>> trade = TradeEvent(
        ...     price=0.75,
        ...     amount=100.0,
        ...     timestamp=datetime.now(timezone.utc),
        ...     maker="0x123abc",
        ...     taker="0x456def",
        ... )
        >>> # Weight for Yes outcome: price * amount = 75.0
        >>> # Weight for No outcome: (1-price) * amount = 25.0
    """

    price: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Execution price representing implied probability [0, 1]",
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Trade size in USD or base currency",
    )
    timestamp: datetime = Field(
        ...,
        description="When the trade occurred (UTC)",
    )
    maker: str = Field(
        ...,
        description="Address of the liquidity provider",
    )
    taker: str = Field(
        ...,
        description="Address of the liquidity taker",
    )
    market_id: Optional[str] = Field(
        default=None,
        description="Identifier for the market/question",
    )
    tx_hash: Optional[str] = Field(
        default=None,
        description="Transaction hash for verification",
    )

    @field_validator("timestamp", mode="after")
    @classmethod
    def _normalize_timestamp(cls, value: datetime) -> datetime:
        r"""Normalize trade timestamps to UTC to make window comparisons stable."""
        return _as_utc(value)

    @property
    def yes_weight(self) -> float:
        r"""Volume-weighted contribution to Yes outcome: price × amount."""
        return self.price * self.amount

    @property
    def no_weight(self) -> float:
        r"""Volume-weighted contribution to No outcome: (1-price) × amount."""
        return (1.0 - self.price) * self.amount


class TradeWindow(BaseModel):
    r"""
    A collection of trades within a time window.

    Used for batch processing and Beta fitting operations.

    Attributes:
        trades: List of trade events in chronological order.
        start_time: Beginning of the time window.
        end_time: End of the time window.
        market_id: Identifier for the market these trades belong to.

    Example:
        >>> window = TradeWindow(
        ...     trades=[trade1, trade2, trade3],
        ...     start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ...     end_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ...     market_id="market_123",
        ... )
        >>> window.total_volume
        300.0
    """

    trades: list[TradeEvent] = Field(
        default_factory=list,
        description="List of trade events in chronological order",
    )
    start_time: datetime = Field(
        ...,
        description="Beginning of the time window",
    )
    end_time: datetime = Field(
        ...,
        description="End of the time window",
    )
    market_id: str = Field(
        ...,
        description="Identifier for the market these trades belong to",
    )

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _normalize_window_boundary(cls, value: datetime) -> datetime:
        r"""Normalize window boundaries to UTC before enforcing leakage invariants."""
        return _as_utc(value)

    @model_validator(mode="after")
    def _validate_temporal_bounds(self) -> "TradeWindow":
        r"""Ensure a trade window cannot contain future or pre-window events."""
        if self.end_time < self.start_time:
            raise ValueError("end_time must not precede start_time")

        leaked = [
            trade.timestamp
            for trade in self.trades
            if trade.timestamp < self.start_time or trade.timestamp > self.end_time
        ]
        if leaked:
            raise ValueError("trades must fall within [start_time, end_time]")
        return self

    @property
    def total_volume(self) -> float:
        r"""Total trading volume in the window."""
        return sum(t.amount for t in self.trades)

    @property
    def trade_count(self) -> int:
        r"""Number of trades in the window."""
        return len(self.trades)

    @property
    def volume_weighted_price(self) -> float:
        r"""Volume-weighted average price (VWAP)."""
        if not self.trades:
            return 0.5  # Uninformative default
        total_volume = self.total_volume
        if total_volume == 0:
            return 0.5
        return sum(t.price * t.amount for t in self.trades) / total_volume


__all__ = ["TradeEvent", "TradeWindow"]
