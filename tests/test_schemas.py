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
from datetime import datetime
from xrtm.data import ForecastOutput, ForecastQuestion, CausalNode, CausalEdge

def test_forecast_output_initialization():
    """Verify that we can create a valid ForecastOutput object."""
    output = ForecastOutput(
        question_id="test_q_1",
        probability=0.8,
        reasoning="Test reasoning",
        logical_trace=[
            CausalNode(event="Event A", probability=0.9),
            CausalNode(event="Event B", probability=0.8)
        ],
        logical_edges=[
            CausalEdge(source="node_1", target="node_2")
        ]
    )
    assert output.probability == 0.8
    assert len(output.logical_trace) == 2

def test_forecast_output_validation_range():
    """Verify that probability range is enforced."""
    with pytest.raises(ValueError):
        ForecastOutput(
            question_id="test_q_2",
            probability=1.5, # Invalid > 1.0
            reasoning="Invalid prob"
        )

def test_backward_compatibility_aliases():
    """Verify legacy aliases work (confidence -> probability)."""
    output = ForecastOutput(
        question_id="test_q_3",
        confidence=0.7,
        reasoning="Alias test"
    )
    assert output.probability == 0.7
    assert output.confidence == 0.7

    output.confidence = 0.5
    assert output.probability == 0.5

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
        logical_edges=[edge]
    )

    # Check that networkx is handled gracefull if installed
    try:
        import networkx
        dg = output.to_networkx()
        assert dg.has_edge("n1", "n2")
    except ImportError:
        pytest.skip("NetworkX not installed")
