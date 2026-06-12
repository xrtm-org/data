# xrtm-data v0.3.0

[![PyPI](https://img.shields.io/pypi/v/xrtm-data?style=flat-square)](https://pypi.org/project/xrtm-data/)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**The Snapshot Vault for XRTM.**

`xrtm-data` provides the schemas, question sources, and temporal sandboxing for the XRTM forecasting ecosystem.

## Installation

```bash
pip install xrtm-data
```

## Schemas

- **`ForecastQuestion`** — Standardized forecast question input
- **`ForecastOutput`** (alias `ForecastResult`) — Forecast result with probability, reasoning trace, causal graph
- **`CausalNode` / `CausalEdge` / `CausalGraph`** — Reasoning chain DAG
- **`BetaPrior` / `PriorState`** — Beta distribution for belief states
- **`TradeEvent` / `TradeWindow`** — Market trade data with temporal integrity

## Question Sources

| Source | API Key | Description |
|--------|---------|-------------|
| **real-binary** | None | 21 embedded historical binary questions (CI fixture) |
| **Polymarket** | None (public) | Live prediction market data via Gamma API |
| **Metaculus** | Free account | Forecasting questions from Metaculus |

```python
from xrtm.data.corpora import load_real_binary_questions
from xrtm.data.providers.online import PolymarketSource, MetaculusSource

# Built-in corpus


questions = load_real_binary_questions(limit=5)

# Live prediction markets (no API key)
poly = PolymarketSource()
markets = await poly.fetch_questions(limit=10)

# Metaculus (needs METACULUS_API_KEY)
meta = MetaculusSource()
meta_qs = await meta.fetch_questions(limit=10)
```

## License

Apache 2.0
