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

import json
from datetime import datetime

import pytest

from xrtm.data.corpora.importers import (
    DeterministicFixtureImporter,
    ImportManifest,
    OfflineCorpusCache,
)


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    return tmp_path / "corpus-cache"


@pytest.fixture
def sample_records():
    """Provide sample corpus records."""
    return [
        {
            "id": "test-question-1",
            "title": "Will test 1 happen?",
            "content": "Test question 1",
            "resolution_criteria": "Test criteria 1",
            "snapshot_time": "2023-01-01T00:00:00Z",
            "source": "test",
            "tags": ["binary", "test"],
            "source_metadata": {"test": True},
        },
        {
            "id": "test-question-2",
            "title": "Will test 2 happen?",
            "content": "Test question 2",
            "resolution_criteria": "Test criteria 2",
            "snapshot_time": "2023-02-01T00:00:00Z",
            "source": "test",
            "tags": ["binary", "test"],
            "source_metadata": {"test": True},
        },
    ]


def test_import_manifest_to_dict():
    manifest = ImportManifest(
        corpus_id="test-corpus",
        version="1.0",
        imported_at=datetime(2024, 1, 1, 12, 0, 0),
        source_url="https://example.com/corpus",
        source_checksum="abc123",
        record_count=100,
        split_info={"train": 70, "eval": 30},
        metadata={"key": "value"},
    )
    data = manifest.to_dict()
    assert data["corpus_id"] == "test-corpus"
    assert data["version"] == "1.0"
    assert data["source_url"] == "https://example.com/corpus"
    assert data["record_count"] == 100
    assert data["split_info"] == {"train": 70, "eval": 30}


def test_import_manifest_from_dict():
    data = {
        "corpus_id": "test-corpus",
        "version": "1.0",
        "imported_at": "2024-01-01T12:00:00",
        "source_url": "https://example.com/corpus",
        "source_checksum": "abc123",
        "record_count": 100,
        "split_info": {"train": 70, "eval": 30},
        "metadata": {"key": "value"},
    }
    manifest = ImportManifest.from_dict(data)
    assert manifest.corpus_id == "test-corpus"
    assert manifest.version == "1.0"
    assert manifest.source_url == "https://example.com/corpus"
    assert manifest.record_count == 100


def test_import_manifest_write_and_load(temp_cache_dir):
    temp_cache_dir.mkdir(parents=True)
    manifest_path = temp_cache_dir / "test-manifest.json"

    original = ImportManifest(
        corpus_id="test-corpus",
        version="1.0",
        imported_at=datetime(2024, 1, 1, 12, 0, 0),
        record_count=50,
    )
    original.write(manifest_path)

    assert manifest_path.exists()
    loaded = ImportManifest.load(manifest_path)
    assert loaded.corpus_id == original.corpus_id
    assert loaded.version == original.version
    assert loaded.record_count == original.record_count


def test_import_manifest_to_json():
    manifest = ImportManifest(
        corpus_id="test-corpus",
        version="1.0",
        imported_at=datetime(2024, 1, 1, 12, 0, 0),
        record_count=100,
    )
    json_str = manifest.to_json()
    parsed = json.loads(json_str)
    assert parsed["corpus_id"] == "test-corpus"
    assert parsed["record_count"] == 100


def test_offline_corpus_cache_initialization(temp_cache_dir):
    cache = OfflineCorpusCache(temp_cache_dir)
    assert cache.cache_root == temp_cache_dir
    assert temp_cache_dir.exists()


def test_offline_corpus_cache_get_corpus_dir(temp_cache_dir):
    cache = OfflineCorpusCache(temp_cache_dir)
    corpus_dir = cache.get_corpus_dir("test-corpus", "1.0")
    assert corpus_dir == temp_cache_dir / "test-corpus" / "1.0"
    assert corpus_dir.exists()


def test_offline_corpus_cache_get_manifest_path(temp_cache_dir):
    cache = OfflineCorpusCache(temp_cache_dir)
    manifest_path = cache.get_manifest_path("test-corpus", "1.0")
    expected = temp_cache_dir / "test-corpus" / "1.0" / "manifest.json"
    assert manifest_path == expected


def test_offline_corpus_cache_is_cached(temp_cache_dir):
    cache = OfflineCorpusCache(temp_cache_dir)
    assert cache.is_cached("test-corpus", "1.0") is False

    manifest = ImportManifest(
        corpus_id="test-corpus",
        version="1.0",
        imported_at=datetime.now(),
    )
    cache.save_manifest(manifest)
    assert cache.is_cached("test-corpus", "1.0") is True


def test_offline_corpus_cache_save_and_load_manifest(temp_cache_dir):
    cache = OfflineCorpusCache(temp_cache_dir)
    manifest = ImportManifest(
        corpus_id="test-corpus",
        version="1.0",
        imported_at=datetime(2024, 1, 1, 12, 0, 0),
        record_count=100,
    )
    cache.save_manifest(manifest)

    loaded = cache.load_manifest("test-corpus", "1.0")
    assert loaded is not None
    assert loaded.corpus_id == "test-corpus"
    assert loaded.version == "1.0"
    assert loaded.record_count == 100


def test_offline_corpus_cache_load_nonexistent_manifest(temp_cache_dir):
    cache = OfflineCorpusCache(temp_cache_dir)
    loaded = cache.load_manifest("nonexistent", "1.0")
    assert loaded is None


def test_deterministic_fixture_importer_import(temp_cache_dir, sample_records):
    importer = DeterministicFixtureImporter("test-fixture", sample_records)
    assert importer.corpus_id == "test-fixture"

    manifest = importer.import_corpus(temp_cache_dir, version="1.0")
    assert manifest.corpus_id == "test-fixture"
    assert manifest.version == "1.0"
    assert manifest.record_count == 2

    manifest_path = temp_cache_dir / "manifest.json"
    assert manifest_path.exists()

    data_path = temp_cache_dir / "test-fixture-1.0.json"
    assert data_path.exists()
    loaded_records = json.loads(data_path.read_text(encoding="utf-8"))
    assert len(loaded_records) == 2
    assert loaded_records[0]["id"] == "test-question-1"


@pytest.mark.asyncio
async def test_deterministic_fixture_importer_load_from_manifest(temp_cache_dir, sample_records):
    importer = DeterministicFixtureImporter("test-fixture", sample_records)
    manifest = importer.import_corpus(temp_cache_dir, version="1.0")

    source = importer.load_from_manifest(manifest, temp_cache_dir)
    questions = await source.fetch_questions(limit=10)
    assert len(questions) == 2
    assert questions[0].id == "test-question-1"
    assert questions[1].id == "test-question-2"


@pytest.mark.asyncio
async def test_deterministic_fixture_importer_load_without_cached_data(temp_cache_dir, sample_records):
    importer = DeterministicFixtureImporter("test-fixture", sample_records)
    manifest = ImportManifest(
        corpus_id="test-fixture",
        version="1.0",
        imported_at=datetime.now(),
    )

    source = importer.load_from_manifest(manifest, temp_cache_dir)
    questions = await source.fetch_questions(limit=10)
    assert len(questions) == 2


def test_corpus_importer_compute_checksum():
    from xrtm.data.corpora.importers import CorpusImporter

    class TestImporter(CorpusImporter):
        @property
        def corpus_id(self):
            return "test"

        def import_corpus(self, output_dir, version=None):
            pass

        def load_from_manifest(self, manifest, data_dir):
            pass

    importer = TestImporter()
    data = b"test data"
    checksum = importer.compute_checksum(data)
    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_corpus_importer_verify_checksum():
    from xrtm.data.corpora.importers import CorpusImporter

    class TestImporter(CorpusImporter):
        @property
        def corpus_id(self):
            return "test"

        def import_corpus(self, output_dir, version=None):
            pass

        def load_from_manifest(self, manifest, data_dir):
            pass

    importer = TestImporter()
    data = b"test data"
    checksum = importer.compute_checksum(data)
    assert importer.verify_checksum(data, checksum) is True
    assert importer.verify_checksum(b"other data", checksum) is False
