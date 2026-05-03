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

r"""Concrete built-in corpus registrations.

This module keeps registry bootstrap and corpus-specific cache workflows out of
``registry.py`` so the registry can stay focused on generic manifest handling.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import List, Optional

from xrtm.data.core import DataSource
from xrtm.data.corpora.forecast_importer import FORECAST_CORPUS_ID, FOReCAstImporter
from xrtm.data.corpora.importers import OfflineCorpusCache
from xrtm.data.corpora.real_binary import REAL_BINARY_CORPUS_ID, RealBinaryCorpusSource
from xrtm.data.corpora.registry import (
    CorpusAvailability,
    CorpusManifest,
    CorpusMetadata,
    CorpusSplit,
    CorpusTier,
    LicenseType,
)

_FORECAST_VERSION = "1.0"

def build_builtin_manifests() -> List[CorpusManifest]:
    """Build manifests for the corpora shipped with the registry bootstrap."""
    return [
        _build_real_binary_manifest(),
        _build_forecast_manifest(),
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

def _build_forecast_manifest() -> CorpusManifest:
    forecast_metadata = CorpusMetadata(
        corpus_id=FORECAST_CORPUS_ID,
        name="FOReCAst (Future Outcome Reasoning and Confidence Assessment)",
        tier=CorpusTier.TIER_2,
        license_type=LicenseType.MIT,
        description="Academic benchmark dataset for probabilistic forecasting from NeurIPS 2025. "
        "1,390 resolved questions from Metaculus. Evaluation-only until Tier 1 approval.",
        version=_FORECAST_VERSION,
        release_gate_approved=False,
        bundled=False,
        size_estimate=1390,
        tags=["forecast", "external", "evaluation-only", "probabilistic"],
        provenance_url="https://huggingface.co/datasets/MoyYuan/FOReCAst",
        license_url="https://opensource.org/licenses/MIT",
        citation="FOReCAst: Future Outcome Reasoning and Confidence Assessment. NeurIPS 2025 Datasets and Benchmarks Track.",
        extra={
            "tier_status": "evaluation-only",
            "promotion_required": "explicit approval needed for Tier 1 promotion",
            "non_commercial_clause": "pending clarification",
        },
    )

    return CorpusManifest(
        corpus_id=FORECAST_CORPUS_ID,
        metadata=forecast_metadata,
        loader_fn=lambda: _load_forecast_source(forecast_metadata.version),
        available_splits=[CorpusSplit.FULL, CorpusSplit.TRAIN, CorpusSplit.EVAL],
        default_split=CorpusSplit.FULL,
        importer_module="xrtm.data.corpora.forecast_importer",
        availability_loader=lambda cache_root: _describe_forecast_corpus(
            forecast_metadata.version,
            cache_root=cache_root,
        ),
        prepare_loader=lambda cache_root, refresh, use_hf_datasets: _prepare_forecast_corpus(
            forecast_metadata.version,
            cache_root=cache_root,
            refresh=refresh,
            use_hf_datasets=use_hf_datasets,
        ),
    )

def _describe_forecast_corpus(
    version: str,
    *,
    cache_root: Optional[Path] = None,
) -> CorpusAvailability:
    resolved_cache_root = _resolve_cache_root(cache_root)
    cache = OfflineCorpusCache(resolved_cache_root)
    manifest = cache.load_manifest(FORECAST_CORPUS_ID, version)
    import_method = manifest.metadata.get("import_method") if manifest is not None else None
    source_mode = "preview" if import_method in {None, "fixture"} else "external-cache"

    return CorpusAvailability(
        corpus_id=FORECAST_CORPUS_ID,
        version=version,
        source_mode=source_mode,
        bundled=False,
        already_cached=manifest is not None,
        record_count=manifest.record_count if manifest is not None else None,
        import_method=import_method,
        cache_root=resolved_cache_root,
        data_dir=cache.get_corpus_dir(FORECAST_CORPUS_ID, version),
        manifest_path=cache.get_manifest_path(FORECAST_CORPUS_ID, version),
    )

def _prepare_forecast_corpus(
    version: str,
    *,
    cache_root: Optional[Path] = None,
    refresh: bool = False,
    use_hf_datasets: bool = True,
) -> CorpusAvailability:
    resolved_cache_root = _resolve_cache_root(cache_root)
    cache = OfflineCorpusCache(resolved_cache_root)
    if cache.is_cached(FORECAST_CORPUS_ID, version) and not refresh:
        return _describe_forecast_corpus(version, cache_root=resolved_cache_root)

    importer = FOReCAstImporter(use_hf_datasets=use_hf_datasets)
    data_dir = cache.get_corpus_dir(FORECAST_CORPUS_ID, version)
    manifest = importer.import_corpus(data_dir, version=version)
    cache.save_manifest(manifest)
    return _describe_forecast_corpus(version, cache_root=resolved_cache_root)

def _load_forecast_source(version: str) -> DataSource:
    importer = FOReCAstImporter(use_hf_datasets=False)
    cache = OfflineCorpusCache(_resolve_cache_root())
    data_dir = cache.get_corpus_dir(FORECAST_CORPUS_ID, version)
    manifest = cache.load_manifest(FORECAST_CORPUS_ID, version)
    if manifest is None:
        warnings.warn(
            "FOReCAst full cache not found; using the 3-record deterministic preview. "
            "Prepare the corpus cache first to run large-scale validation.",
            UserWarning,
            stacklevel=4,
        )
        manifest = importer.import_corpus(data_dir, version=version)
        cache.save_manifest(manifest)
    elif manifest.metadata.get("import_method") == "fixture":
        warnings.warn(
            "FOReCAst cache currently contains the deterministic preview only. "
            "Refresh the cache with the external dataset before relying on large-scale counts.",
            UserWarning,
            stacklevel=4,
        )
    return importer.load_from_manifest(manifest, data_dir)

def _resolve_cache_root(cache_root: Optional[Path] = None) -> Path:
    if cache_root is not None:
        return cache_root
    return Path(os.environ.get("XRTM_CORPUS_CACHE", Path.home() / ".xrtm" / "corpus-cache"))
