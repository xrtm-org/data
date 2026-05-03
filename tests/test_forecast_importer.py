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

"""Tests for FOReCAst corpus importer."""

import json
from pathlib import Path

import pytest

from xrtm.data.corpora import (
    FORECAST_CORPUS_ID,
    CorpusTier,
    FOReCAstImporter,
    LicenseType,
    get_corpus_metadata,
)
from xrtm.data.corpora.importers import OfflineCorpusCache


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary output directory."""
    return tmp_path / "forecast-import"


@pytest.fixture
def forecast_importer():
    """Provide a FOReCAst importer using fixtures."""
    return FOReCAstImporter(use_hf_datasets=False)


def test_forecast_importer_corpus_id(forecast_importer):
    """Test that FOReCAst importer has correct corpus ID."""
    assert forecast_importer.corpus_id == FORECAST_CORPUS_ID


def test_forecast_importer_import_corpus_fixture(forecast_importer, temp_output_dir):
    """Test importing FOReCAst corpus from fixture."""
    manifest = forecast_importer.import_corpus(temp_output_dir, version="1.0")

    assert manifest.corpus_id == FORECAST_CORPUS_ID
    assert manifest.version == "1.0"
    assert manifest.record_count == 3
    assert "train" in manifest.split_info
    assert manifest.metadata["import_method"] == "fixture"
    assert manifest.metadata["deterministic"] is True

    manifest_path = temp_output_dir / "manifest.json"
    assert manifest_path.exists()

    data_path = temp_output_dir / f"{FORECAST_CORPUS_ID}-1.0.json"
    assert data_path.exists()

    records = json.loads(data_path.read_text(encoding="utf-8"))
    assert len(records) == 3
    assert records[0]["id"] == "forecast-fixture-1"
    assert records[0]["source"] == "forecast_benchmark"
    assert "forecast" in records[0]["tags"]
    assert records[0]["resolved_outcome"] is False
    assert records[1]["resolved_outcome"] is True


def test_forecast_importer_manifest_integrity(forecast_importer, temp_output_dir):
    """Test that import manifest includes integrity checksums."""
    manifest = forecast_importer.import_corpus(temp_output_dir, version="1.0")

    assert manifest.source_checksum is not None
    assert len(manifest.source_checksum) == 64

    data_path = temp_output_dir / f"{FORECAST_CORPUS_ID}-1.0.json"
    data_bytes = data_path.read_bytes()
    expected_checksum = forecast_importer.compute_checksum(data_bytes)
    assert manifest.source_checksum == expected_checksum


@pytest.mark.asyncio
async def test_forecast_importer_load_from_manifest(forecast_importer, temp_output_dir):
    """Test loading FOReCAst corpus from manifest."""
    manifest = forecast_importer.import_corpus(temp_output_dir, version="1.0")

    source = forecast_importer.load_from_manifest(manifest, temp_output_dir)

    questions = await source.fetch_questions(limit=10)
    assert len(questions) == 3
    assert questions[0].id == "forecast-fixture-1"
    assert "renewable energy" in questions[0].title.lower()


@pytest.mark.asyncio
async def test_forecast_importer_load_without_cached_data(forecast_importer, temp_output_dir):
    """Test loading FOReCAst corpus when cached data doesn't exist."""
    from datetime import datetime

    from xrtm.data.corpora.importers import ImportManifest

    manifest = ImportManifest(
        corpus_id=FORECAST_CORPUS_ID,
        version="1.0",
        imported_at=datetime.now(),
    )

    source = forecast_importer.load_from_manifest(manifest, temp_output_dir)
    questions = await source.fetch_questions(limit=10)
    assert len(questions) == 3


def test_forecast_importer_fixture_records_schema(forecast_importer):
    """Test that fixture records match XRTM schema."""
    records = forecast_importer._get_fixture_records()

    for record in records:
        assert "id" in record
        assert "title" in record
        assert "content" in record
        assert "resolution_criteria" in record
        assert "snapshot_time" in record
        assert "source" in record
        assert "tags" in record
        assert "source_metadata" in record

        assert record["source"] == "forecast_benchmark"
        assert "forecast" in record["tags"]
        assert "resolved_outcome" in record
        assert "resolution_time" in record
        assert "resolution_notes" in record

        metadata = record["source_metadata"]
        assert "question_type" in metadata
        assert "resolution" in metadata
        assert "resolution_time" in metadata
        assert "confidence" in metadata
        assert "split" in metadata


def test_forecast_importer_date_parsing(forecast_importer):
    """Test date parsing to ISO format."""
    iso_date = forecast_importer._parse_date_to_iso("2023-06-15")
    assert iso_date == "2023-06-15T00:00:00Z"

    empty_date = forecast_importer._parse_date_to_iso("")
    assert empty_date is None

    with pytest.raises(ValueError, match="invalid FOReCAst date"):
        forecast_importer._parse_date_to_iso("invalid")


def test_forecast_importer_boolean_resolution_parsing(forecast_importer):
    """Test yes/no resolution parsing for resolved binary outcomes."""
    assert forecast_importer._parse_boolean_resolution("yes") is True
    assert forecast_importer._parse_boolean_resolution("no") is False
    assert forecast_importer._parse_boolean_resolution("  YES ") is True
    assert forecast_importer._parse_boolean_resolution("2028-01-01") is None


def test_forecast_corpus_registered_as_tier2():
    """Test that FOReCAst is registered as Tier 2 in the registry."""
    metadata = get_corpus_metadata(FORECAST_CORPUS_ID)

    assert metadata.corpus_id == FORECAST_CORPUS_ID
    assert metadata.tier == CorpusTier.TIER_2
    assert metadata.license_type == LicenseType.MIT
    assert metadata.release_gate_approved is False
    assert metadata.bundled is False
    assert "evaluation-only" in metadata.description.lower()
    assert "forecast" in metadata.tags


def test_forecast_corpus_metadata_warnings():
    """Test that FOReCAst metadata requires warnings."""
    metadata = get_corpus_metadata(FORECAST_CORPUS_ID)

    assert metadata.requires_warning() is True
    assert metadata.is_release_gate_approved() is False


@pytest.mark.asyncio
async def test_forecast_corpus_load_emits_warning(monkeypatch, tmp_path):
    """Test that loading FOReCAst corpus emits a Tier 2 warning."""
    from xrtm.data.corpora import get_corpus

    monkeypatch.setenv("XRTM_CORPUS_CACHE", str(tmp_path / "corpus-cache"))
    with pytest.warns(UserWarning, match="tier-2"):
        source = get_corpus(FORECAST_CORPUS_ID)
        questions = await source.fetch_questions(limit=1)
        assert len(questions) >= 1
        assert questions[0].metadata.resolved_outcome in {True, False}


def test_forecast_importer_offline_cache_integration(forecast_importer, tmp_path):
    """Test integration with OfflineCorpusCache."""
    cache_root = tmp_path / "corpus-cache"
    cache = OfflineCorpusCache(cache_root)

    assert cache.is_cached(FORECAST_CORPUS_ID, "1.0") is False

    corpus_dir = cache.get_corpus_dir(FORECAST_CORPUS_ID, "1.0")
    manifest = forecast_importer.import_corpus(corpus_dir, version="1.0")
    cache.save_manifest(manifest)

    assert cache.is_cached(FORECAST_CORPUS_ID, "1.0") is True

    loaded_manifest = cache.load_manifest(FORECAST_CORPUS_ID, "1.0")
    assert loaded_manifest is not None
    assert loaded_manifest.corpus_id == FORECAST_CORPUS_ID
    assert loaded_manifest.version == "1.0"


@pytest.mark.asyncio
async def test_forecast_corpus_question_fetch(forecast_importer, temp_output_dir):
    """Test fetching questions from FOReCAst corpus."""
    manifest = forecast_importer.import_corpus(temp_output_dir, version="1.0")
    source = forecast_importer.load_from_manifest(manifest, temp_output_dir)

    all_questions = await source.fetch_questions(limit=100)
    assert len(all_questions) == 3
    assert {question.metadata.resolved_outcome for question in all_questions} == {False, True}

    limited_questions = await source.fetch_questions(limit=2)
    assert len(limited_questions) == 2

    query_questions = await source.fetch_questions(query="energy", limit=10)
    assert len(query_questions) >= 1
    assert any("energy" in q.title.lower() for q in query_questions)


@pytest.mark.asyncio
async def test_forecast_corpus_get_question_by_id(forecast_importer, temp_output_dir):
    """Test getting a specific question by ID."""
    manifest = forecast_importer.import_corpus(temp_output_dir, version="1.0")
    source = forecast_importer.load_from_manifest(manifest, temp_output_dir)

    question = await source.get_question_by_id("forecast-fixture-1")
    assert question is not None
    assert question.id == "forecast-fixture-1"
    assert "renewable energy" in question.title.lower()

    nonexistent = await source.get_question_by_id("nonexistent-id")
    assert nonexistent is None


def test_forecast_corpus_provenance_metadata():
    """Test that FOReCAst has proper provenance metadata."""
    metadata = get_corpus_metadata(FORECAST_CORPUS_ID)

    assert metadata.provenance_url is not None
    assert "huggingface.co" in metadata.provenance_url.lower()
    assert metadata.license_url is not None
    assert metadata.citation is not None
    assert "NeurIPS" in metadata.citation or "neurips" in metadata.citation.lower()

    assert "tier_status" in metadata.extra
    assert metadata.extra["tier_status"] == "evaluation-only"


def test_forecast_importer_version_handling(forecast_importer, temp_output_dir):
    """Test version handling in FOReCAst importer."""
    manifest_v1 = forecast_importer.import_corpus(temp_output_dir / "v1", version="1.0")
    assert manifest_v1.version == "1.0"

    manifest_v2 = forecast_importer.import_corpus(temp_output_dir / "v2", version="2.0")
    assert manifest_v2.version == "2.0"

    manifest_default = forecast_importer.import_corpus(temp_output_dir / "default")
    assert manifest_default.version == "1.0"


def test_forecast_importer_detects_checksum_mismatch(forecast_importer, temp_output_dir):
    """Test checksum verification during offline load."""
    manifest = forecast_importer.import_corpus(temp_output_dir, version="1.0")
    data_path = temp_output_dir / f"{FORECAST_CORPUS_ID}-1.0.json"
    data_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum mismatch"):
        forecast_importer.load_from_manifest(manifest, temp_output_dir)


def test_forecast_importer_hf_import_requires_library():
    """Test that HuggingFace import mode requires datasets library."""
    importer = FOReCAstImporter(use_hf_datasets=True)

    import importlib.util

    if importlib.util.find_spec("datasets") is not None:
        pytest.skip("datasets library is installed, cannot test import error")

    with pytest.raises(ImportError, match="HuggingFace datasets library required"):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            importer.import_corpus(Path(tmpdir), version="1.0")
