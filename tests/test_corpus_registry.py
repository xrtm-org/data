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

import pytest

from xrtm.data.corpora import (
    REAL_BINARY_CORPUS_ID,
    CorpusManifest,
    CorpusMetadata,
    CorpusRegistry,
    CorpusSplit,
    CorpusTier,
    LicenseType,
    RealBinaryCorpusSource,
    get_corpus,
    get_corpus_metadata,
    list_available_corpora,
)


@pytest.fixture
def fresh_registry():
    """Provide a fresh registry for each test."""
    CorpusRegistry.reset_instance()
    registry = CorpusRegistry.get_instance()
    yield registry
    CorpusRegistry.reset_instance()


def test_corpus_registry_singleton(fresh_registry):
    registry1 = CorpusRegistry.get_instance()
    registry2 = CorpusRegistry.get_instance()
    assert registry1 is registry2


def test_real_binary_corpus_is_registered(fresh_registry):
    metadata = fresh_registry.get_metadata(REAL_BINARY_CORPUS_ID)
    assert metadata.corpus_id == REAL_BINARY_CORPUS_ID
    assert metadata.tier == CorpusTier.TIER_1
    assert metadata.license_type == LicenseType.APACHE_2_0
    assert metadata.release_gate_approved is True
    assert metadata.bundled is True


def test_corpus_registry_list_corpora(fresh_registry):
    all_corpora = fresh_registry.list_corpora()
    assert len(all_corpora) >= 1
    assert any(c.corpus_id == REAL_BINARY_CORPUS_ID for c in all_corpora)


def test_corpus_registry_list_release_gate_only(fresh_registry):
    release_gate = fresh_registry.list_corpora(release_gate_only=True)
    assert all(c.is_release_gate_approved() for c in release_gate)
    assert any(c.corpus_id == REAL_BINARY_CORPUS_ID for c in release_gate)


def test_corpus_registry_list_by_tier(fresh_registry):
    tier1 = fresh_registry.list_corpora(tier=CorpusTier.TIER_1)
    assert all(c.tier == CorpusTier.TIER_1 for c in tier1)
    assert any(c.corpus_id == REAL_BINARY_CORPUS_ID for c in tier1)


@pytest.mark.asyncio
async def test_get_corpus_convenience_function(fresh_registry):
    source = get_corpus(REAL_BINARY_CORPUS_ID)
    assert isinstance(source, RealBinaryCorpusSource)
    questions = await source.fetch_questions(limit=5)
    assert len(questions) == 5


def test_get_corpus_metadata_convenience_function(fresh_registry):
    metadata = get_corpus_metadata(REAL_BINARY_CORPUS_ID)
    assert metadata.corpus_id == REAL_BINARY_CORPUS_ID
    assert metadata.tier == CorpusTier.TIER_1


def test_list_available_corpora_convenience_function(fresh_registry):
    corpora = list_available_corpora()
    assert len(corpora) >= 1
    release_gate = list_available_corpora(release_gate_only=True)
    assert all(c.is_release_gate_approved() for c in release_gate)


def test_corpus_metadata_is_release_gate_approved():
    metadata = CorpusMetadata(
        corpus_id="test",
        name="Test",
        tier=CorpusTier.TIER_1,
        license_type=LicenseType.APACHE_2_0,
        description="Test corpus",
        version="1.0",
        release_gate_approved=True,
    )
    assert metadata.is_release_gate_approved() is True

    metadata_tier2 = CorpusMetadata(
        corpus_id="test2",
        name="Test2",
        tier=CorpusTier.TIER_2,
        license_type=LicenseType.RESEARCH_ONLY,
        description="Test corpus",
        version="1.0",
        release_gate_approved=False,
    )
    assert metadata_tier2.is_release_gate_approved() is False


def test_corpus_metadata_requires_warning():
    tier1 = CorpusMetadata(
        corpus_id="test1",
        name="Test1",
        tier=CorpusTier.TIER_1,
        license_type=LicenseType.APACHE_2_0,
        description="Test",
        version="1.0",
    )
    assert tier1.requires_warning() is False

    tier2 = CorpusMetadata(
        corpus_id="test2",
        name="Test2",
        tier=CorpusTier.TIER_2,
        license_type=LicenseType.RESEARCH_ONLY,
        description="Test",
        version="1.0",
    )
    assert tier2.requires_warning() is True

    tier3 = CorpusMetadata(
        corpus_id="test3",
        name="Test3",
        tier=CorpusTier.TIER_3,
        license_type=LicenseType.TOS_DEPENDENT,
        description="Test",
        version="1.0",
    )
    assert tier3.requires_warning() is True


def test_corpus_metadata_to_dict():
    metadata = CorpusMetadata(
        corpus_id="test",
        name="Test Corpus",
        tier=CorpusTier.TIER_1,
        license_type=LicenseType.APACHE_2_0,
        description="Test corpus",
        version="1.0",
        release_gate_approved=True,
        bundled=True,
        size_estimate=100,
        tags=["test", "fixture"],
        provenance_url="https://example.com",
        license_url="https://example.com/license",
        citation="Test Citation",
    )
    data = metadata.to_dict()
    assert data["corpus_id"] == "test"
    assert data["tier"] == "tier-1"
    assert data["license_type"] == "apache-2.0"
    assert data["tags"] == ["test", "fixture"]


def test_corpus_manifest_load_source(fresh_registry):
    manifest = fresh_registry.get_manifest(REAL_BINARY_CORPUS_ID)
    source = manifest.load_source()
    assert isinstance(source, RealBinaryCorpusSource)


def test_corpus_manifest_load_source_with_split(fresh_registry):
    manifest = fresh_registry.get_manifest(REAL_BINARY_CORPUS_ID)
    source = manifest.load_source(split=CorpusSplit.FULL)
    assert isinstance(source, RealBinaryCorpusSource)


def test_corpus_manifest_load_source_invalid_split(fresh_registry):
    manifest = fresh_registry.get_manifest(REAL_BINARY_CORPUS_ID)
    with pytest.raises(ValueError, match="not available"):
        manifest.load_source(split=CorpusSplit.TRAIN)


def test_corpus_registry_duplicate_registration(fresh_registry):
    metadata = CorpusMetadata(
        corpus_id=REAL_BINARY_CORPUS_ID,
        name="Duplicate",
        tier=CorpusTier.TIER_1,
        license_type=LicenseType.APACHE_2_0,
        description="Duplicate",
        version="1.0",
    )
    manifest = CorpusManifest(
        corpus_id=REAL_BINARY_CORPUS_ID,
        metadata=metadata,
        loader_fn=lambda: RealBinaryCorpusSource(),
    )
    with pytest.raises(ValueError, match="already registered"):
        fresh_registry.register(manifest)


def test_corpus_registry_get_unknown_corpus(fresh_registry):
    with pytest.raises(KeyError, match="not registered"):
        fresh_registry.get_manifest("unknown-corpus-id")

    with pytest.raises(KeyError, match="not registered"):
        fresh_registry.get_metadata("unknown-corpus-id")


def test_corpus_manifest_warning_for_tier2(fresh_registry):
    metadata = CorpusMetadata(
        corpus_id="test-tier2",
        name="Test Tier 2",
        tier=CorpusTier.TIER_2,
        license_type=LicenseType.RESEARCH_ONLY,
        description="Test",
        version="1.0",
    )
    manifest = CorpusManifest(
        corpus_id="test-tier2",
        metadata=metadata,
        loader_fn=lambda: RealBinaryCorpusSource(),
    )
    fresh_registry.register(manifest)

    with pytest.warns(UserWarning, match="tier-2"):
        manifest.load_source()
