# xrtm-data API Reference

## Schemas (xrtm.data.schemas)

### Forecast Definitions

- **`ForecastResult`** / **`ForecastOutput`**: The canonical forecast-result object with legacy alias support.
- **`ForecastRequest`** / **`ForecastQuestion`**: The canonical forecast-request object with legacy alias support.
- Ground-truth resolution objects live in `xrtm-eval`, not `xrtm-data`.

### Reasoning Trace

- **`ReasoningTrace`**: Narrative trace plus a qualified causal graph.
- **`CausalGraph`**: Qualified causal structure nested inside a reasoning trace.
- **`CausalNode`**: A single forecast-path reasoning step.
- **`CausalEdge`**: Qualified causal connection between reasoning steps.

## Providers (xrtm.data.providers)

- **`DataSource`**: Abstract base class for all providers.
- **`DataSourceError`**, **`SourceFetchError`**, **`SourceTemporalIntegrityError`**: Provider failure exceptions exposed for callers that opt into raised errors.
- **`LocalDataSource`**: File-based provider.
- **`PolymarketSource`**: Live Gamma API market data. Historical `snapshot_time` requests are rejected to avoid future leakage; compatible callers can inspect `last_error`, or pass `raise_on_error=True`.
- **`PolymarketTradeSource`**: Subgraph trade data. Returned trades are filtered to the requested `[start_time, end_time]` window, and GraphQL error payloads raise `SourceFetchError`.
