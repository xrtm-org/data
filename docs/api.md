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
- **`LocalDataSource`**: File-based provider.
- **`PolymarketSource`**: Live market data.
