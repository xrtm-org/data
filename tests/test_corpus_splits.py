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

from datetime import datetime

import pytest

from xrtm.data.corpora import load_real_binary_questions
from xrtm.data.corpora.splits import (
    CorpusSplitter,
    SplitAwareCorpusSource,
    SplitConfig,
)


def test_split_config_valid_ratios():
    config = SplitConfig(train_ratio=0.7, eval_ratio=0.2, held_out_ratio=0.1)
    assert config.train_ratio == 0.7
    assert config.eval_ratio == 0.2
    assert config.held_out_ratio == 0.1


def test_split_config_invalid_ratios():
    with pytest.raises(ValueError, match="must sum to 1.0"):
        SplitConfig(train_ratio=0.5, eval_ratio=0.3, held_out_ratio=0.1)


def test_split_config_to_dict():
    config = SplitConfig(
        train_ratio=0.7,
        eval_ratio=0.2,
        held_out_ratio=0.1,
        seed=42,
    )
    data = config.to_dict()
    assert data["train_ratio"] == 0.7
    assert data["eval_ratio"] == 0.2
    assert data["seed"] == 42


def test_split_config_from_dict():
    data = {
        "train_ratio": 0.7,
        "eval_ratio": 0.2,
        "held_out_ratio": 0.1,
        "seed": 42,
        "temporal_split": False,
        "temporal_cutoff": None,
    }
    config = SplitConfig.from_dict(data)
    assert config.train_ratio == 0.7
    assert config.seed == 42
    assert config.temporal_split is False


def test_split_config_from_dict_with_temporal_cutoff():
    data = {
        "train_ratio": 0.7,
        "eval_ratio": 0.2,
        "held_out_ratio": 0.1,
        "seed": 42,
        "temporal_split": True,
        "temporal_cutoff": "2023-06-01T00:00:00",
    }
    config = SplitConfig.from_dict(data)
    assert config.temporal_split is True
    assert config.temporal_cutoff == datetime(2023, 6, 1)


def test_corpus_splitter_random_split():
    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    assert "train" in splits
    assert "eval" in splits
    assert "held-out" in splits

    total = len(splits["train"]) + len(splits["eval"]) + len(splits["held-out"])
    assert total == len(questions)

    assert len(splits["train"]) > len(splits["eval"])
    assert len(splits["eval"]) > len(splits["held-out"])


def test_corpus_splitter_deterministic():
    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)

    splitter1 = CorpusSplitter(config)
    splits1 = splitter1.split_corpus(questions)

    splitter2 = CorpusSplitter(config)
    splits2 = splitter2.split_corpus(questions)

    assert [q.id for q in splits1["train"]] == [q.id for q in splits2["train"]]
    assert [q.id for q in splits1["eval"]] == [q.id for q in splits2["eval"]]
    assert [q.id for q in splits1["held-out"]] == [q.id for q in splits2["held-out"]]


def test_corpus_splitter_different_seeds():
    questions = load_real_binary_questions()
    config1 = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    config2 = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=99)

    splitter1 = CorpusSplitter(config1)
    splits1 = splitter1.split_corpus(questions)

    splitter2 = CorpusSplitter(config2)
    splits2 = splitter2.split_corpus(questions)

    assert [q.id for q in splits1["train"]] != [q.id for q in splits2["train"]]


def test_corpus_splitter_temporal_split():
    from datetime import timezone

    questions = load_real_binary_questions()
    cutoff = datetime(2023, 7, 1, tzinfo=timezone.utc)
    config = SplitConfig(
        train_ratio=0.7,
        eval_ratio=0.3,
        held_out_ratio=0.0,
        temporal_split=True,
        temporal_cutoff=cutoff,
        seed=42,
    )
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    for question in splits["held-out"]:
        snapshot = question.metadata.snapshot_time
        if snapshot and snapshot.tzinfo is None:
            snapshot = snapshot.replace(tzinfo=timezone.utc)
        assert snapshot is None or snapshot >= cutoff

    for question in splits["train"] + splits["eval"]:
        snapshot = question.metadata.snapshot_time
        if snapshot and snapshot.tzinfo is None:
            snapshot = snapshot.replace(tzinfo=timezone.utc)
        assert snapshot is not None and snapshot < cutoff


def test_corpus_splitter_temporal_split_without_cutoff():
    questions = load_real_binary_questions()
    config = SplitConfig(
        train_ratio=0.7,
        eval_ratio=0.2,
        held_out_ratio=0.1,
        temporal_split=True,
        temporal_cutoff=None,
        seed=42,
    )
    splitter = CorpusSplitter(config)
    with pytest.raises(ValueError, match="temporal_cutoff required"):
        splitter.split_corpus(questions)


def test_corpus_splitter_get_split_signature():
    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)

    sig1 = splitter.get_split_signature(questions)
    sig2 = splitter.get_split_signature(questions)
    assert sig1 == sig2

    config2 = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=99)
    splitter2 = CorpusSplitter(config2)
    sig3 = splitter2.get_split_signature(questions)
    assert sig1 != sig3


@pytest.mark.asyncio
async def test_split_aware_corpus_source_get_split():
    from xrtm.data.corpora import RealBinaryCorpusSource

    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    source = RealBinaryCorpusSource()
    split_source = SplitAwareCorpusSource(source, splits, default_split="train")

    train_questions = split_source.get_split("train")
    assert len(train_questions) == len(splits["train"])


@pytest.mark.asyncio
async def test_split_aware_corpus_source_fetch_questions_with_split():
    from xrtm.data.corpora import RealBinaryCorpusSource

    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    source = RealBinaryCorpusSource()
    split_source = SplitAwareCorpusSource(source, splits, default_split="train")

    train_questions = await split_source.fetch_questions(limit=5, split="train")
    assert len(train_questions) <= 5
    for q in train_questions:
        assert q.id in [sq.id for sq in splits["train"]]


@pytest.mark.asyncio
async def test_split_aware_corpus_source_get_question_by_id():
    from xrtm.data.corpora import RealBinaryCorpusSource

    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    source = RealBinaryCorpusSource()
    split_source = SplitAwareCorpusSource(source, splits, default_split="train")

    train_question_id = splits["train"][0].id
    question = await split_source.get_question_by_id(train_question_id, split="train")
    assert question is not None
    assert question.id == train_question_id

    eval_question_id = splits["eval"][0].id if splits["eval"] else None
    if eval_question_id:
        question_none = await split_source.get_question_by_id(eval_question_id, split="train")
        assert question_none is None


@pytest.mark.asyncio
async def test_split_aware_corpus_source_get_question_split():
    from xrtm.data.corpora import RealBinaryCorpusSource

    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    source = RealBinaryCorpusSource()
    split_source = SplitAwareCorpusSource(source, splits, default_split="train")

    train_question_id = splits["train"][0].id
    split_name = split_source.get_question_split(train_question_id)
    assert split_name == "train"

    unknown_id = "unknown-question-id"
    split_name_none = split_source.get_question_split(unknown_id)
    assert split_name_none is None


@pytest.mark.asyncio
async def test_split_aware_corpus_source_unknown_split():
    from xrtm.data.corpora import RealBinaryCorpusSource

    questions = load_real_binary_questions()
    config = SplitConfig(train_ratio=0.6, eval_ratio=0.3, held_out_ratio=0.1, seed=42)
    splitter = CorpusSplitter(config)
    splits = splitter.split_corpus(questions)

    source = RealBinaryCorpusSource()
    split_source = SplitAwareCorpusSource(source, splits, default_split="train")

    with pytest.raises(ValueError, match="unknown split"):
        split_source.get_split("unknown")
