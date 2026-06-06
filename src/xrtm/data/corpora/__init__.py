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

r"""Public entry points for XRTM corpora."""

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
    CorpusManifest,
    CorpusMetadata,
    CorpusRegistry,
    CorpusSplit,
    CorpusTier,
    LicenseType,
    get_corpus,
    get_corpus_metadata,
    list_available_corpora,
)

__all__ = [
    "REAL_BINARY_CORPUS_ID",
    "RealBinaryQuestionRecord",
    "RealBinaryCorpusSource",
    "load_real_binary_corpus",
    "load_real_binary_questions",
    "load_real_binary_resolved_outcomes",
    "validate_real_binary_corpus",
    "CorpusRegistry",
    "CorpusMetadata",
    "CorpusManifest",
    "CorpusTier",
    "LicenseType",
    "CorpusSplit",
    "get_corpus",
    "get_corpus_metadata",
    "list_available_corpora",
]
