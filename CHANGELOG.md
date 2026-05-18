# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.7] - 2026-05-18

### Changed
- Add forecast request/path compatibility aliases for the coordinated terminology release train.
- Align schema terminology with workflow and forecast-path authoring surfaces.

## [0.2.5] - 2026-04-30

### Fixed
- Hardened data-source error state, temporal snapshot semantics, UTC normalization, subgraph filtering, and no-leakage trade-window validation.

## [0.2.0] - 2026-02-04

### Changed
- **Architecture**: Restructured to `core/kit/providers` hierarchy for consistency with xrtm-forecast
- **core/**: Added `interfaces.py` (DataSource protocol) and `schemas/` (ForecastQuestion, ForecastOutput, etc.)
- **kit/**: Added placeholder directory for future data processors
- **providers/**: Reorganized into `local/` and `online/` subdirectories
- **README**: Added Project Structure section

### Breaking Changes
- Import paths changed: `xrtm.data.schemas` → `xrtm.data.core.schemas`
- Import paths changed: `xrtm.data.providers.data.local` → `xrtm.data.providers.local`

## [0.1.0] - 2026-01-27

### Added
- Initial release
- `ForecastQuestion` and `ForecastOutput` Pydantic schemas
- `MetadataBase` with Zero Leakage `snapshot_time` enforcement
- `LocalDataSource` for JSON file ingestion
- `PolymarketSource` for Gamma API integration
