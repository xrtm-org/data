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

r"""Unit tests for PolymarketTradeSource with mocked HTTP responses."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xrtm.data.providers.subgraph import PolymarketTradeSource


class TestPolymarketTradeSource:
    r"""Tests for PolymarketTradeSource with mocked HTTP."""

    @pytest.fixture
    def source(self) -> PolymarketTradeSource:
        r"""Create a trade source instance."""
        return PolymarketTradeSource()

    @pytest.fixture
    def mock_response_data(self) -> dict:
        r"""Mock GraphQL response data."""
        return {
            "data": {
                "orderFilledEvents": [
                    {
                        "id": "trade1",
                        "makerAmountFilled": "100",
                        "takerAmountFilled": "75",
                        "timestamp": "1704067200",
                        "maker": "0xmaker1",
                        "taker": "0xtaker1",
                        "transactionHash": "0xhash1",
                    },
                    {
                        "id": "trade2",
                        "makerAmountFilled": "200",
                        "takerAmountFilled": "160",
                        "timestamp": "1704153600",
                        "maker": "0xmaker2",
                        "taker": "0xtaker2",
                        "transactionHash": "0xhash2",
                    },
                ]
            }
        }

    def test_init_default_endpoint(self, source: PolymarketTradeSource) -> None:
        r"""Verify default endpoint is set."""
        assert "goldsky" in source.endpoint.lower()
        assert source.timeout == 30.0

    def test_init_custom_endpoint(self) -> None:
        r"""Verify custom endpoint can be set."""
        custom = PolymarketTradeSource(endpoint="https://custom.api", timeout=60.0)
        assert custom.endpoint == "https://custom.api"
        assert custom.timeout == 60.0

    @pytest.mark.asyncio
    async def test_fetch_trades_success(
        self, source: PolymarketTradeSource, mock_response_data: dict
    ) -> None:
        r"""Test successful trade fetching with mocked response."""
        # Create mock response
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        # Create async context manager for response
        mock_response_ctx = AsyncMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        # Create mock session
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx

        # Create async context manager for session
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            trades = await source.fetch_trades(
                market_id="0xmarket",
                start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 3, tzinfo=timezone.utc),
            )

            assert len(trades) == 2
            assert trades[0].price == 0.75
            assert trades[0].amount == 100.0
            assert trades[0].maker == "0xmaker1"
            assert trades[1].price == 0.8
            assert trades[1].market_id == "0xmarket"

    @pytest.mark.asyncio
    async def test_fetch_trade_window(
        self, source: PolymarketTradeSource, mock_response_data: dict
    ) -> None:
        r"""Test fetch_trade_window returns TradeWindow."""
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = AsyncMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            start = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end = datetime(2024, 1, 3, tzinfo=timezone.utc)

            window = await source.fetch_trade_window(
                market_id="0xmarket",
                start_time=start,
                end_time=end,
            )

            assert window.market_id == "0xmarket"
            assert window.start_time == start
            assert window.end_time == end
            assert len(window.trades) == 2
            assert window.total_volume == 300.0

    def test_parse_trades_empty_response(self, source: PolymarketTradeSource) -> None:
        r"""Test parsing empty response."""
        trades = source._parse_trades({}, "market1")
        assert trades == []

    def test_parse_trades_malformed_entry(self, source: PolymarketTradeSource) -> None:
        r"""Test parsing skips malformed entries."""
        data = {
            "data": {
                "orderFilledEvents": [
                    {"makerAmountFilled": "0", "takerAmountFilled": "100"},  # maker <= 0, skipped
                    {
                        "makerAmountFilled": "50",
                        "takerAmountFilled": "25",
                        "timestamp": "1704067200",
                        "maker": "0x1",
                        "taker": "0x2",
                    },
                ]
            }
        }
        trades = source._parse_trades(data, "market1")
        # Should have 1 valid trade (malformed skipped)
        assert len(trades) == 1
        assert trades[0].price == 0.5

    def test_parse_trades_price_normalization(self, source: PolymarketTradeSource) -> None:
        r"""Test price > 1 is clamped to 1.0."""
        data = {
            "data": {
                "orderFilledEvents": [
                    {
                        "makerAmountFilled": "10",
                        "takerAmountFilled": "200",
                        "timestamp": "1704067200",
                        "maker": "0x1",
                        "taker": "0x2",
                    }
                ]
            }
        }
        trades = source._parse_trades(data, "market1")
        assert len(trades) == 1
        assert trades[0].price == 1.0  # Clamped from 20.0

    def test_parse_trades_uses_maker_amount(self, source: PolymarketTradeSource) -> None:
        r"""Test amount uses maker amount (token volume)."""
        data = {
            "data": {
                "orderFilledEvents": [
                    {
                        "makerAmountFilled": "50",
                        "takerAmountFilled": "100",
                        "timestamp": "1704067200",
                        "maker": "0x1",
                        "taker": "0x2",
                    }
                ]
            }
        }
        trades = source._parse_trades(data, "market1")
        assert trades[0].amount == 50.0  # Uses maker amount
