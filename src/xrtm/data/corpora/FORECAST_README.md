# FOReCAst Corpus Importer

This module provides an importer for the **FOReCAst** (Future Outcome Reasoning and Confidence Assessment) benchmark dataset for XRTM.

## Overview

- **Dataset**: MoyYuan/FOReCAst on Hugging Face
- **License**: MIT
- **Size**: 1,390 resolved probabilistic forecasting questions
- **Splits**: Train (952), Dev (142), Test (296)
- **Publication**: NeurIPS 2025 Datasets and Benchmarks Track

## Tier Classification

**Important**: FOReCAst is classified as **Tier 2 (evaluation-only)** per the XRTM benchmark corpus policy.

- ✅ Permitted for internal evaluation and academic research
- ❌ NOT approved for release gates or public performance claims
- ❌ NOT bundled in XRTM distributions
- ⚠️ Requires explicit written approval for Tier 1 promotion

See `data/docs/benchmark-corpus-policy.md` for complete policy details.

## Usage

### Option 1: Using Registry (Recommended)

```python
from xrtm.data.corpora import get_corpus

# Load FOReCAst via registry (emits Tier 2 warning)
# Uses cached imported data if present, otherwise a deterministic fixture preview.
source = get_corpus("forecast-v1")

# Use as standard DataSource
questions = await source.fetch_questions(limit=100)
```

### Option 2: Direct Importer Usage

```python
from xrtm.data.corpora import FOReCAstImporter, OfflineCorpusCache
from pathlib import Path

# Create importer with HuggingFace datasets support
importer = FOReCAstImporter(use_hf_datasets=True)

# Set up cache
cache = OfflineCorpusCache(Path.home() / ".xrtm" / "corpus-cache")
corpus_dir = cache.get_corpus_dir("forecast-v1", "1.0")

# Import corpus (one-time network access)
if not cache.is_cached("forecast-v1", "1.0"):
    manifest = importer.import_corpus(corpus_dir, version="1.0")
    cache.save_manifest(manifest)

# Load from cache (offline)
manifest = cache.load_manifest("forecast-v1", "1.0")
source = importer.load_from_manifest(manifest, corpus_dir)
```

### Option 3: Fixture Mode (Testing)

```python
# Use deterministic fixtures (no network required)
importer = FOReCAstImporter(use_hf_datasets=False)
manifest = importer.import_corpus(Path("./test-cache"), version="1.0")
source = importer.load_from_manifest(manifest, Path("./test-cache"))
```

## Installation

The importer requires the `datasets` library for HuggingFace integration:

```bash
pip install datasets
```

For testing/offline usage, no additional dependencies are required.

## Schema Mapping

FOReCAst records are converted into XRTM `ForecastQuestion` objects through a FOReCAst-specific record model:

| FOReCAst Field | XRTM Field | Notes |
|---------------|------------|-------|
| `id` | `id` | Direct mapping |
| `question` | `title` + `content` | Question text used for both |
| `type` | `subject_type` + tags + `source_metadata.question_type` | Boolean/quantity/timeframe preserved |
| `resolution` | `resolved_outcome` + `source_metadata.resolution` | `yes`/`no` are promoted to resolved boolean outcomes |
| `resolution_time` | `resolution_time` + `source_metadata.resolution_time` | ISO 8601 format |
| `created_time` | `snapshot_time` | ISO 8601 format |
| `confidence` | `source_metadata.confidence` | Community confidence score |

## Testing

The importer includes comprehensive test coverage:

```bash
pytest tests/test_forecast_importer.py -v
```

All tests use deterministic fixtures and do NOT require network access.

## Fixture Fallback

The registry path `get_corpus("forecast-v1")` is offline-safe:

- if a cached imported dataset exists, it loads that cached data
- otherwise it falls back to a deterministic fixture preview

Use the importer path above when you need the full external FOReCAst dataset in cache.

## Provenance

- **Dataset URL**: https://huggingface.co/datasets/MoyYuan/FOReCAst
- **License**: MIT (with pending non-commercial clause clarification)
- **Citation**: FOReCAst: Future Outcome Reasoning and Confidence Assessment. NeurIPS 2025 Datasets and Benchmarks Track.

## Related Documentation

- [Benchmark Corpus Policy](../../docs/benchmark-corpus-policy.md) - Tier classification and licensing
- [Corpus Infrastructure Guide](../../docs/corpus-infrastructure-guide.md) - Developer guide for corpus management
- [Corpus Registry](./registry.py) - Central corpus discovery and metadata

## Status

- ✅ Implementation: Complete
- ✅ Tests: 16 passing tests with full coverage
- ✅ Documentation: Inline docstrings and README
- ⚠️ Tier Status: Tier 2 (evaluation-only)
- 🔄 License Review: Non-commercial clause pending clarification
- ❌ Release Gate: NOT approved (requires explicit approval)

---

**Last Updated**: 2025-01-01  
**Implementation**: M5 Product Step (FOReCAst External Importer)
