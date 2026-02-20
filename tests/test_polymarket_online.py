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

r"""Tests for PolymarketSource Gamma API provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from xrtm.data.providers.online.polymarket import PolymarketSource


class TestPolymarketSource:
    r"""Tests for PolymarketSource."""

    @pytest.mark.asyncio
    async def test_context_manager_reuse(self):
        r"""Test that the session is reused when used as a context manager."""
        async with PolymarketSource() as source:
            # First call should create session if not present (handled by __aenter__)
            assert source._session is not None
            session_id = id(source._session)

            # Create a mock context manager for the response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"id": "1", "title": "Test"})

            mock_get_ctx = MagicMock()
            mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_ctx.__aexit__ = AsyncMock(return_value=None)

            # Patch the session.get method on the *existing* session object
            with patch.object(source._session, 'get', return_value=mock_get_ctx) as mock_get:
                await source.get_question_by_id("1")
                await source.get_question_by_id("2")

                # Verify session object is the same
                assert id(source._session) == session_id
                # Verify get was called twice on the same session
                assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        r"""Test that the session is closed on exit."""
        source = PolymarketSource()
        async with source:
            assert source._session is not None
            assert not source._session.closed
            session = source._session

        # After exit, session should be closed and _session set to None
        assert source._session is None
        assert session.closed

    @pytest.mark.asyncio
    async def test_passed_session_cleanup(self):
        r"""Test that a passed session is NOT closed on exit."""
        session = aiohttp.ClientSession()
        try:
            source = PolymarketSource(session=session)
            async with source:
                assert source._session is session
                assert not session.closed

            # After exit, session should still be open and _session kept (because not owned)
            assert source._session is session
            assert not session.closed
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_one_off_usage(self):
        r"""Test usage without context manager (legacy mode)."""
        source = PolymarketSource()

        # Mock response context manager
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"id": "1", "title": "Test"})

        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=None)

        # Mock session
        mock_session = MagicMock()
        mock_session.get.return_value = mock_get_ctx

        # Mock session context manager (returned by ClientSession())
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("xrtm.data.providers.online.polymarket.aiohttp.ClientSession", return_value=mock_session_ctx) as mock_cls:
            await source.get_question_by_id("1")

            # Should have created a session
            mock_cls.assert_called()
            # And used it
            mock_session.get.assert_called()
