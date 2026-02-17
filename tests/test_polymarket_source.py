
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from xrtm.data.providers.online.polymarket import PolymarketSource


@pytest.fixture
def mock_response():
    resp = AsyncMock()
    resp.status = 200
    resp.json.return_value = [{"id": "1", "title": "Test"}]
    return resp

@pytest.fixture
def mock_session(mock_response):
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.return_value.__aenter__.return_value = mock_response
    session.closed = False
    return session

@pytest.mark.asyncio
async def test_legacy_usage_creates_session(mock_session):
    """Test that legacy usage (without context manager) creates and closes a session per call."""
    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
        source = PolymarketSource()
        questions = await source.fetch_questions()

        assert len(questions) == 1
        assert mock_cls.call_count == 1
        mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_context_manager_reuses_session(mock_session):
    """Test that context manager usage reuses the session."""
    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
        async with PolymarketSource() as source:
            # First call
            await source.fetch_questions()
            # Second call
            await source.fetch_questions()

        # Session should be created only once
        assert mock_cls.call_count == 1
        # And closed once at the end of context
        mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_session_helper_logic(mock_session):
    """Test _get_session helper logic."""
    source = PolymarketSource()

    # Case 1: No internal session -> creates new one
    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
        async with source._get_session() as session:
            assert session == mock_session
        mock_session.close.assert_awaited_once()
        assert mock_cls.call_count == 1

    # Reset mocks
    mock_session.reset_mock()

    # Case 2: Internal session exists and is open -> reuses it
    source._session = mock_session
    mock_session.closed = False

    with patch("aiohttp.ClientSession") as mock_cls:
        async with source._get_session() as session:
            assert session == mock_session
        # Should not close internal session
        mock_session.close.assert_not_awaited()
        # Should not create new session
        mock_cls.assert_not_called()

@pytest.mark.asyncio
async def test_aexit_clears_session(mock_session):
    """Test that __aexit__ closes and clears the session."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        source = PolymarketSource()
        await source.__aenter__()
        assert source._session is not None

        await source.__aexit__(None, None, None)
        assert source._session is None
        mock_session.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_external_session_lifecycle(mock_session):
    """Test that externally provided session is not closed by the source."""
    source = PolymarketSource(session=mock_session)

    async with source._get_session() as session:
        assert session == mock_session

    # Should not close external session
    mock_session.close.assert_not_awaited()

    await source.__aexit__(None, None, None)
    # Even on exit, should not close external session
    mock_session.close.assert_not_awaited()
