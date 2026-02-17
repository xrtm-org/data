import json

import pytest

from xrtm.data.providers.local import LocalDataSource


@pytest.fixture
def sample_data(tmp_path):
    data = [
        {"id": "q1", "title": "Will it snow?", "description": "Weather forecast", "resolution_criteria": "If it snows"},
        {
            "id": "q2",
            "title": "Will AI take over?",
            "description": "AGI prediction",
            "resolution_criteria": "If AI is AGI",
        },
        {
            "id": "q3",
            "title": "Will stock go up?",
            "description": "Market forecast",
            "resolution_criteria": "If stock > 100",
        },
    ]
    file_path = tmp_path / "questions.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return str(file_path)


@pytest.mark.asyncio
async def test_fetch_questions_all(sample_data):
    source = LocalDataSource(sample_data)
    questions = await source.fetch_questions(limit=10)
    assert len(questions) == 3
    assert questions[0].id == "q1"
    assert questions[1].id == "q2"
    assert questions[2].id == "q3"


@pytest.mark.asyncio
async def test_fetch_questions_limit(sample_data):
    source = LocalDataSource(sample_data)
    questions = await source.fetch_questions(limit=2)
    assert len(questions) == 2
    assert questions[0].id == "q1"
    assert questions[1].id == "q2"


@pytest.mark.asyncio
async def test_fetch_questions_query(sample_data):
    source = LocalDataSource(sample_data)
    questions = await source.fetch_questions(query="AI")
    assert len(questions) == 1
    assert questions[0].id == "q2"


@pytest.mark.asyncio
async def test_fetch_questions_query_case_insensitive(sample_data):
    source = LocalDataSource(sample_data)
    questions = await source.fetch_questions(query="ai")
    assert len(questions) == 1
    assert questions[0].id == "q2"


@pytest.mark.asyncio
async def test_get_question_by_id(sample_data):
    source = LocalDataSource(sample_data)
    q = await source.get_question_by_id("q2")
    assert q is not None
    assert q.id == "q2"
    assert q.title == "Will AI take over?"


@pytest.mark.asyncio
async def test_get_question_by_id_not_found(sample_data):
    source = LocalDataSource(sample_data)
    q = await source.get_question_by_id("nonexistent")
    assert q is None


@pytest.mark.asyncio
async def test_file_missing(tmp_path):
    non_existent_file = str(tmp_path / "missing.json")
    source = LocalDataSource(non_existent_file)

    # Should log error and return empty list
    questions = await source.fetch_questions()
    assert questions == []

    # Should log error and return None
    q = await source.get_question_by_id("q1")
    assert q is None


@pytest.mark.asyncio
async def test_invalid_json(tmp_path):
    file_path = tmp_path / "invalid.json"
    with open(file_path, "w") as f:
        f.write("{invalid json")

    source = LocalDataSource(str(file_path))

    questions = await source.fetch_questions()
    assert questions == []

    q = await source.get_question_by_id("q1")
    assert q is None


@pytest.mark.asyncio
async def test_caching_behavior(sample_data):
    """Verify that file is read only once."""
    source = LocalDataSource(sample_data)

    # First call - should load data
    await source.fetch_questions()
    assert source._questions is not None

    # Modify file on disk
    with open(sample_data, "w") as f:
        json.dump([], f)

    # Second call - should still return original data because it's cached
    questions = await source.fetch_questions()
    assert len(questions) == 3


@pytest.mark.asyncio
async def test_mixed_invalid_data(tmp_path):
    """Verify that invalid items are skipped and valid ones are loaded."""
    data = [
        {"id": "q1", "title": "Valid Q1"},
        {"id": "q2", "title": "Missing fields"},  # Might be valid depending on schema, but let's assume valid enough or make it invalid
        "not a dict",
        {"id": "q3", "title": "Valid Q3"},
        {"invalid": "schema"},  # Missing required fields
    ]
    # ForecastQuestion requires id and title.

    file_path = tmp_path / "mixed.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    source = LocalDataSource(str(file_path))
    questions = await source.fetch_questions()

    # "Missing fields" (q2) has id and title, so it is valid.
    # "not a dict" should be skipped.
    # {"invalid": "schema"} missing id/title, should be skipped.

    assert len(questions) == 3
    ids = {q.id for q in questions}
    assert ids == {"q1", "q2", "q3"}


@pytest.mark.asyncio
async def test_duplicate_ids(tmp_path):
    """Verify that the first occurrence of a duplicate ID is kept."""
    data = [
        {"id": "q1", "title": "First"},
        {"id": "q1", "title": "Second"},
    ]
    file_path = tmp_path / "dupes.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    source = LocalDataSource(str(file_path))
    q = await source.get_question_by_id("q1")

    assert q is not None
    assert q.title == "First"


@pytest.mark.asyncio
async def test_malformed_json_structure(tmp_path):
    """Verify that a non-list JSON root is handled gracefully."""
    data = {"questions": []}
    file_path = tmp_path / "dict_root.json"
    with open(file_path, "w") as f:
        json.dump(data, f)

    source = LocalDataSource(str(file_path))
    questions = await source.fetch_questions()

    assert questions == []

@pytest.mark.asyncio
async def test_returned_objects_are_copies(sample_data):
    """Verify that returned objects are copies and mutation doesn't affect cache."""
    source = LocalDataSource(sample_data)

    # Fetch a question
    q1 = await source.get_question_by_id("q1")
    assert q1 is not None
    original_title = q1.title

    # Mutate it
    q1.title = "Mutated Title"

    # Fetch it again
    q2 = await source.get_question_by_id("q1")
    assert q2.title == original_title
    assert q2.title != q1.title
