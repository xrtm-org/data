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

from collections.abc import ItemsView, KeysView, ValuesView
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


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

    @field_validator("created_at", "snapshot_time", mode="after")
    @classmethod
    def _normalize_temporal_fields(cls, value: datetime) -> datetime:
        r"""Store temporal boundary fields as timezone-aware UTC datetimes."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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


ForecastRequest = ForecastQuestion


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
    weight: float = Field(default=1.0, ge=-1, le=1, description="Strength of causal relationship (negative = inhibitory)")
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


class MappingCompatibleModel(BaseModel):
    r"""Base model with lightweight dict-style compatibility helpers."""

    def get(self, key: str, default: Any = None) -> Any:
        r"""Provide dict-style access for compatibility shims."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def items(self) -> ItemsView[str, Any]:
        return self.model_dump(exclude_none=True).items()

    def keys(self) -> KeysView[str]:
        return self.model_dump(exclude_none=True).keys()

    def values(self) -> ValuesView[Any]:
        return self.model_dump(exclude_none=True).values()

    def __iter__(self) -> Generator[tuple[str, Any], None, None]:
        for item in self.model_dump(exclude_none=True).items():
            yield item

    def __len__(self) -> int:
        return len(self.model_dump(exclude_none=True))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return self.model_dump(exclude_none=True) == other
        return super().__eq__(other)


class CausalGraph(MappingCompatibleModel):
    r"""Qualified causal graph embedded inside a reasoning trace."""

    nodes: List[CausalNode] = Field(
        default_factory=list,
        description="Ordered forecast-path nodes inside the qualified causal graph",
    )
    edges: List[CausalEdge] = Field(
        default_factory=list,
        description="Qualified causal graph edges connecting forecast-path nodes",
    )


class ReasoningTrace(MappingCompatibleModel):
    r"""Canonical reasoning trace payload for a forecast result."""

    narrative: str = Field("", description="Narrative reasoning for the forecast result")
    causal_graph: CausalGraph = Field(
        default_factory=CausalGraph,
        description="Qualified causal graph for structured forecast-path reasoning",
    )

    @property
    def forecast_path(self) -> List[CausalNode]:
        r"""Canonical alias for ordered reasoning nodes."""
        return self.causal_graph.nodes

    @forecast_path.setter
    def forecast_path(self, value: List[CausalNode] | List[Dict[str, Any]]) -> None:
        r"""Backward-compatible setter for forecast-path nodes."""
        self.causal_graph.nodes = [
            node if isinstance(node, CausalNode) else CausalNode.model_validate(node) for node in value
        ]


class ForecastOutput(BaseModel):
    r"""
    The structured result of an agent's forecasting reasoning.

    This model captures not just the final probability, but also the
    complete reasoning chain that led to it, enabling audit and calibration.

    Attributes:
        forecast_request_id: Reference to the input forecast request.
        probability: The assigned probability of the primary outcome.
        uncertainty: Optional measure of forecast uncertainty.
        confidence_interval: Range for calibration.
        reasoning_trace: Narrative reasoning plus a qualified causal graph.
        execution_trace: Ordered workflow stages executed to produce the result.
        calibration_metrics: Performance metrics.
        metadata: Associated temporal and source metadata.
    """

    model_config = ConfigDict(populate_by_name=True)

    forecast_request_id: str = Field(
        ...,
        validation_alias=AliasChoices("forecast_request_id", "question_id"),
        description="Reference to the input forecast request",
    )
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
    reasoning_trace: ReasoningTrace = Field(
        ...,
        description="Narrative reasoning trace with a qualified causal graph",
    )
    execution_trace: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("execution_trace", "structural_trace"),
        description="Ordered workflow stages executed for this forecast result",
    )
    calibration_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    metadata: MetadataBase = Field(default_factory=MetadataBase)  # type: ignore[arg-type]

    @model_validator(mode="before")
    @classmethod
    def _normalize_runtime_aliases(cls, data: Any) -> Any:
        r"""Normalize legacy runtime aliases into the canonical result vocabulary."""
        if not isinstance(data, dict):
            return data

        updated = dict(data)
        if "question_id" in updated and "forecast_request_id" not in updated:
            updated["forecast_request_id"] = updated["question_id"]
        if "structural_trace" in updated and "execution_trace" not in updated:
            updated["execution_trace"] = updated["structural_trace"]

        trace = updated.get("reasoning_trace")
        if isinstance(trace, list):
            trace = {
                "narrative": str(updated.get("reasoning", "")),
                "causal_graph": {
                    "nodes": trace,
                    "edges": updated.get("logical_edges", []),
                },
            }
            updated["reasoning_trace"] = trace

        if isinstance(trace, dict):
            trace_dict = dict(trace)
            if "narrative" not in trace_dict and isinstance(updated.get("reasoning"), str):
                trace_dict["narrative"] = updated["reasoning"]
            causal_graph = trace.get("causal_graph")
            if not isinstance(causal_graph, dict):
                causal_graph = {}
            causal_graph = dict(causal_graph)
            if "nodes" not in causal_graph and "logical_trace" in updated:
                causal_graph["nodes"] = updated["logical_trace"]
            if "edges" not in causal_graph and "logical_edges" in updated:
                causal_graph["edges"] = updated["logical_edges"]
            trace_dict["causal_graph"] = causal_graph
            updated["reasoning_trace"] = trace_dict
        elif any(key in updated for key in ("reasoning", "logical_trace", "logical_edges")):
            updated["reasoning_trace"] = {
                "narrative": str(updated.get("reasoning", "")),
                "causal_graph": {
                    "nodes": updated.get("logical_trace", []),
                    "edges": updated.get("logical_edges", []),
                },
            }

        return updated

    @property
    def question_id(self) -> str:
        r"""Backward compatibility alias for ``forecast_request_id``."""
        return self.forecast_request_id

    @question_id.setter
    def question_id(self, value: str) -> None:
        r"""Backward compatibility setter for ``forecast_request_id``."""
        self.forecast_request_id = value

    @property
    def confidence(self) -> float:
        r"""Backward compatibility alias for probability."""
        return self.probability

    @confidence.setter
    def confidence(self, value: float) -> None:
        r"""Backward compatibility setter for probability."""
        self.probability = value

    @property
    def reasoning(self) -> str:
        r"""Backward compatibility alias for ``reasoning_trace.narrative``."""
        return self.reasoning_trace.narrative

    @reasoning.setter
    def reasoning(self, value: str) -> None:
        r"""Backward compatibility setter for ``reasoning_trace.narrative``."""
        self.reasoning_trace.narrative = value

    @property
    def logical_trace(self) -> List[CausalNode]:
        r"""Backward compatibility alias for reasoning-trace nodes."""
        return self.reasoning_trace.causal_graph.nodes

    @logical_trace.setter
    def logical_trace(self, value: List[CausalNode] | List[Dict[str, Any]]) -> None:
        r"""Backward compatibility setter for reasoning-trace nodes."""
        self.reasoning_trace.causal_graph.nodes = [
            node if isinstance(node, CausalNode) else CausalNode.model_validate(node) for node in value
        ]

    @property
    def logical_edges(self) -> List[CausalEdge]:
        r"""Backward compatibility alias for reasoning-trace edges."""
        return self.reasoning_trace.causal_graph.edges

    @logical_edges.setter
    def logical_edges(self, value: List[CausalEdge] | List[Dict[str, Any]]) -> None:
        r"""Backward compatibility setter for reasoning-trace edges."""
        self.reasoning_trace.causal_graph.edges = [
            edge if isinstance(edge, CausalEdge) else CausalEdge.model_validate(edge) for edge in value
        ]

    @property
    def forecast_path(self) -> List[CausalNode]:
        r"""Canonical alias for the ordered reasoning path."""
        return self.reasoning_trace.forecast_path

    @forecast_path.setter
    def forecast_path(self, value: List[CausalNode] | List[Dict[str, Any]]) -> None:
        r"""Canonical setter for the ordered reasoning path."""
        self.reasoning_trace.forecast_path = value

    @property
    def structural_trace(self) -> List[str]:
        r"""Backward compatibility alias for ``execution_trace``."""
        return self.execution_trace

    @structural_trace.setter
    def structural_trace(self, value: List[str]) -> None:
        r"""Backward compatibility setter for ``execution_trace``."""
        self.execution_trace = list(value)

    def to_networkx(self) -> Any:
        r"""
        Convert the reasoning trace to a NetworkX directed graph.

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
    "ForecastRequest",
    "CausalNode",
    "CausalEdge",
    "CausalGraph",
    "ConfidenceInterval",
    "ReasoningTrace",
    "ForecastOutput",
    "ForecastResult",
]

ForecastResult = ForecastOutput
