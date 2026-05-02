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

r"""Public entry points for XRTM corpora.

The package-root API intentionally stays focused on the stable registry and the
embedded real-binary corpus. Less-stable helpers remain available from their
submodules and are kept here as lazy compatibility exports.

Example:
    >>> from xrtm.data.corpora import get_corpus, list_available_corpora
    >>> corpus = get_corpus("xrtm-real-binary-v1")
    >>> metadata_list = list_available_corpora(release_gate_only=True)
"""

from __future__ import annotations

from importlib import import_module

from xrtm.data.corpora.forecast_importer import FORECAST_CORPUS_ID
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

__all__ = [
    "REAL_BINARY_CORPUS_ID",
    "FORECAST_CORPUS_ID",
    "RealBinaryQuestionRecord",
    "RealBinaryCorpusSource",
    "load_real_binary_corpus",
    "load_real_binary_questions",
    "load_real_binary_resolved_outcomes",
    "validate_real_binary_corpus",
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
]

_COMPAT_EXPORTS = {
    "FORECAST_HF_DATASET": ("xrtm.data.corpora.forecast_importer", "FORECAST_HF_DATASET"),
    "FOReCAstImporter": ("xrtm.data.corpora.forecast_importer", "FOReCAstImporter"),
    "CorpusImporter": ("xrtm.data.corpora.importers", "CorpusImporter"),
    "ImportManifest": ("xrtm.data.corpora.importers", "ImportManifest"),
    "OfflineCorpusCache": ("xrtm.data.corpora.importers", "OfflineCorpusCache"),
    "DeterministicFixtureImporter": ("xrtm.data.corpora.importers", "DeterministicFixtureImporter"),
    "SplitConfig": ("xrtm.data.corpora.splits", "SplitConfig"),
    "CorpusSplitter": ("xrtm.data.corpora.splits", "CorpusSplitter"),
    "SplitAwareCorpusSource": ("xrtm.data.corpora.splits", "SplitAwareCorpusSource"),
}

def __getattr__(name: str):
    if name in _COMPAT_EXPORTS:
        module_name, attr_name = _COMPAT_EXPORTS[name]
        return getattr(import_module(module_name), attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_COMPAT_EXPORTS))
