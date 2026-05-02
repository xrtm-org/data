# Benchmark Corpus Policy

This document establishes the source classification and licensing policy for benchmark corpora used in XRTM release-gate evaluation and public performance claims.

## Scope

This policy applies to:
- Release-gate benchmarks that block production deployments
- Performance metrics published in release notes, papers, or public communications
- Corpus data bundled with XRTM distributions

This policy does **not** restrict:
- Local development and experimentation with any data source
- Internal research runs or ablation studies
- Optional supplemental benchmarks clearly documented as non-release-gate

## Source Classification

### Tier 1: Release-Gate Approved

**ForecastBench** is the preferred large-scale benchmark corpus for release-grade evaluation.

- **Status**: Primary release-gate benchmark
- **License**: Broadly redistributable, suitable for commercial use
- **Usage**: Required for performance claims and release gates
- **Rationale**: Large-scale, diverse question set with established provenance and licensing clarity
- **Implementation**: Full importer support required before 1.0 release
- **Location**: Import as external dependency; do not embed raw data in xrtm-data

### Tier 2: Evaluation-Only (Conditional)

**FOReCAst** (Future Outcome Reasoning and Confidence Assessment) is useful for comparative research and is the current preferred implementation target for external corpus expansion, but it remains evaluation-only unless explicitly approved.

- **Status**: Research/non-commercial license
- **License**: May have restrictions incompatible with commercial distribution
- **Usage**: Permitted for internal evaluation and academic research only
- **Release-gate status**: **NOT approved** for release gates or public performance claims unless legal review grants explicit written approval
- **Rationale**: Valuable for research comparisons, but licensing posture must be verified before any redistribution or commercial claims
- **Implementation**: Optional external importer; mark clearly as "evaluation-only" in all code and documentation

### Tier 3: Optional Supplemental

**Metaculus snapshot building** provides rich forecasting context but is optional and should not block releases.

- **Status**: Optional supplemental benchmark
- **License**: Subject to Metaculus Terms of Service; snapshot mechanics require provenance review
- **Usage**: Permitted as supplemental validation when properly attributed
- **Release-gate status**: **NOT a release-gate dependency**
- **Rationale**: Useful for domain-specific validation but adds operational complexity and external dependencies
- **Implementation**: Optional tooling; never required for CI or release gates

**Polymarket** is a supplemental source pending terms/provenance review.

- **Status**: Supplemental only after legal review
- **License**: Requires terms of service review and explicit approval
- **Usage**: Internal research only until approved
- **Release-gate status**: **NOT approved** for release gates
- **Rationale**: Live market data requires careful provenance tracking and terms compliance
- **Implementation**: Experimental importers only; never bundled or required

## Current Seed Corpus

The `xrtm-real-binary-v1` corpus is a minimal deterministic fixture embedded in `data/src/xrtm/data/corpora/real_binary.py`.

- **Purpose**: Offline validation, CI smoke tests, and provider-free benchmarking
- **Source**: Manually curated historical events with public verification sources
- **License**: Apache 2.0 (same as XRTM)
- **Size**: ~5-10 binary questions
- **Scope**: Intentionally minimal; not a comprehensive benchmark
- **Usage**: Always available for deterministic validation; does not replace Tier 1 benchmarks for performance claims

## Implementation Guidance

### For Corpus Importers

1. **Always declare license and tier** in module docstrings and README
2. **Never embed Tier 2/3 data** in xrtm-data or xrtm distributions
3. **Clearly mark evaluation-only sources** with runtime warnings if used in release contexts
4. **Prefer external dependencies** over embedding raw question data
5. **Document provenance** for every question in metadata

### For Release Gates

1. **Use only Tier 1 sources** for blocking CI checks and performance claims
2. **Require ForecastBench** for comprehensive pre-release validation
3. **Allow Tier 2/3 sources** in non-blocking supplemental reports only
4. **Never ship binaries or distributions** that bundle Tier 2/3 data without explicit approval

### For Documentation

1. **Reference this policy** in operator runbooks and benchmark scripts
2. **Label benchmark results** with source tier in all reports
3. **Include license/attribution** in performance tables and charts
4. **Warn users** when running evaluation-only benchmarks

## Maintenance

This policy is owned by the XRTM governance team. Updates require:
- Documented rationale for tier changes
- Legal review for any Tier 2 → Tier 1 promotion
- Broadcast to all maintainers before enforcement

## Implementation Infrastructure

The corpus registry and importer infrastructure (added 2025-01-01) provides:

### Corpus Registry (`data/src/xrtm/data/corpora/registry.py`)

Central metadata and discovery for benchmark corpora:
- `CorpusRegistry`: Singleton registry for corpus management
- `CorpusMetadata`: Tier, license, and provenance tracking
- `get_corpus()`: Load corpus DataSource by ID
- `list_available_corpora()`: Discovery with tier/release-gate filtering

### Corpus Importers (`data/src/xrtm/data/corpora/importers.py`)

Reproducible offline import/cache mechanisms:
- `CorpusImporter`: Base class for external corpus importers
- `ImportManifest`: Versioned manifest with integrity checksums
- `OfflineCorpusCache`: Deterministic cache for CI/test environments
- Separates import-time (network) from load-time (offline)

### Corpus Splits (`data/src/xrtm/data/corpora/splits.py`)

Deterministic train/eval/held-out partitioning:
- `SplitConfig`: Configurable split ratios with temporal support
- `CorpusSplitter`: Reproducible random or temporal splitting
- `SplitAwareCorpusSource`: Split-filtered DataSource wrapper

### Usage Example

```python
from xrtm.data.corpora import (
    get_corpus,
    list_available_corpora,
    CorpusSplitter,
    SplitConfig,
)

# Discover release-gate approved corpora
approved = list_available_corpora(release_gate_only=True)

# Load a corpus
source = get_corpus("xrtm-real-binary-v1")

# Create deterministic splits
config = SplitConfig(train_ratio=0.7, eval_ratio=0.2, held_out_ratio=0.1, seed=42)
splitter = CorpusSplitter(config)
questions = await source.fetch_questions(limit=100)
splits = splitter.split_corpus(questions)
```

## Related Documentation

- [`data/src/xrtm/data/corpora/`](../src/xrtm/data/corpora/): Corpus implementation modules
- [`data/src/xrtm/data/corpora/registry.py`](../src/xrtm/data/corpora/registry.py): Corpus registry and metadata
- [`data/src/xrtm/data/corpora/importers.py`](../src/xrtm/data/corpora/importers.py): Importer infrastructure
- [`data/src/xrtm/data/corpora/splits.py`](../src/xrtm/data/corpora/splits.py): Corpus splitting utilities
- [`scripts/bench_real.py`](../../scripts/bench_real.py): Provider-free benchmark harness
- [`xrtm/docs/operator-runbook.md`](../../xrtm/docs/operator-runbook.md): Performance and scale checks
- Governance schemas: `governance/schemas/forecast_object_v1.json`

## Summary Table

| Source | Tier | License | Release-Gate | Bundled | Notes |
|--------|------|---------|-------------|---------|-------|
| **ForecastBench** | 1 | Redistributable | ✅ Required | Via dependency | Primary benchmark |
| **xrtm-real-binary-v1** | 1 | Apache 2.0 | ✅ Allowed | ✅ Embedded | Minimal seed corpus |
| **FOReCAst** | 2 | Research-only | ❌ Pending approval | ❌ Never | Preferred external implementation target; evaluation use only |
| **Metaculus** | 3 | TOS-dependent | ❌ Optional | ❌ Never | Supplemental validation |
| **Polymarket** | 3 | Pending review | ❌ Not approved | ❌ Never | Experimental only |

---

**Last Updated**: 2025-01-01  
**Policy Version**: 1.0  
**Owner**: XRTM Governance Team
