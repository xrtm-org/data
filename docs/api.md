# xrtm-data API Reference

## Schemas (xrtm.data.schemas)

### Forecast Definitions

- **`ForecastOutput`**: The standard prediction object.
- **`ForecastQuestion`**: The input question object.
- **`ForecastResolution`**: The ground truth object.

### Causal Graph

- **`CausalNode`**: A single reasoning step.
- **`CausalEdge`**: Connection between nodes.

## Providers (xrtm.data.providers)

- **`DataSource`**: Abstract base class for all providers.
- **`DataSourceError`**, **`SourceFetchError`**, **`SourceTemporalIntegrityError`**: Provider failure exceptions exposed for callers that opt into raised errors.
- **`LocalDataSource`**: File-based provider.
- **`PolymarketSource`**: Live Gamma API market data. Historical `snapshot_time` requests are rejected to avoid future leakage; compatible callers can inspect `last_error`, or pass `raise_on_error=True`.
- **`PolymarketTradeSource`**: Subgraph trade data. Returned trades are filtered to the requested `[start_time, end_time]` window, and GraphQL error payloads raise `SourceFetchError`.
