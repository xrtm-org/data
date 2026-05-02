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

r"""Corpus registry and metadata system for XRTM benchmark corpora.

This module provides the infrastructure for registering, discovering, and
managing benchmark corpora in a structured way. It supports both embedded
corpora (like xrtm-real-binary-v1) and external corpora (like ForecastBench).

See data/docs/benchmark-corpus-policy.md for source classification and
licensing requirements.

Example:
    >>> from xrtm.data.corpora.registry import CorpusRegistry, get_corpus
    >>> registry = CorpusRegistry.get_instance()
    >>> corpus = get_corpus("xrtm-real-binary-v1")
    >>> metadata = registry.get_metadata("xrtm-real-binary-v1")
    >>> print(metadata.tier, metadata.license_type)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from xrtm.data.core import DataSource


class CorpusTier(str, enum.Enum):
    """Corpus tier classification per benchmark-corpus-policy.md."""

    TIER_1 = "tier-1"
    TIER_2 = "tier-2"
    TIER_3 = "tier-3"


class LicenseType(str, enum.Enum):
    """Common license types for corpus classification."""

    APACHE_2_0 = "apache-2.0"
    MIT = "mit"
    CC_BY_4_0 = "cc-by-4.0"
    REDISTRIBUTABLE = "redistributable"
    RESEARCH_ONLY = "research-only"
    TOS_DEPENDENT = "tos-dependent"
    PENDING_REVIEW = "pending-review"


class CorpusSplit(str, enum.Enum):
    """Standard corpus splits for train/eval/test partitions."""

    FULL = "full"
    TRAIN = "train"
    EVAL = "eval"
    HELD_OUT = "held-out"
    DEV = "dev"


@dataclass(frozen=True)
class CorpusMetadata:
    """Metadata descriptor for a registered corpus."""

    corpus_id: str
    name: str
    tier: CorpusTier
    license_type: LicenseType
    description: str
    version: str
    release_gate_approved: bool = False
    bundled: bool = False
    size_estimate: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    provenance_url: Optional[str] = None
    license_url: Optional[str] = None
    citation: Optional[str] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now())
    extra: Dict[str, Any] = field(default_factory=dict)

    def is_release_gate_approved(self) -> bool:
        """Check if this corpus is approved for release-gate benchmarks."""
        return self.release_gate_approved and self.tier == CorpusTier.TIER_1

    def requires_warning(self) -> bool:
        """Check if usage of this corpus should emit a warning."""
        return self.tier in (CorpusTier.TIER_2, CorpusTier.TIER_3)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to a JSON-serializable dict."""
        return {
            "corpus_id": self.corpus_id,
            "name": self.name,
            "tier": self.tier.value,
            "license_type": self.license_type.value,
            "description": self.description,
            "version": self.version,
            "release_gate_approved": self.release_gate_approved,
            "bundled": self.bundled,
            "size_estimate": self.size_estimate,
            "tags": list(self.tags),
            "provenance_url": self.provenance_url,
            "license_url": self.license_url,
            "citation": self.citation,
            "extra": dict(self.extra),
        }


@dataclass
class CorpusManifest:
    """Manifest for a corpus with optional split support."""

    corpus_id: str
    metadata: CorpusMetadata
    loader_fn: Callable[[], DataSource]
    available_splits: List[CorpusSplit] = field(default_factory=lambda: [CorpusSplit.FULL])
    default_split: CorpusSplit = CorpusSplit.FULL
    local_path: Optional[Path] = None
    importer_module: Optional[str] = None

    def load_source(self, split: Optional[CorpusSplit] = None) -> DataSource:
        """Load the corpus DataSource for the given split."""
        if split is None:
            split = self.default_split
        if split not in self.available_splits:
            raise ValueError(f"split {split} not available for corpus {self.corpus_id}")
        if self.metadata.requires_warning():
            import warnings
            warnings.warn(
                f"Corpus {self.corpus_id} is {self.metadata.tier.value} and not approved for release gates. "
                f"Use for {self.metadata.license_type.value} purposes only.",
                UserWarning,
                stacklevel=2,
            )
        return self.loader_fn()


@dataclass(frozen=True)
class CorpusAvailability:
    """Availability state for a registered corpus."""

    corpus_id: str
    version: str
    source_mode: str
    bundled: bool
    already_cached: bool
    record_count: Optional[int] = None
    import_method: Optional[str] = None
    cache_root: Optional[Path] = None
    data_dir: Optional[Path] = None
    manifest_path: Optional[Path] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert availability info to a JSON-serializable dict."""
        return {
            "corpus_id": self.corpus_id,
            "version": self.version,
            "source_mode": self.source_mode,
            "bundled": self.bundled,
            "already_cached": self.already_cached,
            "record_count": self.record_count,
            "import_method": self.import_method,
            "cache_root": str(self.cache_root) if self.cache_root is not None else None,
            "data_dir": str(self.data_dir) if self.data_dir is not None else None,
            "manifest_path": str(self.manifest_path) if self.manifest_path is not None else None,
        }


class CorpusRegistry:
    """Global registry for XRTM benchmark corpora."""

    _instance: Optional[CorpusRegistry] = None

    def __init__(self) -> None:
        self._manifests: Dict[str, CorpusManifest] = {}
        self._metadata_cache: Dict[str, CorpusMetadata] = {}

    @classmethod
    def get_instance(cls) -> CorpusRegistry:
        """Get the singleton corpus registry instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_builtin_corpora()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def register(self, manifest: CorpusManifest) -> None:
        """Register a corpus manifest in the registry."""
        if manifest.corpus_id in self._manifests:
            raise ValueError(f"corpus {manifest.corpus_id} is already registered")
        self._manifests[manifest.corpus_id] = manifest
        self._metadata_cache[manifest.corpus_id] = manifest.metadata

    def get_manifest(self, corpus_id: str) -> CorpusManifest:
        """Get the manifest for a registered corpus."""
        if corpus_id not in self._manifests:
            raise KeyError(f"corpus {corpus_id} is not registered")
        return self._manifests[corpus_id]

    def get_metadata(self, corpus_id: str) -> CorpusMetadata:
        """Get metadata for a registered corpus."""
        if corpus_id not in self._metadata_cache:
            raise KeyError(f"corpus {corpus_id} is not registered")
        return self._metadata_cache[corpus_id]

    def list_corpora(
        self,
        tier: Optional[CorpusTier] = None,
        release_gate_only: bool = False,
    ) -> List[CorpusMetadata]:
        """List all registered corpora, optionally filtered by tier or release-gate status."""
        results = list(self._metadata_cache.values())
        if tier is not None:
            results = [m for m in results if m.tier == tier]
        if release_gate_only:
            results = [m for m in results if m.is_release_gate_approved()]
        return sorted(results, key=lambda m: (m.tier.value, m.corpus_id))

    def load_corpus(
        self,
        corpus_id: str,
        split: Optional[CorpusSplit] = None,
    ) -> DataSource:
        """Load a corpus DataSource by ID and optional split."""
        manifest = self.get_manifest(corpus_id)
        return manifest.load_source(split=split)

    def describe_corpus(
        self,
        corpus_id: str,
        *,
        cache_root: Optional[Path] = None,
    ) -> CorpusAvailability:
        """Describe whether a corpus is bundled, cached, or using a preview fixture."""
        metadata = self.get_metadata(corpus_id)
        if metadata.bundled:
            return CorpusAvailability(
                corpus_id=metadata.corpus_id,
                version=metadata.version,
                source_mode="bundled",
                bundled=True,
                already_cached=True,
                record_count=metadata.size_estimate,
            )

        if corpus_id == "forecast-v1":
            from xrtm.data.corpora.importers import OfflineCorpusCache

            resolved_cache_root = _resolve_cache_root(cache_root)
            cache = OfflineCorpusCache(resolved_cache_root)
            manifest = cache.load_manifest(corpus_id, metadata.version)
            data_dir = cache.get_corpus_dir(corpus_id, metadata.version)
            manifest_path = cache.get_manifest_path(corpus_id, metadata.version)
            import_method = manifest.metadata.get("import_method") if manifest is not None else None
            source_mode = "preview" if import_method in {None, "fixture"} else "external-cache"

            return CorpusAvailability(
                corpus_id=metadata.corpus_id,
                version=metadata.version,
                source_mode=source_mode,
                bundled=False,
                already_cached=manifest is not None,
                record_count=manifest.record_count if manifest is not None else None,
                import_method=import_method,
                cache_root=resolved_cache_root,
                data_dir=data_dir,
                manifest_path=manifest_path,
            )

        raise ValueError(f"corpus {corpus_id} does not expose cacheable availability metadata")

    def prepare_corpus(
        self,
        corpus_id: str,
        *,
        cache_root: Optional[Path] = None,
        refresh: bool = False,
        use_hf_datasets: bool = True,
    ) -> CorpusAvailability:
        """Prepare an external corpus cache for offline validation."""
        metadata = self.get_metadata(corpus_id)
        if metadata.bundled:
            return self.describe_corpus(corpus_id, cache_root=cache_root)

        if corpus_id != "forecast-v1":
            raise ValueError(f"corpus {corpus_id} does not provide a product cache workflow")

        from xrtm.data.corpora.forecast_importer import FOReCAstImporter
        from xrtm.data.corpora.importers import OfflineCorpusCache

        resolved_cache_root = _resolve_cache_root(cache_root)
        cache = OfflineCorpusCache(resolved_cache_root)
        if cache.is_cached(corpus_id, metadata.version) and not refresh:
            return self.describe_corpus(corpus_id, cache_root=resolved_cache_root)

        importer = FOReCAstImporter(use_hf_datasets=use_hf_datasets)
        data_dir = cache.get_corpus_dir(corpus_id, metadata.version)
        manifest = importer.import_corpus(data_dir, version=metadata.version)
        cache.save_manifest(manifest)
        return self.describe_corpus(corpus_id, cache_root=resolved_cache_root)

    def _register_builtin_corpora(self) -> None:
        """Register built-in embedded corpora."""
        from xrtm.data.corpora.real_binary import (
            REAL_BINARY_CORPUS_ID,
            RealBinaryCorpusSource,
        )

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

        real_binary_manifest = CorpusManifest(
            corpus_id=REAL_BINARY_CORPUS_ID,
            metadata=real_binary_metadata,
            loader_fn=lambda: RealBinaryCorpusSource(),
            available_splits=[CorpusSplit.FULL],
            default_split=CorpusSplit.FULL,
        )

        self.register(real_binary_manifest)

        self._register_forecast_corpus()

    def _register_forecast_corpus(self) -> None:
        """Register FOReCAst external corpus as Tier 2 (evaluation-only).

        FOReCAst is NOT approved for release gates per benchmark-corpus-policy.md.
        This registration enables evaluation workflows while preserving the
        Tier 2 classification until explicit approval is granted.
        """
        import warnings

        from xrtm.data.corpora.forecast_importer import FORECAST_CORPUS_ID, FOReCAstImporter
        from xrtm.data.corpora.importers import OfflineCorpusCache

        cache_root = _resolve_cache_root()
        cache = OfflineCorpusCache(cache_root)

        forecast_metadata = CorpusMetadata(
            corpus_id=FORECAST_CORPUS_ID,
            name="FOReCAst (Future Outcome Reasoning and Confidence Assessment)",
            tier=CorpusTier.TIER_2,
            license_type=LicenseType.MIT,
            description="Academic benchmark dataset for probabilistic forecasting from NeurIPS 2025. "
                       "1,390 resolved questions from Metaculus. Evaluation-only until Tier 1 approval.",
            version="1.0",
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

        def load_forecast_source() -> DataSource:
            importer = FOReCAstImporter(use_hf_datasets=False)
            data_dir = cache.get_corpus_dir(FORECAST_CORPUS_ID, "1.0")
            manifest = cache.load_manifest(FORECAST_CORPUS_ID, "1.0")
            if manifest is None:
                warnings.warn(
                    "FOReCAst full cache not found; using the 3-record deterministic preview. "
                    "Prepare the corpus cache first to run large-scale validation.",
                    UserWarning,
                    stacklevel=3,
                )
                manifest = importer.import_corpus(data_dir, version="1.0")
                cache.save_manifest(manifest)
            elif manifest.metadata.get("import_method") == "fixture":
                warnings.warn(
                    "FOReCAst cache currently contains the deterministic preview only. "
                    "Refresh the cache with the external dataset before relying on large-scale counts.",
                    UserWarning,
                    stacklevel=3,
                )
            return importer.load_from_manifest(manifest, data_dir)

        forecast_manifest = CorpusManifest(
            corpus_id=FORECAST_CORPUS_ID,
            metadata=forecast_metadata,
            loader_fn=load_forecast_source,
            available_splits=[CorpusSplit.FULL, CorpusSplit.TRAIN, CorpusSplit.EVAL],
            default_split=CorpusSplit.FULL,
            importer_module="xrtm.data.corpora.forecast_importer",
        )

        self.register(forecast_manifest)


def get_corpus(corpus_id: str, split: Optional[CorpusSplit] = None) -> DataSource:
    """Convenience function to load a corpus from the global registry."""
    registry = CorpusRegistry.get_instance()
    return registry.load_corpus(corpus_id, split=split)


def get_corpus_metadata(corpus_id: str) -> CorpusMetadata:
    """Convenience function to get corpus metadata from the global registry."""
    registry = CorpusRegistry.get_instance()
    return registry.get_metadata(corpus_id)


def list_available_corpora(
    tier: Optional[CorpusTier] = None,
    release_gate_only: bool = False,
) -> List[CorpusMetadata]:
    """Convenience function to list available corpora."""
    registry = CorpusRegistry.get_instance()
    return registry.list_corpora(tier=tier, release_gate_only=release_gate_only)


def describe_corpus(
    corpus_id: str,
    *,
    cache_root: Optional[Path] = None,
) -> CorpusAvailability:
    """Convenience function to describe corpus availability."""
    registry = CorpusRegistry.get_instance()
    return registry.describe_corpus(corpus_id, cache_root=cache_root)


def prepare_corpus(
    corpus_id: str,
    *,
    cache_root: Optional[Path] = None,
    refresh: bool = False,
    use_hf_datasets: bool = True,
) -> CorpusAvailability:
    """Convenience function to prepare a registered external corpus."""
    registry = CorpusRegistry.get_instance()
    return registry.prepare_corpus(
        corpus_id,
        cache_root=cache_root,
        refresh=refresh,
        use_hf_datasets=use_hf_datasets,
    )


def _resolve_cache_root(cache_root: Optional[Path] = None) -> Path:
    """Resolve the cache root for external corpora."""
    import os

    if cache_root is not None:
        return cache_root
    return Path(os.environ.get("XRTM_CORPUS_CACHE", Path.home() / ".xrtm" / "corpus-cache"))


__all__ = [
    "CorpusAvailability",
    "CorpusTier",
    "LicenseType",
    "CorpusSplit",
    "CorpusMetadata",
    "CorpusManifest",
    "CorpusRegistry",
    "describe_corpus",
    "get_corpus",
    "get_corpus_metadata",
    "list_available_corpora",
    "prepare_corpus",
]
