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
from datetime import datetime, timedelta, timezone

import pytest

from xrtm.data import CausalEdge, CausalNode, ForecastOutput, ForecastResult, MetadataBase
from xrtm.data.core.schemas import TradeEvent, TradeWindow


def test_forecast_result_initialization():
    """Verify that we can create a valid ForecastResult object."""
    output = ForecastResult(
        forecast_request_id="test_q_1",
        probability=0.8,
        reasoning_trace={
            "narrative": "Test reasoning",
            "causal_graph": {
                "nodes": [
                    CausalNode(event="Event A", probability=0.9).model_dump(exclude_none=True),
                    CausalNode(event="Event B", probability=0.8).model_dump(exclude_none=True),
                ],
                "edges": [CausalEdge(source="node_1", target="node_2").model_dump(exclude_none=True)],
            },
        },
        execution_trace=["ingestion", "forecast"],
    )
    assert output.probability == 0.8
    assert output.question_id == "test_q_1"
    assert len(output.forecast_path) == 2
    assert output.execution_trace == ["ingestion", "forecast"]

    payload = output.model_dump(mode="json")
    assert payload["forecast_request_id"] == "test_q_1"
    assert payload["reasoning_trace"]["narrative"] == "Test reasoning"
    assert payload["execution_trace"] == ["ingestion", "forecast"]
    assert "question_id" not in payload
    assert "structural_trace" not in payload


def test_forecast_output_validation_range():
    """Verify that probability range is enforced."""
    with pytest.raises(ValueError):
        ForecastOutput(
            question_id="test_q_2",
            probability=1.5,  # Invalid > 1.0
            reasoning="Invalid prob",
        )


def test_backward_compatibility_aliases():
    """Verify legacy aliases work (confidence -> probability)."""
    output = ForecastOutput(
        question_id="test_q_3",
        confidence=0.7,
        reasoning="Alias test",
        structural_trace=["legacy-stage"],
    )
    assert output.probability == 0.7
    assert output.confidence == 0.7
    assert output.forecast_request_id == "test_q_3"
    assert output.execution_trace == ["legacy-stage"]

    output.confidence = 0.5
    assert output.probability == 0.5


def test_governance_reasoning_trace_alias():
    """Verify governance reasoning_trace maps to runtime logical_trace fields."""
    output = ForecastOutput(
        question_id="test_q_4",
        probability=0.65,
        reasoning_trace={
            "narrative": "Governance trace",
            "causal_graph": {
                "nodes": [{"node_id": "n1", "event": "Event A", "probability": 0.65}],
                "edges": [{"source": "n1", "target": "n2", "weight": 0.4}],
            },
        },
    )

    assert output.reasoning == "Governance trace"
    assert output.logical_trace[0].node_id == "n1"
    assert output.logical_edges[0].source == "n1"
    assert output.reasoning_trace == {
        "narrative": "Governance trace",
        "causal_graph": {
            "nodes": [{"event": "Event A", "probability": 0.65, "node_id": "n1"}],
            "edges": [{"source": "n1", "target": "n2", "weight": 0.4}],
        },
    }


def test_to_networkx_conversion():
    """Verify conversion to NetworkX graph."""
    node1 = CausalNode(event="Start", node_id="n1")
    node2 = CausalNode(event="End", node_id="n2")
    edge = CausalEdge(source="n1", target="n2")

    output = ForecastOutput(
        question_id="q_graph",
        probability=0.5,
        reasoning="Graph test",
        logical_trace=[node1, node2],
        logical_edges=[edge],
    )

    # Check that networkx is handled gracefull if installed
    try:
        import networkx  # noqa: F401

        dg = output.to_networkx()
        assert dg.has_edge("n1", "n2")
    except ImportError:
        pytest.skip("NetworkX not installed")


def test_metadata_temporal_fields_normalize_to_utc():
    """Metadata timestamps remain timezone-aware for deterministic snapshot comparisons."""
    metadata = MetadataBase(
        created_at=datetime(2024, 1, 1, 12, 0),
        snapshot_time=datetime(2024, 1, 1, 13, 0),
    )

    assert metadata.created_at.tzinfo == timezone.utc
    assert metadata.snapshot_time.tzinfo == timezone.utc


def test_trade_window_rejects_future_leakage():
    """TradeWindow enforces that no trade falls outside its snapshot window."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    future_trade = TradeEvent(
        price=0.5,
        amount=1.0,
        timestamp=end + timedelta(seconds=1),
        maker="0xmaker",
        taker="0xtaker",
    )

    with pytest.raises(ValueError, match="trades must fall within"):
        TradeWindow(trades=[future_trade], start_time=start, end_time=end, market_id="m1")


def test_trade_window_normalizes_naive_boundaries_and_timestamps():
    """Legacy naive datetimes are interpreted as UTC before invariant checks."""
    trade = TradeEvent(
        price=0.5,
        amount=1.0,
        timestamp=datetime(2024, 1, 1, 12, 0),
        maker="0xmaker",
        taker="0xtaker",
    )
    window = TradeWindow(
        trades=[trade],
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2),
        market_id="m1",
    )

    assert window.start_time.tzinfo == timezone.utc
    assert window.trades[0].timestamp.tzinfo == timezone.utc
