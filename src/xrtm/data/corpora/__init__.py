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

r"""Deterministic fixture corpora for offline validation.

The XRTM benchmark corpus policy defines source classification and licensing
requirements for release-gate evaluation. See:
    data/docs/benchmark-corpus-policy.md

Current embedded corpus:
- xrtm-real-binary-v1: Minimal seed corpus (Tier 1, Apache 2.0)

Future large-scale benchmarks (Tier 1):
- ForecastBench: Primary release-gate benchmark (external dependency)

Evaluation-only sources (not approved for release gates):
- FOReCAst: Research/academic dataset (Tier 2, evaluation-only)
- Metaculus: Optional supplemental (Tier 3)
- Polymarket: Pending review (Tier 3)

The corpus registry and importer infrastructure provide:
- Centralized corpus metadata and discovery (registry.py)
- Reproducible offline import/cache mechanisms (importers.py)
- Deterministic train/eval/held-out splits (splits.py)

Example:
    >>> from xrtm.data.corpora import get_corpus, list_available_corpora
    >>> corpus = get_corpus("xrtm-real-binary-v1")
    >>> metadata_list = list_available_corpora(release_gate_only=True)
"""

from xrtm.data.corpora.forecast_importer import (
    FORECAST_CORPUS_ID,
    FORECAST_HF_DATASET,
    FOReCAstImporter,
)
from xrtm.data.corpora.importers import (
    CorpusImporter,
    DeterministicFixtureImporter,
    ImportManifest,
    OfflineCorpusCache,
)
from xrtm.data.corpora.real_binary import (
    REAL_BINARY_CORPUS_ID,
    RealBinaryCorpusSource,
    RealBinaryQuestionRecord,
    load_real_binary_corpus,
    load_real_binary_questions,
    load_real_binary_resolved_outcomes,
    validate_real_binary_corpus,
)
from xrtm.data.corpora.registry import (
    CorpusAvailability,
    CorpusManifest,
    CorpusMetadata,
    CorpusRegistry,
    CorpusSplit,
    CorpusTier,
    LicenseType,
    describe_corpus,
    get_corpus,
    get_corpus_metadata,
    list_available_corpora,
    prepare_corpus,
)
from xrtm.data.corpora.splits import (
    CorpusSplitter,
    SplitAwareCorpusSource,
    SplitConfig,
)

__all__ = [
    # Legacy real-binary exports (backward compatible)
    "REAL_BINARY_CORPUS_ID",
    "RealBinaryQuestionRecord",
    "RealBinaryCorpusSource",
    "load_real_binary_corpus",
    "load_real_binary_questions",
    "load_real_binary_resolved_outcomes",
    "validate_real_binary_corpus",
    # Corpus registry
    "CorpusRegistry",
    "CorpusAvailability",
    "CorpusMetadata",
    "CorpusManifest",
    "CorpusTier",
    "LicenseType",
    "CorpusSplit",
    "describe_corpus",
    "get_corpus",
    "get_corpus_metadata",
    "list_available_corpora",
    "prepare_corpus",
    # Importers
    "CorpusImporter",
    "ImportManifest",
    "OfflineCorpusCache",
    "DeterministicFixtureImporter",
    "FOReCAstImporter",
    # Splits
    "SplitConfig",
    "CorpusSplitter",
    "SplitAwareCorpusSource",
    # External corpora
    "FORECAST_CORPUS_ID",
    "FORECAST_HF_DATASET",
]
