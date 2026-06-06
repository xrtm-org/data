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

r"""Concrete built-in corpus registrations."""

from __future__ import annotations

from typing import List

from xrtm.data.corpora.real_binary import REAL_BINARY_CORPUS_ID, RealBinaryCorpusSource
from xrtm.data.corpora.registry import (
    CorpusManifest,
    CorpusMetadata,
    CorpusSplit,
    CorpusTier,
    LicenseType,
)


def build_builtin_manifests() -> List[CorpusManifest]:
    """Build manifests for the corpora shipped with the registry bootstrap."""
    return [
        _build_real_binary_manifest(),
    ]


def _build_real_binary_manifest() -> CorpusManifest:
    real_binary_metadata = CorpusMetadata(
        corpus_id=REAL_BINARY_CORPUS_ID,
        name="XRTM Real Binary v1",
        tier=CorpusTier.TIER_1,
        license_type=LicenseType.APACHE_2_0,
        description="Minimal deterministic real-world binary question corpus for CI smoke tests",
        version="1.0",
        release_gate_approved=True,
        bundled=True,
        size_estimate=25,
        tags=["binary", "deterministic", "embedded", "seed-corpus"],
        provenance_url="https://github.com/xrtm/xrtm",
        license_url="https://www.apache.org/licenses/LICENSE-2.0",
    )

    return CorpusManifest(
        corpus_id=REAL_BINARY_CORPUS_ID,
        metadata=real_binary_metadata,
        loader_fn=lambda: RealBinaryCorpusSource(),
        available_splits=[CorpusSplit.FULL],
        default_split=CorpusSplit.FULL,
    )
