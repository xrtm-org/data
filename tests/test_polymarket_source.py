from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xrtm.data.providers.data.online.polymarket import PolymarketSource


@pytest.mark.asyncio
async def test_fetch_questions_reuses_session():
    # Mock ClientSession to return a mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = []
    mock_response.__aenter__.return_value = mock_response
    mock_response.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.get.return_value = mock_response
    mock_session.close = AsyncMock()

    # Patch aiohttp.ClientSession to return our mock_session
    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_session_cls:
        source = PolymarketSource()

        # First call creates session
        await source.fetch_questions()
        mock_session_cls.assert_called_once()

        # Second call reuses session
        await source.fetch_questions()
        mock_session_cls.assert_called_once()

        # Verify get was called twice on the same session
        assert mock_session.get.call_count == 2

        await source.close()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager_closes_session():
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.close = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        async with PolymarketSource() as source:
            await source._get_session()

        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_provided_session_is_not_closed():
    provided_session = MagicMock()
    provided_session.closed = False
    provided_session.close = AsyncMock()

    source = PolymarketSource(session=provided_session)
    session = await source._get_session()

    assert session is provided_session

    # close() should NOT call close on provided session
    await source.close()
    provided_session.close.assert_not_called()
