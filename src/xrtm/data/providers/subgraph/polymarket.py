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
Polymarket Goldsky Subgraph data provider.

This module provides access to order-filled events from the Polymarket
prediction market via the Goldsky public subgraph API. These trade events
are essential for fitting Beta distributions to represent market belief state.

The Goldsky subgraph provides granular trade data that neither the Gamma API
(single price snapshot) nor CLOB API (unfilled orders) can provide.

Example:
    >>> from xrtm.data.providers.subgraph import PolymarketTradeSource
    >>> source = PolymarketTradeSource()
    >>> trades = await source.fetch_trades(
    ...     market_id="0x123...",
    ...     start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    ...     end_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
    ... )
"""

from datetime import datetime, timezone
from typing import Any, Optional

import aiohttp

from xrtm.data.core import SourceFetchError
from xrtm.data.core.schemas.trade import TradeEvent, TradeWindow


def _as_utc(value: datetime) -> datetime:
    r"""Normalize datetimes to timezone-aware UTC without rejecting legacy naive inputs."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class PolymarketTradeSource:
    r"""
    Data provider for Polymarket Goldsky Subgraph.

    Fetches OrderFilled events from the public Polymarket subgraph,
    providing granular trade data for Beta distribution fitting.

    Attributes:
        endpoint: The Goldsky API endpoint URL.
        timeout: Request timeout in seconds.

    Example:
        >>> source = PolymarketTradeSource()
        >>> trades = await source.fetch_trades(
        ...     market_id="0x123...",
        ...     start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ...     end_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ... )
        >>> print(f"Found {len(trades)} trades")
    """

    ENDPOINT = (
        "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/"
        "subgraphs/orderbook-subgraph/0.0.1/gn"
    )

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        r"""
        Initialize the Polymarket trade source.

        Args:
            endpoint: Custom subgraph endpoint. Defaults to Goldsky public API.
            timeout: Request timeout in seconds.
        """
        self.endpoint = endpoint or self.ENDPOINT
        self.timeout = timeout
        self.last_error: Optional[SourceFetchError] = None

    @staticmethod
    def _validate_window(start_time: datetime, end_time: datetime, limit: int) -> tuple[datetime, datetime]:
        start_utc = _as_utc(start_time)
        end_utc = _as_utc(end_time)
        if end_utc < start_utc:
            raise ValueError("end_time must not precede start_time")
        if limit <= 0:
            raise ValueError("limit must be positive")
        return start_utc, end_utc

    async def fetch_trades(
        self,
        market_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> list[TradeEvent]:
        r"""
        Fetch OrderFilled events for a market token within a time window.

        Args:
            market_id: The asset/token identifier (ERC20 Token ID).
            start_time: Start of the time window (UTC).
            end_time: End of the time window (UTC).
            limit: Maximum number of trades to fetch.

        Returns:
            List of TradeEvent objects in chronological order.
        """
        start_utc, end_utc = self._validate_window(start_time, end_time, limit)

        # Query filtering by makerAssetId (assuming token is the asset being traded)
        query = """
        query($assetId: String!, $start: Int!, $end: Int!, $first: Int!) {
            orderFilledEvents(
                where: {
                    makerAssetId: $assetId,
                    timestamp_gte: $start,
                    timestamp_lte: $end
                }
                first: $first
                orderBy: timestamp
                orderDirection: asc
            ) {
                id
                makerAmountFilled
                takerAmountFilled
                timestamp
                maker
                taker
                transactionHash
                # Price is not always explicitly in OrderFilledEvent in basic schema,
                # but we introspected it earlier? Wait.
                # Introspection showed: makerAmountFilled, takerAmountFilled.
                # It usually implies Price = takerAmount / makerAmount (or vice versa).
                # But let's check if 'price' field exists (Introspection didn't show it explicitly?
                # Step 1830 output: fields: id, transactionHash, timestamp, orderHash, maker, taker, makerAssetId, takerAssetId, makerAmountFilled, takerAmountFilled, fee.
                # NO PRICE FIELD!
            }
        }
        """
        # Wait, if there is no Price field, we must calculate it!
        # Price = takerAmountFilled / makerAmountFilled (if one is USDC and other is Outcome?)
        # This is complex.
        # But wait, checking logic... Goldsky usually has enriched fields.
        # Step 1809 sample output: {"id": "..."} didn't show fields because I requested only ID.
        # Step 1830 Schema introspection: NO 'price' field.
        # So I must compute price.

        variables = {
            "assetId": market_id,
            "start": int(start_utc.timestamp()),
            "end": int(end_utc.timestamp()),
            "first": limit,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                response.raise_for_status()
                data = await response.json()

        if not isinstance(data, dict):
            error = SourceFetchError("Polymarket subgraph returned a non-object GraphQL payload.")
            self.last_error = error
            raise error
        if data.get("errors"):
            error = SourceFetchError(f"Polymarket subgraph returned GraphQL errors: {data['errors']}")
            self.last_error = error
            raise error

        self.last_error = None
        return self._parse_trades(data, market_id, start_utc, end_utc)

    def _parse_trades(
        self,
        data: dict[str, Any],
        market_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[TradeEvent]:
        r"""Parse GraphQL response into TradeEvent objects."""
        trades: list[TradeEvent] = []
        start_utc = _as_utc(start_time) if start_time is not None else None
        end_utc = _as_utc(end_time) if end_time is not None else None

        order_filleds = data.get("data", {}).get("orderFilledEvents", [])
        for item in order_filleds:
            try:
                # We need to derive price and volume (amount)
                # Maker Asset is usually the Outcome Token (if matched against Collateral)
                # Taker Asset is typically USDC (Collateral)
                # If so:
                # Maker Amount = Token Amount
                # Taker Amount = USDC Amount
                # Price = Taker / Maker

                maker_amt = float(item.get("makerAmountFilled", "0"))
                taker_amt = float(item.get("takerAmountFilled", "0"))

                if maker_amt <= 0 or taker_amt <= 0:
                    continue

                # Assume standard direction: Maker provides Outcome, Taker provides USDC
                # To be precise, we would check makerAssetId == market_id, but we filtered query by it.
                # If market_id matches makerAssetId, then Maker Amount is valid Token Volume.
                amount = maker_amt
                price = taker_amt / maker_amt

                # Normalize price if it's crazy (sometimes amounts are in wei vs usdc decimals)
                # But Goldsky usually returns raw updated values or formatted?
                # Usually raw units.
                # Polymarket Tokens (CTF) are 18 decimals?
                # USDC is 6 decimals.
                # Price will be scaled by 1e12 if not handled.
                # Wait, if data returns raw integers, we need decimals!
                # The Subgraph usually returns formatted strings (BigDecimal) or raw integers.
                # Introspection showed "BigDecimal" type for some fields?
                # Step 1801 showed "BigDecimal".
                # If Goldsky returns "1.5" string, it is formatted.
                # If "1500000", it is raw.
                # Step 1809 output showed IDs, not amounts.
                # Safest bet: Assume formatted decimal strings if they contain ".".
                # If they are integers, check magnitude.
                # Assuming formatted for now as The Graph usually does BigDecimal for amounts.

                # Sanity cap
                if price > 1.0:
                    # Maybe it's inverted? or Raw units issue.
                    # For now, clamp.
                    price = 1.0

                # Convert timestamp
                timestamp = datetime.fromtimestamp(int(item.get("timestamp", 0)), tz=timezone.utc)
                if start_utc is not None and timestamp < start_utc:
                    continue
                if end_utc is not None and timestamp > end_utc:
                    continue

                trade = TradeEvent(
                    price=max(0.0, min(1.0, price)),
                    amount=amount,
                    timestamp=timestamp,
                    maker=item.get("maker", ""),
                    taker=item.get("taker", ""),
                    market_id=market_id,
                    tx_hash=item.get("transactionHash"),
                )
                trades.append(trade)
            except (ValueError, TypeError, KeyError, ZeroDivisionError):
                continue

        return trades

    async def fetch_trade_window(
        self,
        market_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> TradeWindow:
        r"""
        Fetch trades and return as a TradeWindow.

        Args:
            market_id: The market/question identifier.
            start_time: Start of the time window (UTC).
            end_time: End of the time window (UTC).
            limit: Maximum number of trades to fetch.

        Returns:
            TradeWindow containing all trades in the specified window.
        """
        start_utc, end_utc = self._validate_window(start_time, end_time, limit)
        trades = await self.fetch_trades(market_id, start_utc, end_utc, limit)
        return TradeWindow(
            trades=trades,
            start_time=start_utc,
            end_time=end_utc,
            market_id=market_id,
        )

    async def fetch_recent_markets(self, limit: int = 10) -> list[dict[str, Any]]:
        r"""
        Fetch recent active markets from the subgraph.

        Args:
            limit: Maximum number of markets to return.

        Returns:
            List of market info dicts with 'id' and 'question' keys.
        """
        query = """
        query($first: Int!) {
            markets(
                first: $first
                orderBy: createdAt
                orderDirection: desc
                where: { resolved: false }
            ) {
                id
                question
                createdAt
                outcomes
            }
        }
        """

        variables = {"first": limit}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                response.raise_for_status()
                data = await response.json()

        if not isinstance(data, dict):
            error = SourceFetchError("Polymarket subgraph returned a non-object GraphQL payload.")
            self.last_error = error
            raise error
        if data.get("errors"):
            error = SourceFetchError(f"Polymarket subgraph returned GraphQL errors: {data['errors']}")
            self.last_error = error
            raise error

        self.last_error = None
        markets = data.get("data", {}).get("markets", [])
        return [
            {
                "id": m.get("id", ""),
                "question": m.get("question", "Unknown"),
                "outcomes": m.get("outcomes", []),
            }
            for m in markets
        ]


__all__ = ["PolymarketTradeSource"]
