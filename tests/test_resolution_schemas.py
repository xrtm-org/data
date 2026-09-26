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

r"""Tests for the ResolvedQuestion schema."""

from datetime import datetime, timezone

import pytest

from xrtm.data import ResolvedQuestion


def test_outcome_range_is_enforced():
    with pytest.raises(ValueError):
        ResolvedQuestion(question_id="q1", venue="test", outcome=1.5)


def test_resolved_at_normalizes_naive_time_to_utc():
    resolved = ResolvedQuestion(
        question_id="q2",
        venue="test",
        outcome=1.0,
        resolved_at=datetime(2026, 9, 26, 12, 0),
    )
    assert resolved.resolved_at.tzinfo == timezone.utc


def test_resolved_question_round_trips():
    resolved = ResolvedQuestion(
        question_id="manifold-abc",
        venue="manifold",
        title="Will X happen?",
        outcome=0.0,
        url="https://manifold.markets/x",
    )
    payload = resolved.model_dump(mode="json")
    reloaded = ResolvedQuestion.model_validate(payload)
    assert reloaded.question_id == "manifold-abc"
    assert reloaded.outcome == 0.0
    assert reloaded.url == "https://manifold.markets/x"
