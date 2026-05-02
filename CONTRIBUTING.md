# Contributing to xrtm-data

Reference schemas for the XRTM forecasting ecosystem. We welcome contributions!

## Development Environment

```bash
# Install uv (https://github.com/astral-sh/uv)
uv sync --all-extras

# Run checks
uv run ruff check .
uv run mypy .
uv run pytest
```

## Key Standards

1. **Type Safety**: All code must pass `mypy .`
2. **License Headers**: Every `.py` file must have Apache 2.0 header
3. **Public API**: Define `__all__` in every module
4. **Docstrings**: Use Hugging Face style (`r""" """`)

## Cross-repo compatibility

`xrtm-data` is an upstream contract repo for the rest of the stack. Before merging a change that affects documented schemas, serialized payloads, dependency/version expectations, or cross-repo CI behavior, follow the canonical [Cross-Repository Compatibility and Coordination Policy](https://github.com/xrtm-org/governance/blob/main/policies/cross-repo-compatibility-policy.md).

When a change affects downstream consumers, link the related PRs and validate with explicit downstream refs or candidate artifacts instead of same-name branch aliases.

## Pull Request Process

1. Fork and create branch from `main`
2. Add tests in `tests/`
3. Ensure checks pass
4. Update docs if changing public APIs
