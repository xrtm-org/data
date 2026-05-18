# xrtm-data

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/xrtm-data.svg)](https://pypi.org/project/xrtm-data/)

**The Snapshot Vault for XRTM.**

`xrtm-data` provides the rigid schemas and temporal sandboxing infrastructure required for zero-leakage forecasting. It defines the "Ground Truth" data structures that the rest of the ecosystem (Forecast, Eval, Train) relies on.

## Part of the XRTM Ecosystem

```
Layer 4: xrtm-train    → (imports all)
Layer 3: xrtm-forecast → (imports eval, data)
Layer 2: xrtm-eval     → (imports data)
Layer 1: xrtm-data     → (zero dependencies) ← YOU ARE HERE
```

`xrtm-data` is the foundation layer with **zero dependencies** on other xrtm packages.

## Installation

```bash
pip install xrtm-data
```

## Core Primitives

### 1. The Forecast Object Standard
Adhering to strict Governance, the canonical runtime schema is
`ForecastResult` (legacy alias: `ForecastOutput`). Every forecast result carries
`forecast_request_id`, `probability`, a `reasoning_trace`, and an optional
`execution_trace`. Legacy `question_id`, `reasoning`, `logical_trace`,
`logical_edges`, and `structural_trace` inputs remain accepted for compatibility.

```python
from xrtm.data import ForecastResult, CausalNode

forecast_result = ForecastResult(
    forecast_request_id="q_123",
    probability=0.75,
    reasoning_trace={
        "narrative": "Base rate analysis suggests...",
        "causal_graph": {
            "nodes": [
                CausalNode(event="Inflation rises", probability=0.8),
                CausalNode(event="Fed cuts rates", probability=0.4),
            ]
        },
    },
    execution_trace=["ingestion", "forecast"],
)
```

### 2. Zero Leakage
The `MetadataBase` enforces a strict `snapshot_time`. This timestamp represents the "End of History" for the model. Any data point generated after this time is considered "Future Leakage" and is programmatically inaccessible during backtesting.

## Project Structure

```
src/xrtm/data/
├── core/            # Interfaces & Schemas (domain-agnostic)
│   ├── interfaces.py    # DataSource protocol
│   └── schemas/         # ForecastRequest, ForecastResult, etc.
├── kit/             # Composable utilities (processors)
└── providers/       # External data source implementations
    ├── local/           # LocalDataSource (JSON files)
    └── online/          # PolymarketSource (Gamma API)
```

## Development

Prerequisites:
- [uv](https://github.com/astral-sh/uv)

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest
```
