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

r"""Corpus importer infrastructure for external benchmark datasets.

This module provides the base infrastructure for importing external corpus
data without requiring live network access during tests. Importers produce
reproducible manifests that can be cached and versioned.

Design principles:
- Never download data during test execution
- Support offline manifests for deterministic testing
- Enable reproducible corpus snapshots with version pinning
- Provide clear separation between import-time and load-time

Example:
    >>> from xrtm.data.corpora.importers import CorpusImporter
    >>> importer = MyCorpusImporter()
    >>> manifest = importer.import_corpus(output_dir="/path/to/cache")
    >>> # Later, in tests or production:
    >>> source = importer.load_from_manifest(manifest)
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from xrtm.data.core import DataSource


@dataclass
class ImportManifest:
    """Manifest for an imported corpus with provenance and integrity metadata."""

    corpus_id: str
    version: str
    imported_at: datetime
    source_url: Optional[str] = None
    source_checksum: Optional[str] = None
    record_count: int = 0
    split_info: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to a JSON-serializable dict."""
        return {
            "corpus_id": self.corpus_id,
            "version": self.version,
            "imported_at": self.imported_at.isoformat(),
            "source_url": self.source_url,
            "source_checksum": self.source_checksum,
            "record_count": self.record_count,
            "split_info": dict(self.split_info),
            "metadata": dict(self.metadata),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def write(self, path: Path) -> None:
        """Write manifest to a JSON file."""
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImportManifest:
        """Load manifest from a dict."""
        return cls(
            corpus_id=data["corpus_id"],
            version=data["version"],
            imported_at=datetime.fromisoformat(data["imported_at"]),
            source_url=data.get("source_url"),
            source_checksum=data.get("source_checksum"),
            record_count=data.get("record_count", 0),
            split_info=data.get("split_info", {}),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def load(cls, path: Path) -> ImportManifest:
        """Load manifest from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


class CorpusImporter(abc.ABC):
    """Base class for corpus importers."""

    @property
    @abc.abstractmethod
    def corpus_id(self) -> str:
        """Unique identifier for the corpus."""
        pass

    @abc.abstractmethod
    def import_corpus(
        self,
        output_dir: Path,
        version: Optional[str] = None,
    ) -> ImportManifest:
        """Import the corpus and return a manifest.

        This method may perform network downloads and should NOT be called
        during test execution. It produces a manifest that can be cached and
        used for offline loading.

        Args:
            output_dir: Directory to store imported data and manifest
            version: Optional version specifier for the corpus

        Returns:
            ImportManifest with metadata and integrity information
        """
        pass

    @abc.abstractmethod
    def load_from_manifest(
        self,
        manifest: ImportManifest,
        data_dir: Path,
    ) -> DataSource:
        """Load a DataSource from a previously imported manifest.

        This method must work offline using only the manifest and cached data.

        Args:
            manifest: Previously generated import manifest
            data_dir: Directory containing the imported corpus data

        Returns:
            DataSource instance for the corpus
        """
        pass

    def compute_checksum(self, data: bytes) -> str:
        """Compute SHA256 checksum for integrity verification."""
        return hashlib.sha256(data).hexdigest()

    def verify_checksum(self, data: bytes, expected: str) -> bool:
        """Verify data integrity against expected checksum."""
        return self.compute_checksum(data) == expected


class OfflineCorpusCache:
    """Manage cached corpus data for offline deterministic testing."""

    def __init__(self, cache_root: Path):
        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def get_corpus_dir(self, corpus_id: str, version: str) -> Path:
        """Get the cache directory for a specific corpus version."""
        corpus_dir = self.cache_root / corpus_id / version
        corpus_dir.mkdir(parents=True, exist_ok=True)
        return corpus_dir

    def get_manifest_path(self, corpus_id: str, version: str) -> Path:
        """Get the manifest file path for a corpus version."""
        return self.get_corpus_dir(corpus_id, version) / "manifest.json"

    def load_manifest(self, corpus_id: str, version: str) -> Optional[ImportManifest]:
        """Load a cached manifest if it exists."""
        manifest_path = self.get_manifest_path(corpus_id, version)
        if not manifest_path.exists():
            return None
        return ImportManifest.load(manifest_path)

    def save_manifest(self, manifest: ImportManifest) -> None:
        """Save a manifest to the cache."""
        manifest_path = self.get_manifest_path(manifest.corpus_id, manifest.version)
        manifest.write(manifest_path)

    def is_cached(self, corpus_id: str, version: str) -> bool:
        """Check if a corpus version is cached."""
        return self.get_manifest_path(corpus_id, version).exists()


class SimpleFixtureSource(DataSource):
    """Simple in-memory DataSource for test fixtures."""

    def __init__(self, records: List[Dict[str, Any]]):
        from xrtm.data.corpora.real_binary import RealBinaryQuestionRecord

        self._records = [RealBinaryQuestionRecord.model_validate(r) for r in records]
        self._questions = [r.to_forecast_question() for r in self._records]
        self._questions_by_id = {q.id: q for q in self._questions}

    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[Any]:
        """Fetch questions with optional filtering."""
        questions = list(self._questions)
        if query:
            query_lower = query.lower()
            questions = [
                q for q in questions
                if query_lower in q.title.lower() or query_lower in q.description.lower()
            ]
        if snapshot_time:
            questions = [
                q for q in questions
                if q.metadata.snapshot_time and q.metadata.snapshot_time <= snapshot_time
            ]
        return questions[:limit]

    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[Any]:
        """Get a question by ID."""
        question = self._questions_by_id.get(question_id)
        if question and snapshot_time:
            if not question.metadata.snapshot_time or question.metadata.snapshot_time > snapshot_time:
                return None
        return question


class DeterministicFixtureImporter(CorpusImporter):
    """Importer for small deterministic fixtures embedded in code.

    This is a reference implementation showing how to wrap an embedded
    corpus in the importer interface. It requires no network access
    and is suitable for CI/test environments.
    """

    def __init__(self, corpus_id: str, records: List[Dict[str, Any]]):
        self._corpus_id = corpus_id
        self._records = records

    @property
    def corpus_id(self) -> str:
        return self._corpus_id

    def import_corpus(
        self,
        output_dir: Path,
        version: Optional[str] = None,
    ) -> ImportManifest:
        """Create a manifest for the embedded fixture."""
        version = version or "1.0"
        manifest = ImportManifest(
            corpus_id=self.corpus_id,
            version=version,
            imported_at=datetime.now(),
            record_count=len(self._records),
            metadata={"embedded": True, "deterministic": True},
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        data_path = output_dir / f"{self.corpus_id}-{version}.json"
        data_path.write_text(
            json.dumps(self._records, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        manifest_path = output_dir / "manifest.json"
        manifest.write(manifest_path)

        return manifest

    def load_from_manifest(
        self,
        manifest: ImportManifest,
        data_dir: Path,
    ) -> DataSource:
        """Load the fixture from manifest."""
        data_path = data_dir / f"{self.corpus_id}-{manifest.version}.json"
        if data_path.exists():
            records = json.loads(data_path.read_text(encoding="utf-8"))
            return SimpleFixtureSource(records)
        return SimpleFixtureSource(self._records)


__all__ = [
    "ImportManifest",
    "CorpusImporter",
    "OfflineCorpusCache",
    "DeterministicFixtureImporter",
]
