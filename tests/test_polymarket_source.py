from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from xrtm.data.providers.online import PolymarketSource


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(
        return_value=[
            {
                "id": "event1",
                "title": "Will it rain tomorrow?",
                "description": "Weather forecast question",
                "tags": ["weather"],
            }
        ]
    )
    return response


@pytest.fixture
def mock_single_response():
    """Create a mock aiohttp response for a single event."""
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(
        return_value={
            "id": "event1",
            "title": "Will it rain tomorrow?",
            "description": "Weather forecast question",
            "tags": ["weather"],
        }
    )
    return response


@pytest.mark.asyncio
async def test_context_manager_creates_and_closes_session():
    """Test that async context manager creates and closes session when not provided."""
    source = PolymarketSource()

    # Session should be None initially
    assert source._session is None
    assert source._owns_session is True

    async with source:
        # Session should be created
        assert source._session is not None
        assert isinstance(source._session, aiohttp.ClientSession)
        assert not source._session.closed

    # Session should be closed and reset to None after exit
    assert source._session is None


@pytest.mark.asyncio
async def test_context_manager_does_not_close_injected_session():
    """Test that async context manager does not close an externally provided session."""
    external_session = aiohttp.ClientSession()
    source = PolymarketSource(session=external_session)

    assert source._session is external_session
    assert source._owns_session is False

    async with source:
        assert source._session is external_session
        assert not source._session.closed

    # Session should still be open after exit
    assert source._session is external_session
    assert not source._session.closed

    # Clean up
    await external_session.close()


@pytest.mark.asyncio
async def test_context_manager_reuse():
    """Test that context manager can be used multiple times."""
    source = PolymarketSource()

    # First use
    async with source:
        first_session = source._session
        assert first_session is not None

    # Session should be reset
    assert source._session is None

    # Second use should create a new session
    async with source:
        second_session = source._session
        assert second_session is not None
        # Should be a different session instance
        assert second_session is not first_session

    # Should be reset again
    assert source._session is None


@pytest.mark.asyncio
async def test_has_active_session_detects_closed_session():
    """Test that _has_active_session correctly detects a closed session."""
    source = PolymarketSource()

    # No session initially
    assert not source._has_active_session()

    # Create a session
    source._session = aiohttp.ClientSession()
    assert source._has_active_session()

    # Close the session
    await source._session.close()
    assert not source._has_active_session()


@pytest.mark.asyncio
async def test_fetch_questions_with_reused_session(mock_response):
    """Test fetch_questions reuses an active session."""
    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        MockSession.return_value = mock_session

        async with PolymarketSource() as source:
            questions = await source.fetch_questions(limit=5)

            # Should return normalized questions
            assert len(questions) == 1
            assert questions[0].id == "event1"
            assert questions[0].title == "Will it rain tomorrow?"

            # Session should be reused (get called on existing session)
            assert mock_session.get.called


@pytest.mark.asyncio
async def test_fetch_questions_without_session(mock_response):
    """Test fetch_questions creates a one-off session when no reusable session exists."""
    source = PolymarketSource()

    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
        MockSession.return_value = mock_session

        questions = await source.fetch_questions(limit=5)

        # Should return normalized questions
        assert len(questions) == 1
        assert questions[0].id == "event1"

        # A new session should have been created
        MockSession.assert_called_once()


@pytest.mark.asyncio
async def test_get_question_by_id_with_reused_session(mock_single_response):
    """Test get_question_by_id reuses an active session."""
    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_single_response)))
        MockSession.return_value = mock_session

        async with PolymarketSource() as source:
            question = await source.get_question_by_id("event1")

            # Should return normalized question
            assert question is not None
            assert question.id == "event1"
            assert question.title == "Will it rain tomorrow?"

            # Session should be reused
            assert mock_session.get.called


@pytest.mark.asyncio
async def test_get_question_by_id_without_session(mock_single_response):
    """Test get_question_by_id creates a one-off session when no reusable session exists."""
    source = PolymarketSource()

    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_single_response)))
        MockSession.return_value = mock_session

        question = await source.get_question_by_id("event1")

        # Should return normalized question
        assert question is not None
        assert question.id == "event1"

        # A new session should have been created
        MockSession.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling_in_fetch_questions():
    """Test that fetch_questions handles errors gracefully."""
    source = PolymarketSource()

    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # Make the request fail - exception will be caught by fetch_questions
        mock_resp = MagicMock()
        mock_resp.__aenter__ = AsyncMock(side_effect=Exception("Network error"))
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=mock_resp)

        MockSession.return_value = mock_session

        questions = await source.fetch_questions(limit=5)

        # Should return empty list on error
        assert questions == []


@pytest.mark.asyncio
async def test_error_handling_in_get_question_by_id():
    """Test that get_question_by_id handles errors gracefully."""
    source = PolymarketSource()

    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("Network error"))
        MockSession.return_value = mock_session

        question = await source.get_question_by_id("event1")

        # Should return None on error
        assert question is None
