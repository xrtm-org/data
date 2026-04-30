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
xrtm-data: The Foundation Layer (Layer 1)

This package provides the core data schemas and interfaces for the xrtm
ecosystem. It follows the "Zero Leakage" principle, ensuring all data
is properly timestamped for temporal isolation.

Structure:
    - core/: Domain-agnostic interfaces and schemas
    - kit/: High-level processors and utilities
    - providers/: External data source implementations

Example:
    >>> from xrtm.data import ForecastQuestion, DataSource
    >>> from xrtm.data.providers import LocalDataSource
"""

# Core interfaces
from xrtm.data.core import DataSource, DataSourceError, SourceFetchError, SourceTemporalIntegrityError

# Core schemas (public API)
from xrtm.data.core.schemas import (
    CausalEdge,
    CausalNode,
    ConfidenceInterval,
    ForecastOutput,
    ForecastQuestion,
    MetadataBase,
)

__all__ = [
    # Interfaces
    "DataSource",
    "DataSourceError",
    "SourceFetchError",
    "SourceTemporalIntegrityError",
    # Schemas
    "MetadataBase",
    "ForecastQuestion",
    "ForecastOutput",
    "CausalNode",
    "CausalEdge",
    "ConfidenceInterval",
]
