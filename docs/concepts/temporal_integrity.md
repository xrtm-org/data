# Temporal Integrity in Data

**Temporal Integrity** in the context of `xrtm-data` refers to the **immutable storage** of historical truth. It is the guarantee that once a snapshot is saved, it represents the state of the world at that exact moment, forever.

## The Snapshot Time

The `snapshot_time` field in `MetadataBase` is the single most critical field in the schema.

```python
class MetadataBase(BaseModel):
    snapshot_time: datetime  # The "End of History"
```

### Rules
1.  **Immutable Boundary**: No data point generated or modified after `snapshot_time` can be included in an object marked with that timestamp.
2.  **Zero Leakage**: Providers implementation must ensure they do not fetch "live" data if a `snapshot_time` is provided. They must query the state *as it was* at that time.

## Evaluation vs. Training

- **For Training**: We need historical snapshots to simulate "not knowing the future."
- **For Evaluation**: We need Future Resolutions to score the past predictions.

`xrtm-data` stores both **Questions** (the past) and **Resolutions** (the future relative to the question) in separate structures to prevent contamination.
