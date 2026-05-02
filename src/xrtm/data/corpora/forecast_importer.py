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

r"""FOReCAst corpus importer for XRTM.

FOReCAst (Future Outcome Reasoning and Confidence Assessment) is an academic
benchmark dataset for probabilistic forecasting, derived from resolved Metaculus
questions. Released at NeurIPS 2025 Datasets and Benchmarks Track.

Dataset: MoyYuan/FOReCAst on Hugging Face
License: MIT (evaluation-only until explicit Tier 1 promotion approval)
Size: 1,390 resolved questions with train/dev/test splits

This importer provides external access to FOReCAst without bundling the raw
dataset in XRTM distributions. Data is cached locally for offline testing.

Classification per benchmark-corpus-policy.md:
- Tier: 2 (evaluation-only)
- License: MIT (pending non-commercial clause clarification)
- Release-gate approved: NO (requires explicit approval)
- Bundled: NO (external dependency only)

Example:
    >>> from xrtm.data.corpora.forecast_importer import FOReCAstImporter
    >>> importer = FOReCAstImporter()
    >>> manifest = importer.import_corpus(output_dir="./cache")
    >>> source = importer.load_from_manifest(manifest, data_dir="./cache")
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from xrtm.data.core import DataSource
from xrtm.data.core.schemas import ForecastQuestion, MetadataBase
from xrtm.data.corpora.importers import (
    CorpusImporter,
    ImportManifest,
)

FORECAST_CORPUS_ID = "forecast-v1"
FORECAST_HF_DATASET = "MoyYuan/FOReCAst"


class FOReCAstQuestionRecord(BaseModel):
    """Validated FOReCAst-backed question record for mixed forecasting types."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable corpus-local question identifier")
    title: str = Field(..., description="Forecast question title")
    content: str = Field(..., description="Question background available at snapshot time")
    resolution_criteria: str = Field(..., description="Rules or observed outcome text")
    snapshot_time: datetime = Field(..., description="Zero-leakage history cutoff for this question")
    source: str = Field(..., description="Stable source category for the FOReCAst record")
    tags: list[str] = Field(default_factory=list, description="Question tags and source taxonomy")
    source_metadata: dict[str, Any] = Field(default_factory=dict, description="Original FOReCAst fields and provenance")
    subject_type: str = Field("binary", description="Question type such as binary, numeric, or timeframe")
    resolved_outcome: Optional[bool] = Field(None, description="Resolved YES/NO outcome when the source is boolean")
    resolution_time: Optional[datetime] = Field(None, description="Timestamp when the outcome was resolved")
    resolution_notes: Optional[str] = Field(None, description="Human-readable resolution evidence summary")

    @model_validator(mode="after")
    def _validate_resolution_pairing(self) -> "FOReCAstQuestionRecord":
        if self.resolved_outcome is not None and self.resolution_time is None:
            raise ValueError("resolved boolean FOReCAst records must include resolution_time")
        if self.resolution_time is not None and self.resolution_time < self.snapshot_time:
            raise ValueError("resolution_time must not precede snapshot_time")
        return self

    def to_forecast_question(self) -> ForecastQuestion:
        """Convert the imported record to the canonical XRTM ForecastQuestion schema."""
        raw_data = self.model_dump(mode="json")
        return ForecastQuestion(
            id=self.id,
            title=self.title,
            description=self.content,
            resolution_criteria=self.resolution_criteria,
            metadata=MetadataBase(
                id=f"{self.id}:metadata",
                created_at=self.snapshot_time,
                snapshot_time=self.snapshot_time,
                tags=list(self.tags),
                subject_type=self.subject_type,
                source_version=FORECAST_CORPUS_ID,
                raw_data=raw_data,
                source=self.source,
                source_metadata=dict(self.source_metadata),
                resolved_outcome=self.resolved_outcome,
                resolution_time=self.resolution_time,
                resolution_notes=self.resolution_notes,
            ),
        )


class FOReCAstSource(DataSource):
    """In-memory DataSource for imported FOReCAst question records."""

    def __init__(self, records: List[Dict[str, Any]]):
        self._records = [FOReCAstQuestionRecord.model_validate(record) for record in records]
        self._questions = [record.to_forecast_question() for record in self._records]
        self._questions_by_id = {question.id: question for question in self._questions}

    async def fetch_questions(
        self, query: Optional[str] = None, limit: int = 5, *, snapshot_time: Optional[datetime] = None
    ) -> List[Any]:
        questions = list(self._questions)
        if query:
            query_lower = query.lower()
            questions = [
                question
                for question in questions
                if query_lower in question.title.lower() or query_lower in (question.description or "").lower()
            ]
        if snapshot_time:
            questions = [
                question
                for question in questions
                if question.metadata.snapshot_time and question.metadata.snapshot_time <= snapshot_time
            ]
        return questions[:limit]

    async def get_question_by_id(
        self, question_id: str, *, snapshot_time: Optional[datetime] = None
    ) -> Optional[Any]:
        question = self._questions_by_id.get(question_id)
        if question and snapshot_time:
            if not question.metadata.snapshot_time or question.metadata.snapshot_time > snapshot_time:
                return None
        return question


class FOReCAstImporter(CorpusImporter):
    """Importer for FOReCAst dataset from Hugging Face.

    This importer handles the FOReCAst benchmark corpus, which provides
    1,390 resolved probabilistic forecasting questions. The dataset is
    fetched from Hugging Face and cached locally for offline operation.

    The importer supports:
    - Network-based import with HuggingFace datasets library
    - Offline loading from cached manifests
    - Deterministic test fixtures for CI environments

    Note: FOReCAst is classified as Tier 2 (evaluation-only) per
    benchmark-corpus-policy.md. It should NOT be used for release gates
    or public performance claims without explicit approval.
    """

    def __init__(self, use_hf_datasets: bool = True):
        """Initialize the FOReCAst importer.

        Args:
            use_hf_datasets: If True, use HuggingFace datasets library for import.
                           If False, fall back to deterministic fixtures for testing.
        """
        self._use_hf_datasets = use_hf_datasets

    @property
    def corpus_id(self) -> str:
        return FORECAST_CORPUS_ID

    def import_corpus(
        self,
        output_dir: Path,
        version: Optional[str] = None,
    ) -> ImportManifest:
        """Import FOReCAst corpus from Hugging Face or fixtures.

        This method downloads the FOReCAst dataset (if use_hf_datasets=True)
        and creates a manifest with integrity metadata. The data is cached
        in output_dir for subsequent offline loading.

        Args:
            output_dir: Directory to store imported data and manifest
            version: Version specifier (defaults to "1.0")

        Returns:
            ImportManifest with metadata and integrity information
        """
        version = version or "1.0"
        output_dir.mkdir(parents=True, exist_ok=True)

        if self._use_hf_datasets:
            return self._import_from_huggingface(output_dir, version)
        else:
            return self._import_from_fixture(output_dir, version)

    def _import_from_huggingface(self, output_dir: Path, version: str) -> ImportManifest:
        """Import FOReCAst from HuggingFace datasets library."""
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "HuggingFace datasets library required for FOReCAst import. "
                "Install with: pip install datasets"
            )

        dataset = load_dataset(FORECAST_HF_DATASET)

        all_records = []
        split_info: dict[str, int] = {}

        for split_name in ["train", "validation", "dev", "test"]:
            if split_name not in dataset:
                continue
            split_data = dataset[split_name]
            split_records = self._convert_hf_records(split_data, split_name)
            all_records.extend(split_records)
            canonical_split = self._canonical_split_name(split_name)
            split_info[canonical_split] = split_info.get(canonical_split, 0) + len(split_records)

        data_path = output_dir / f"{FORECAST_CORPUS_ID}-{version}.json"
        data_path.write_text(
            json.dumps(all_records, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        data_bytes = data_path.read_bytes()
        checksum = self.compute_checksum(data_bytes)

        manifest = ImportManifest(
            corpus_id=self.corpus_id,
            version=version,
            imported_at=datetime.now(),
            source_url=f"https://huggingface.co/datasets/{FORECAST_HF_DATASET}",
            source_checksum=checksum,
            record_count=len(all_records),
            split_info=split_info,
            metadata={
                "hf_dataset": FORECAST_HF_DATASET,
                "import_method": "huggingface",
            },
        )

        manifest_path = output_dir / "manifest.json"
        manifest.write(manifest_path)

        return manifest

    def _import_from_fixture(self, output_dir: Path, version: str) -> ImportManifest:
        """Import from a small deterministic fixture for testing."""
        fixture_records = self._get_fixture_records()

        data_path = output_dir / f"{FORECAST_CORPUS_ID}-{version}.json"
        data_path.write_text(
            json.dumps(fixture_records, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        data_bytes = data_path.read_bytes()
        checksum = self.compute_checksum(data_bytes)

        manifest = ImportManifest(
            corpus_id=self.corpus_id,
            version=version,
            imported_at=datetime.now(),
            source_checksum=checksum,
            record_count=len(fixture_records),
            split_info={"train": 2, "eval": 1},
            metadata={
                "import_method": "fixture",
                "deterministic": True,
            },
        )

        manifest_path = output_dir / "manifest.json"
        manifest.write(manifest_path)

        return manifest

    def _convert_hf_records(
        self,
        hf_data: Any,
        split_name: str,
    ) -> List[Dict[str, Any]]:
        """Convert HuggingFace dataset records to XRTM format.

        FOReCAst schema:
        {
          "id": "unique-question-id",
          "question": "Will we confirm evidence for megastructures...",
          "type": "Boolean question | quantity estimation | timeframe prediction",
          "resolution": "yes | no | <numeric> | <date>",
          "resolution_time": "YYYY-MM-DD",
          "created_time": "YYYY-MM-DD",
          "confidence": 0.7133
        }

        XRTM RealBinaryQuestionRecord schema:
        {
          "id": str,
          "title": str,
          "content": str,
          "resolution_criteria": str,
          "snapshot_time": str,  # ISO 8601
          "source": str,
          "tags": List[str],
          "source_metadata": Dict[str, Any]
        }
        """
        records = []

        for idx, item in enumerate(hf_data):
            question_id = item.get("id", f"forecast-{split_name}-{idx}")
            question_text = item.get("question", "")
            question_type = item.get("type", "unknown")
            subject_type = self._subject_type(question_type)
            resolution = item.get("resolution", "")
            resolution_time = item.get("resolution_time", "")
            created_time = item.get("created_time", "")
            confidence = item.get("confidence", None)

            created_time_iso = self._parse_date_to_iso(created_time)
            if created_time_iso is None:
                raise ValueError(f"FOReCAst record {question_id} is missing created_time")
            resolution_time_iso = self._parse_date_to_iso(resolution_time)
            resolved_outcome = self._parse_boolean_resolution(resolution)
            if resolved_outcome is not None and resolution_time_iso is None:
                raise ValueError(f"FOReCAst record {question_id} is missing resolution_time for boolean resolution")

            canonical_split = self._canonical_split_name(split_name)
            tags = ["forecast", canonical_split]
            if "boolean" in question_type.lower():
                tags.append("binary")

            record = {
                "id": question_id,
                "title": question_text[:200] if len(question_text) > 200 else question_text,
                "content": question_text,
                "resolution_criteria": f"Resolution: {resolution}",
                "snapshot_time": created_time_iso,
                "source": "forecast_benchmark",
                "tags": tags,
                "subject_type": subject_type,
                "resolved_outcome": resolved_outcome,
                "resolution_time": resolution_time_iso,
                "resolution_notes": f"FOReCAst resolution value: {resolution}",
                "source_metadata": {
                    "question_type": question_type,
                    "resolution": resolution,
                    "resolution_time": resolution_time_iso,
                    "confidence": confidence,
                    "split": canonical_split,
                    "source_split": split_name,
                },
            }

            records.append(record)

        return records

    def _parse_date_to_iso(self, date_str: str) -> str | None:
        """Parse YYYY-MM-DD to ISO 8601 format."""
        if not date_str:
            return None

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.isoformat() + "Z"
        except (ValueError, TypeError):
            raise ValueError(f"invalid FOReCAst date: {date_str!r}")

    def _parse_boolean_resolution(self, resolution: Any) -> bool | None:
        """Parse yes/no-style resolutions into resolved boolean outcomes."""
        if not isinstance(resolution, str):
            return None
        normalized = resolution.strip().lower()
        if normalized == "yes":
            return True
        if normalized == "no":
            return False
        return None

    def _canonical_split_name(self, split_name: str) -> str:
        """Normalize external split names to XRTM-friendly labels."""
        if split_name in {"validation", "dev"}:
            return "eval"
        return split_name

    def _subject_type(self, question_type: Any) -> str:
        """Map FOReCAst question types into XRTM subject types."""
        normalized = str(question_type).strip().lower()
        if "boolean" in normalized:
            return "binary"
        if "quantity" in normalized or "numeric" in normalized:
            return "numeric"
        if "timeframe" in normalized or "date" in normalized or "time" in normalized:
            return "timeframe"
        return "forecast"

    def _get_fixture_records(self) -> List[Dict[str, Any]]:
        """Return deterministic fixture records for testing."""
        return [
            {
                "id": "forecast-fixture-1",
                "title": "Will renewable energy exceed 50% of global electricity by 2030?",
                "content": "Will renewable energy sources (solar, wind, hydro, geothermal) exceed 50% of global electricity generation by December 31, 2030?",
                "resolution_criteria": "Resolution: no",
                "snapshot_time": "2023-01-15T00:00:00Z",
                "source": "forecast_benchmark",
                "tags": ["forecast", "train", "binary"],
                "subject_type": "binary",
                "resolved_outcome": False,
                "resolution_time": "2030-12-31T00:00:00Z",
                "resolution_notes": "FOReCAst resolution value: no",
                "source_metadata": {
                    "question_type": "Boolean question",
                    "resolution": "no",
                    "resolution_time": "2030-12-31T00:00:00Z",
                    "confidence": 0.35,
                    "split": "train",
                },
            },
            {
                "id": "forecast-fixture-2",
                "title": "Will GPT-5 be released before January 2025?",
                "content": "Will OpenAI release a model named GPT-5 before January 1, 2025?",
                "resolution_criteria": "Resolution: yes",
                "snapshot_time": "2023-06-01T00:00:00Z",
                "source": "forecast_benchmark",
                "tags": ["forecast", "train", "binary"],
                "subject_type": "binary",
                "resolved_outcome": True,
                "resolution_time": "2024-11-15T00:00:00Z",
                "resolution_notes": "FOReCAst resolution value: yes",
                "source_metadata": {
                    "question_type": "Boolean question",
                    "resolution": "yes",
                    "resolution_time": "2024-11-15T00:00:00Z",
                    "confidence": 0.68,
                    "split": "train",
                },
            },
            {
                "id": "forecast-fixture-3",
                "title": "Will global CO2 levels exceed 450 ppm by 2028?",
                "content": "Will atmospheric CO2 concentration exceed 450 parts per million by December 31, 2028?",
                "resolution_criteria": "Resolution: yes",
                "snapshot_time": "2023-03-20T00:00:00Z",
                "source": "forecast_benchmark",
                "tags": ["forecast", "eval", "binary"],
                "subject_type": "binary",
                "resolved_outcome": True,
                "resolution_time": "2028-08-15T00:00:00Z",
                "resolution_notes": "FOReCAst resolution value: yes",
                "source_metadata": {
                    "question_type": "Boolean question",
                    "resolution": "yes",
                    "resolution_time": "2028-08-15T00:00:00Z",
                    "confidence": 0.82,
                    "split": "eval",
                    "source_split": "validation",
                },
            },
        ]

    def load_from_manifest(
        self,
        manifest: ImportManifest,
        data_dir: Path,
    ) -> DataSource:
        """Load FOReCAst DataSource from a cached manifest.

        This method works offline using only the manifest and cached data.

        Args:
            manifest: Previously generated import manifest
            data_dir: Directory containing the imported corpus data

        Returns:
            DataSource instance for the FOReCAst corpus
        """
        data_path = data_dir / f"{FORECAST_CORPUS_ID}-{manifest.version}.json"

        if not data_path.exists():
            if not self._use_hf_datasets:
                records = self._get_fixture_records()
            else:
                raise FileNotFoundError(
                    f"FOReCAst data file not found: {data_path}. "
                    f"Run import_corpus() first to download the dataset."
                )
        else:
            if manifest.source_checksum is not None:
                data_bytes = data_path.read_bytes()
                if not self.verify_checksum(data_bytes, manifest.source_checksum):
                    raise ValueError(f"checksum mismatch for FOReCAst data file: {data_path}")
            records = json.loads(data_path.read_text(encoding="utf-8"))

        return FOReCAstSource(records)


__all__ = [
    "FOReCAstImporter",
    "FOReCAstQuestionRecord",
    "FOReCAstSource",
    "FORECAST_CORPUS_ID",
    "FORECAST_HF_DATASET",
]
