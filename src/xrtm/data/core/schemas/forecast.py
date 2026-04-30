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

r"""
Core forecast schemas for xrtm-data.

This module defines the foundational Pydantic models used across the xrtm
ecosystem for representing forecast questions, outputs, and causal reasoning
structures.

Example:
    >>> from xrtm.data.core.schemas import ForecastQuestion
    >>> q = ForecastQuestion(id="q1", title="Will it rain tomorrow?")
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class MetadataBase(BaseModel):
    r"""
    A foundational metadata block used to ensure consistency across schemas.

    This model captures temporal information critical for the Zero Leakage
    principle, ensuring all data is properly timestamped.

    Attributes:
        id: Unique identifier for this metadata block.
        created_at: When this metadata was created.
        snapshot_time: The "Time T" at which the world state was frozen.
        tags: List of classification tags.
        subject_type: Type of subject being forecasted.
        source_version: Version of the data source.
        raw_data: Original unprocessed data.
    """

    model_config = ConfigDict(extra="allow")
    id: str = Field(
        default_factory=lambda: "meta_" + str(datetime.now(timezone.utc).timestamp()),
        description="Unique identifier for this metadata block",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this metadata was created",
    )
    snapshot_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Zero Leakage: The specific 'Time T' at which the world state was frozen.",
    )
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    subject_type: Optional[str] = Field(None, description="Type of subject being forecasted")
    source_version: Optional[str] = Field(None, description="Version of the data source")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Original unprocessed data")

    def get(self, key: str, default: Any = None) -> Any:
        r"""Backward compatibility for dict-like access."""
        return getattr(self, key, default)


class ForecastQuestion(BaseModel):
    r"""
    The standardized input format for a forecasting task.

    This is the primary input schema used throughout the xrtm ecosystem
    to represent a question or hypothesis to be forecasted.

    Attributes:
        id: Unique identifier for the question.
        title: The main question or statement being forecasted.
        description: Detailed context and background.
        resolution_criteria: Explicit rules for ground truth determination.
        metadata: Associated metadata including temporal information.

    Example:
        >>> q = ForecastQuestion(
        ...     id="q1",
        ...     title="Will Company X announce earnings above expectations?",
        ...     description="Q4 earnings call scheduled for Jan 15",
        ... )
    """

    id: str = Field(..., description="Unique identifier for the question")
    title: str = Field(..., description="The main question or statement being forecasted")
    description: Optional[str] = Field(
        None,
        alias="content",
        validation_alias=AliasChoices("description", "content"),
        description="Detailed context and background",
    )
    resolution_criteria: Optional[str] = Field(None, description="Explicit rules for ground truth determination")
    metadata: MetadataBase = Field(default_factory=MetadataBase)  # type: ignore[arg-type]

    @property
    def content(self) -> Optional[str]:
        r"""Backward compatibility alias for description."""
        return self.description


class CausalNode(BaseModel):
    r"""
    Represents a single step in a logical reasoning chain.

    Attributes:
        event: The assumption or event in the chain.
        probability: Optional probability assigned to this node.
        description: Additional context for this reasoning step.
        node_id: Unique identifier for graph operations.
    """

    event: str = Field(..., description="The assumption or event in the chain")
    probability: Optional[float] = Field(None, ge=0, le=1, description="Probability of this event")
    description: Optional[str] = Field(None, description="Additional context")
    node_id: str = Field(
        default_factory=lambda: "node_" + str(datetime.now().timestamp()),
        description="Unique ID for graph operations",
    )


class CausalEdge(BaseModel):
    r"""
    Represents a directed causal dependency between two reasoning nodes.

    Attributes:
        source: ID of the source node.
        target: ID of the target node.
        weight: Strength of the causal relationship.
        description: Context for this causal link.
    """

    source: str = Field(..., description="ID of the source node")
    target: str = Field(..., description="ID of the target node")
    weight: float = Field(default=1.0, ge=0, le=1, description="Strength of causal relationship")
    description: Optional[str] = Field(None, description="Context for this causal link")


class ConfidenceInterval(BaseModel):
    r"""
    Standard range for probabilistic calibration.

    Attributes:
        low: Lower bound of the interval.
        high: Upper bound of the interval.
        level: Confidence level (default 0.9 for 90%).
    """

    low: float = Field(..., description="Lower bound")
    high: float = Field(..., description="Upper bound")
    level: float = Field(0.9, ge=0, le=1, description="Confidence level")


class ForecastOutput(BaseModel):
    r"""
    The structured result of an agent's forecasting reasoning.

    This model captures not just the final probability, but also the
    complete reasoning chain that led to it, enabling audit and calibration.

    Attributes:
        question_id: Reference to the input question.
        probability: The assigned probability of the primary outcome.
        uncertainty: Optional measure of forecast uncertainty.
        confidence_interval: Range for calibration.
        reasoning: Narrative reasoning for the forecast.
        logical_trace: Bayesian-style sequence of assumptions.
        logical_edges: Causal dependencies between nodes.
        structural_trace: Order of graph nodes executed.
        calibration_metrics: Performance metrics.
        metadata: Associated temporal and source metadata.
    """

    question_id: str = Field(..., description="Reference to the input question")
    probability: float = Field(
        ...,
        alias="confidence",
        validation_alias=AliasChoices("probability", "confidence"),
        ge=0,
        le=1,
        description="The assigned probability of the primary outcome",
    )
    uncertainty: Optional[float] = Field(None, ge=0, le=1, description="Measure of forecast uncertainty")
    confidence_interval: Optional[ConfidenceInterval] = None
    reasoning: str = Field(..., description="Narrative reasoning for the forecast")
    logical_trace: List[CausalNode] = Field(
        default_factory=list, description="The Bayesian-style sequence of assumptions"
    )
    logical_edges: List[CausalEdge] = Field(default_factory=list, description="Causal dependencies between nodes")
    structural_trace: List[str] = Field(default_factory=list, description="Order of graph nodes executed")
    calibration_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    metadata: MetadataBase = Field(default_factory=MetadataBase)  # type: ignore[arg-type]

    @model_validator(mode="before")
    @classmethod
    def _apply_reasoning_trace_alias(cls, data: Any) -> Any:
        r"""Accept governance ``reasoning_trace`` as an alias for runtime trace fields."""
        if not isinstance(data, dict) or "reasoning_trace" not in data:
            return data

        trace = data["reasoning_trace"]
        updated = dict(data)
        if isinstance(trace, dict):
            if "reasoning" not in updated and isinstance(trace.get("narrative"), str):
                updated["reasoning"] = trace["narrative"]

            causal_graph = trace.get("causal_graph")
            if isinstance(causal_graph, dict):
                if "logical_trace" not in updated and "nodes" in causal_graph:
                    updated["logical_trace"] = causal_graph["nodes"]
                if "logical_edges" not in updated and "edges" in causal_graph:
                    updated["logical_edges"] = causal_graph["edges"]
        elif isinstance(trace, list) and "logical_trace" not in updated:
            updated["logical_trace"] = trace

        return updated

    @property
    def reasoning_trace(self) -> Dict[str, Any]:
        r"""Governance-compatible alias for the narrative and causal graph trace."""
        return {
            "narrative": self.reasoning,
            "causal_graph": {
                "nodes": [node.model_dump(exclude_none=True) for node in self.logical_trace],
                "edges": [edge.model_dump(exclude_none=True) for edge in self.logical_edges],
            },
        }

    @property
    def confidence(self) -> float:
        r"""Backward compatibility alias for probability."""
        return self.probability

    @confidence.setter
    def confidence(self, value: float) -> None:
        r"""Backward compatibility setter for probability."""
        self.probability = value

    def to_networkx(self) -> Any:
        r"""
        Convert the logical trace to a NetworkX directed graph.

        Returns:
            A NetworkX DiGraph representing the reasoning chain.

        Raises:
            ImportError: If networkx is not installed.
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for to_networkx(). Install it with 'uv add networkx'.")
        dg = nx.DiGraph()
        dg.add_nodes_from(
            (
                node.node_id,
                {"event": node.event, "probability": node.probability, "description": node.description},
            )
            for node in self.logical_trace
        )
        dg.add_edges_from(
            (edge.source, edge.target, {"weight": edge.weight, "description": edge.description})
            for edge in self.logical_edges
        )
        return dg


__all__ = [
    "MetadataBase",
    "ForecastQuestion",
    "CausalNode",
    "CausalEdge",
    "ConfidenceInterval",
    "ForecastOutput",
]
