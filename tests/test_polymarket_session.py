import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock
from xrtm.data.providers.data.online.polymarket import PolymarketSource

@pytest.mark.asyncio
async def test_polymarket_session_injection():
    # Use real session to verify behavior
    async with aiohttp.ClientSession() as session:
        source = PolymarketSource(session=session)

        assert source._session is session
        assert source._owns_session is False

        # Ensure it uses the same session
        got_session = await source._get_session()
        assert got_session is session

        await source.close()
        # Should not close the injected session
        assert not session.closed

@pytest.mark.asyncio
async def test_polymarket_session_creation():
    source = PolymarketSource()
    assert source._session is None
    assert source._owns_session is True

    # First call creates session
    session1 = await source._get_session()
    assert isinstance(session1, aiohttp.ClientSession)

    # Second call returns same session
    session2 = await source._get_session()
    assert session1 is session2

    await source.close()
    # Should close the owned session
    assert session1.closed
    assert source._session is None

@pytest.mark.asyncio
async def test_polymarket_context_manager():
    async with PolymarketSource() as source:
        assert source._session is None
        # Use session
        session = await source._get_session()
        assert not session.closed

    # Should be closed after context exit
    assert session.closed

@pytest.mark.asyncio
async def test_polymarket_fetch_uses_session_mock():
    # Mocking the session behavior for fetch_questions
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = []

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_response
    mock_context.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.get.return_value = mock_context

    source = PolymarketSource(session=mock_session)

    await source.fetch_questions()

    mock_session.get.assert_called()

    # Clean up
    await source.close()
