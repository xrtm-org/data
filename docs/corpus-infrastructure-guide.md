# Corpus Infrastructure Developer Guide

This guide explains how to use the XRTM corpus registry, importers, and splits infrastructure for benchmark corpus management.

## Quick Start

### Loading a Corpus

```python
from xrtm.data.corpora import get_corpus

# Load the default embedded corpus
source = get_corpus("xrtm-real-binary-v1")

# Load FOReCAst corpus (Tier 2, evaluation-only)
# Uses cached imported data if present, otherwise a deterministic fixture preview.
forecast_source = get_corpus("forecast-v1")  # Emits warning about Tier 2 status

# Use as a standard DataSource
questions = await source.fetch_questions(limit=10)
question = await source.get_question_by_id("real-binary-2023-fed-mar-hike")
```

### Discovering Available Corpora

```python
from xrtm.data.corpora import list_available_corpora, CorpusTier

# List all corpora
all_corpora = list_available_corpora()

# List only release-gate approved corpora
release_gate = list_available_corpora(release_gate_only=True)

# List by tier
tier1_corpora = list_available_corpora(tier=CorpusTier.TIER_1)
```

### Creating Train/Eval Splits

```python
from xrtm.data.corpora import (
    get_corpus,
    SplitConfig,
    CorpusSplitter,
    SplitAwareCorpusSource,
)

# Load questions
source = get_corpus("xrtm-real-binary-v1")
questions = await source.fetch_questions(limit=100)

# Configure deterministic splits
config = SplitConfig(
    train_ratio=0.7,
    eval_ratio=0.2,
    held_out_ratio=0.1,
    seed=42,  # Ensures reproducibility
)

# Create splits
splitter = CorpusSplitter(config)
splits = splitter.split_corpus(questions)

# Access split data
print(f"Train: {len(splits['train'])} questions")
print(f"Eval: {len(splits['eval'])} questions")
print(f"Held-out: {len(splits['held-out'])} questions")

# Create a split-aware source for filtered access
split_source = SplitAwareCorpusSource(source, splits, default_split="train")
train_questions = await split_source.fetch_questions(limit=10, split="train")
```

### Temporal Splits

For time-based train/eval partitioning:

```python
from datetime import datetime
from xrtm.data.corpora import SplitConfig, CorpusSplitter

config = SplitConfig(
    train_ratio=0.7,
    eval_ratio=0.3,
    held_out_ratio=0.0,
    temporal_split=True,
    temporal_cutoff=datetime(2023, 7, 1),  # Split at this timestamp
    seed=42,
)

splitter = CorpusSplitter(config)
splits = splitter.split_corpus(questions)

# Questions before cutoff → train/eval
# Questions after cutoff → held-out
```

## Advanced Topics

### Registering a Custom Corpus

```python
from xrtm.data.corpora import (
    CorpusRegistry,
    CorpusMetadata,
    CorpusManifest,
    CorpusTier,
    LicenseType,
    CorpusSplit,
)
from xrtm.data.core import DataSource

class MyCustomSource(DataSource):
    # Implement DataSource interface
    async def fetch_questions(self, query=None, limit=5, *, snapshot_time=None):
        return []
    
    async def get_question_by_id(self, question_id, *, snapshot_time=None):
        return None

# Create metadata
metadata = CorpusMetadata(
    corpus_id="my-custom-corpus",
    name="My Custom Corpus",
    tier=CorpusTier.TIER_1,
    license_type=LicenseType.APACHE_2_0,
    description="A custom corpus for testing",
    version="1.0",
    release_gate_approved=True,
    bundled=False,
    size_estimate=1000,
    tags=["custom", "test"],
)

# Create manifest
manifest = CorpusManifest(
    corpus_id="my-custom-corpus",
    metadata=metadata,
    loader_fn=lambda: MyCustomSource(),
    available_splits=[CorpusSplit.FULL],
)

# Register
registry = CorpusRegistry.get_instance()
registry.register(manifest)

# Now it's available globally
source = get_corpus("my-custom-corpus")
```

### Creating a Corpus Importer

For external corpora that need to be downloaded and cached:

```python
from pathlib import Path
from datetime import datetime
from xrtm.data.corpora.importers import (
    CorpusImporter,
    ImportManifest,
    OfflineCorpusCache,
)

class MyCorpusImporter(CorpusImporter):
    @property
    def corpus_id(self) -> str:
        return "my-external-corpus"
    
    def import_corpus(self, output_dir: Path, version: str = None) -> ImportManifest:
        """Download and cache the corpus."""
        version = version or "1.0"
        
        # Download data (this happens at import-time, not test-time)
        data = self._download_corpus_data()
        
        # Save to cache
        data_path = output_dir / f"{self.corpus_id}-{version}.json"
        data_path.write_text(json.dumps(data), encoding="utf-8")
        
        # Compute checksum for integrity
        checksum = self.compute_checksum(data_path.read_bytes())
        
        # Create manifest
        manifest = ImportManifest(
            corpus_id=self.corpus_id,
            version=version,
            imported_at=datetime.now(),
            source_url="https://example.com/corpus",
            source_checksum=checksum,
            record_count=len(data),
        )
        
        manifest.write(output_dir / "manifest.json")
        return manifest
    
    def load_from_manifest(self, manifest: ImportManifest, data_dir: Path):
        """Load from cached data (offline, deterministic)."""
        data_path = data_dir / f"{self.corpus_id}-{manifest.version}.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))
        
        # Verify integrity
        if not self.verify_checksum(data_path.read_bytes(), manifest.source_checksum):
            raise ValueError("Checksum mismatch")
        
        return MyCustomSource(data)

# Usage: Import phase (network access allowed)
importer = MyCorpusImporter()
cache = OfflineCorpusCache(Path(".cache/corpora"))
corpus_dir = cache.get_corpus_dir("my-external-corpus", "1.0")

if not cache.is_cached("my-external-corpus", "1.0"):
    manifest = importer.import_corpus(corpus_dir, version="1.0")
    cache.save_manifest(manifest)

# Usage: Load phase (offline, for tests)
manifest = cache.load_manifest("my-external-corpus", "1.0")
source = importer.load_from_manifest(manifest, corpus_dir)
```

### FOReCAst Importer Example

The FOReCAst corpus demonstrates the importer pattern for external datasets:

```python
from xrtm.data.corpora import FOReCAstImporter, OfflineCorpusCache
from pathlib import Path

# Option 1: Use HuggingFace datasets (requires network and `datasets` library)
importer = FOReCAstImporter(use_hf_datasets=True)
cache = OfflineCorpusCache(Path.home() / ".xrtm" / "corpus-cache")
corpus_dir = cache.get_corpus_dir("forecast-v1", "1.0")

# Import from HuggingFace (one-time network access)
if not cache.is_cached("forecast-v1", "1.0"):
    manifest = importer.import_corpus(corpus_dir, version="1.0")
    cache.save_manifest(manifest)

# Option 2: Use deterministic fixtures (no network, for testing)
test_importer = FOReCAstImporter(use_hf_datasets=False)
test_manifest = test_importer.import_corpus(Path("./test-cache"), version="1.0")

# Load from cached manifest (offline)
manifest = cache.load_manifest("forecast-v1", "1.0")
source = importer.load_from_manifest(manifest, corpus_dir)
questions = await source.fetch_questions(limit=100)
```

If you call `get_corpus("forecast-v1")` without importing first, the registry falls back to a deterministic fixture preview so tests and offline examples stay stable. Import into the cache first when you want the full external dataset.

## Testing Best Practices

### Keep Tests Deterministic

```python
import pytest
from xrtm.data.corpora import get_corpus, SplitConfig, CorpusSplitter

@pytest.mark.asyncio
async def test_deterministic_corpus_loading():
    # Load the same corpus twice
    source1 = get_corpus("xrtm-real-binary-v1")
    source2 = get_corpus("xrtm-real-binary-v1")
    
    questions1 = await source1.fetch_questions(limit=10)
    questions2 = await source2.fetch_questions(limit=10)
    
    # Results should be identical
    assert [q.id for q in questions1] == [q.id for q in questions2]

def test_deterministic_splits():
    from xrtm.data.corpora import load_real_binary_questions
    
    questions = load_real_binary_questions()
    
    # Same config = same splits
    config = SplitConfig(train_ratio=0.7, eval_ratio=0.2, held_out_ratio=0.1, seed=42)
    splitter1 = CorpusSplitter(config)
    splitter2 = CorpusSplitter(config)
    
    splits1 = splitter1.split_corpus(questions)
    splits2 = splitter2.split_corpus(questions)
    
    assert [q.id for q in splits1["train"]] == [q.id for q in splits2["train"]]
```

### Never Download in Tests

```python
# ❌ BAD: Downloads during test execution
@pytest.mark.asyncio
async def test_external_corpus():
    importer = ExternalCorpusImporter()
    manifest = importer.import_corpus(tmp_path)  # Network access!
    source = importer.load_from_manifest(manifest, tmp_path)

# ✅ GOOD: Use pre-cached fixtures
@pytest.fixture(scope="session")
def cached_corpus_manifest():
    cache = OfflineCorpusCache(Path(".cache/test-corpora"))
    manifest = cache.load_manifest("test-corpus", "1.0")
    if manifest is None:
        pytest.skip("Test corpus not cached; run import script first")
    return manifest

@pytest.mark.asyncio
async def test_external_corpus(cached_corpus_manifest):
    importer = ExternalCorpusImporter()
    source = importer.load_from_manifest(cached_corpus_manifest, Path(".cache/test-corpora"))
    questions = await source.fetch_questions(limit=10)
    assert len(questions) <= 10
```

## Corpus Policy Compliance

Always check the corpus tier before using in release gates:

```python
from xrtm.data.corpora import get_corpus_metadata, CorpusTier

metadata = get_corpus_metadata("my-corpus")

# Only use Tier 1 for release gates
if metadata.tier != CorpusTier.TIER_1:
    raise ValueError(f"Corpus {metadata.corpus_id} is not approved for release gates")

if not metadata.is_release_gate_approved():
    raise ValueError(f"Corpus {metadata.corpus_id} is not release-gate approved")
```

## Migration from Legacy Code

The new infrastructure is backward-compatible with existing real-binary usage:

```python
# Old code (still works)
from xrtm.data.corpora import load_real_binary_questions
questions = load_real_binary_questions(limit=10)

# New code (recommended)
from xrtm.data.corpora import get_corpus
source = get_corpus("xrtm-real-binary-v1")
questions = await source.fetch_questions(limit=10)
```

Both approaches work, but the registry-based approach provides:
- Centralized metadata and discovery
- Consistent API across all corpora
- Tier and license enforcement
- Split support

## See Also

- [Benchmark Corpus Policy](./benchmark-corpus-policy.md) - Tier classification and licensing
- `data/src/xrtm/data/corpora/registry.py` - Registry implementation
- `data/src/xrtm/data/corpora/importers.py` - Importer infrastructure
- `data/src/xrtm/data/corpora/splits.py` - Splitting utilities
- `data/tests/test_corpus_*.py` - Usage examples

## Integration with Validation Harness

The corpus registry integrates directly with the large-scale validation harness in `xrtm.product.validation`. This provides:

### Corpus-Aware Validation

```bash
# Discover available corpora
xrtm validate list-corpora
xrtm validate list-corpora --tier tier-1
xrtm validate list-corpora --release-gate-only

# Run validation with specific corpus
xrtm validate run \
  --corpus-id xrtm-real-binary-v1 \
  --provider mock \
  --limit 50 \
  --iterations 5

# Use corpus splits for partitioned validation
xrtm validate run \
  --corpus-id xrtm-real-binary-v1 \
  --split train \
  --limit 100
```

### Tier Enforcement

The validation harness enforces tier requirements:

- **Release-gate mode**: Only Tier 1 corpora allowed
- **Non-Tier-1 usage**: Emits warnings about license restrictions
- **Safety limits**: Local-LLM runs capped by default

```python
from xrtm.product.validation import run_validation, ValidationOptions

# Release-gate validation (enforces Tier 1)
options = ValidationOptions(
    corpus_id="xrtm-real-binary-v1",
    release_gate_mode=True,
    provider="mock",
    limit=100,
)
report = run_validation(options)
```

### Structured Artifacts

Validation runs produce structured artifacts with corpus metadata:

```json
{
  "schema_version": "xrtm.validation.v1",
  "corpus": {
    "corpus_id": "xrtm-real-binary-v1",
    "name": "XRTM Real Binary v1",
    "tier": "tier-1",
    "license": "apache-2.0",
    "version": "1.0",
    "release_gate_approved": true
  },
  "configuration": {
    "split": "train",
    "provider": "mock",
    "limit": 100,
    "iterations": 5,
    "release_gate_mode": true
  },
  "summary": {
    "total_duration_seconds": 42.5,
    "total_forecasts": 500,
    "forecasts_per_second": 11.76
  }
}
```

See `xrtm/docs/operator-runbook.md` for complete validation harness documentation.

---

**Last Updated**: 2025-01-01  
**Version**: 1.0
