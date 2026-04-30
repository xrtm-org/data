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

import pytest

from xrtm.data import ForecastQuestion
from xrtm.data.corpora import (
    REAL_BINARY_CORPUS_ID,
    RealBinaryCorpusSource,
    load_real_binary_corpus,
    load_real_binary_questions,
    load_real_binary_resolved_outcomes,
    validate_real_binary_corpus,
)


def test_real_binary_corpus_shape_and_resolution_coverage():
    records = load_real_binary_corpus()

    assert len(records) >= 20
    assert len({record.id for record in records}) == len(records)
    assert all(record.title.endswith("?") for record in records)
    assert all(record.content for record in records)
    assert all(record.resolution_criteria for record in records)
    assert all(record.snapshot_time.tzinfo is not None for record in records)
    assert all(record.source for record in records)
    assert all("binary" in record.tags for record in records)
    assert all(record.source_metadata.get("source_url") for record in records)

    outcomes = load_real_binary_resolved_outcomes()
    assert len(outcomes) >= 10
    assert any(outcomes.values())
    assert not all(outcomes.values())


def test_real_binary_corpus_converts_to_forecast_questions():
    records = load_real_binary_corpus()
    questions = load_real_binary_questions()

    assert len(questions) == len(records)
    assert all(isinstance(question, ForecastQuestion) for question in questions)

    record = records[0]
    question = questions[0]
    assert question.id == record.id
    assert question.title == record.title
    assert question.content == record.content
    assert question.resolution_criteria == record.resolution_criteria
    assert question.metadata.id == f"{record.id}:metadata"
    assert question.metadata.created_at == record.snapshot_time
    assert question.metadata.snapshot_time == record.snapshot_time
    assert question.metadata.subject_type == "binary"
    assert question.metadata.source_version == REAL_BINARY_CORPUS_ID
    assert question.metadata.raw_data is not None
    assert question.metadata.raw_data["id"] == record.id
    assert question.metadata.get("source") == record.source
    assert question.metadata.get("resolved_outcome") is record.resolved_outcome
    assert question.metadata.get("resolution_time") == record.resolution_time


def test_real_binary_loading_is_deterministic_and_returns_copies():
    first = [question.model_dump(mode="json") for question in load_real_binary_questions()]
    second = [question.model_dump(mode="json") for question in load_real_binary_questions()]

    assert first == second

    mutated = load_real_binary_questions(limit=1)[0]
    mutated.title = "mutated"

    assert load_real_binary_questions(limit=1)[0].title != "mutated"


def test_real_binary_validator_rejects_duplicate_ids():
    records = [record.model_dump(mode="json") for record in load_real_binary_corpus()]
    records[1]["id"] = records[0]["id"]

    with pytest.raises(ValueError, match="duplicate"):
        validate_real_binary_corpus(records)


@pytest.mark.asyncio
async def test_real_binary_corpus_source_fetch_and_get():
    source = RealBinaryCorpusSource()

    questions = await source.fetch_questions(limit=25)
    assert [question.id for question in questions] == [record.id for record in load_real_binary_corpus()]

    filtered = await source.fetch_questions(query="Federal Reserve", limit=5)
    assert [question.id for question in filtered] == ["real-binary-2023-fed-mar-hike"]

    question = await source.get_question_by_id("real-binary-2023-fed-mar-hike")
    assert question is not None
    assert question.metadata.get("resolved_outcome") is True

    question.title = "mutated"
    fresh_question = await source.get_question_by_id("real-binary-2023-fed-mar-hike")
    assert fresh_question is not None
    assert fresh_question.title != "mutated"
