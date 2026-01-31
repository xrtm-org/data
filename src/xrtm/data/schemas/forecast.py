# coding=utf-8
# Copyright 2026 XRTM Team. All rights reserved.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MetadataBase(BaseModel):
    r"""
    A foundational metadata block used to ensure consistency across schemas.
    """

    model_config = ConfigDict(extra="allow")
    id: str = Field(default_factory=lambda: "meta_" + str(datetime.now(timezone.utc).timestamp()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    snapshot_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Zero Leakage: The specific 'Time T' at which the world state was frozen."
    )
    tags: List[str] = Field(default_factory=list)
    subject_type: Optional[str] = None
    source_version: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def get(self, key: str, default: Any = None) -> Any:
        r"""Backward compatibility for dict-like access."""
        return getattr(self, key, default)


class ForecastQuestion(BaseModel):
    r"""
    The standardized input format for a forecasting task.
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
    metadata: MetadataBase = Field(default_factory=MetadataBase)

    @property
    def content(self) -> Optional[str]:
        r"""Backward compatibility alias for description."""
        return self.description


class CausalNode(BaseModel):
    r"""
    Represents a single step in a logical reasoning chain.
    """
    event: str = Field(..., description="The assumption or event in the chain")
    probability: Optional[float] = Field(None, ge=0, le=1)
    description: Optional[str] = None
    node_id: str = Field(
        default_factory=lambda: "node_" + str(datetime.now().timestamp()), description="Unique ID for graph operations"
    )


class CausalEdge(BaseModel):
    r"""
    Represents a directed causal dependency between two reasoning nodes.
    """
    source: str
    target: str
    weight: float = Field(default=1.0, ge=0, le=1)
    description: Optional[str] = None


class ConfidenceInterval(BaseModel):
    r"""Standard range for probabilistic calibration."""
    low: float
    high: float
    level: float = 0.9


class ForecastOutput(BaseModel):
    r"""
    The structured result of an agent's forecasting reasoning, compliant with Governance v1.
    """
    question_id: str
    probability: float = Field(
        ...,
        alias="confidence",
        validation_alias=AliasChoices("probability", "confidence"),
        ge=0,
        le=1,
        description="The assigned probability of the primary outcome",
    )
    uncertainty: Optional[float] = Field(None, ge=0, le=1)
    confidence_interval: Optional[ConfidenceInterval] = None
    reasoning: str = Field(..., description="Narrative reasoning for the forecast")
    logical_trace: List[CausalNode] = Field(
        default_factory=list, description="The Bayesian-style sequence of assumptions (Mental Model)"
    )
    logical_edges: List[CausalEdge] = Field(
        default_factory=list, description="Causal dependencies between nodes in the trace"
    )
    structural_trace: List[str] = Field(default_factory=list, description="Order of graph nodes executed (Audit Trail)")
    calibration_metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: MetadataBase = Field(default_factory=MetadataBase)

    @property
    def confidence(self) -> float:
        r"""Backward compatibility alias for probability."""
        return self.probability

    @confidence.setter
    def confidence(self, value: float):
        r"""Backward compatibility setter for probability."""
        self.probability = value

    def to_networkx(self) -> Any:
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for to_networkx(). Install it with 'pip install networkx'.")
        dg = nx.DiGraph()
        for node in self.logical_trace:
            dg.add_node(
                node.node_id,
                event=node.event,
                probability=node.probability,
                description=node.description,
            )
        for edge in self.logical_edges:
            dg.add_edge(edge.source, edge.target, weight=edge.weight, description=edge.description)
        return dg


__all__ = ["MetadataBase", "ForecastQuestion", "CausalNode", "CausalEdge", "ForecastOutput"]
