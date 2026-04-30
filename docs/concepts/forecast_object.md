# The Forecast Object Standard

The **Forecast Object** is the atomic unit of exchange in the xrtm ecosystem. It is defined by `xrtm-data` and strictly enforced by Governance.

## Core Schema Components

Every valid prediction must adhere to this structure:

```python
class ForecastOutput(BaseModel):
    question_id: str
    probability: float          # Main signal (0.0 to 1.0)
    confidence: Optional[float] # Meta-uncertainty
    reasoning: str              # Surface-level explanation
    logical_trace: List[CausalNode] # Structured causal chain
```

## The "Causal Node" requirement

Unlike simple ML models that output a single number, xrtm agents must output a **Reasoning Trace**. This is stored as a directed acyclic graph (DAG) of `CausalNode` objects.

Governance v1/v1.1 names this surface `reasoning_trace`. The runtime `ForecastOutput` keeps the historical `logical_trace`/`logical_edges` fields for compatibility, while accepting `reasoning_trace` input and exposing a read-only `reasoning_trace` alias with the governance shape.

### Why?
1.  **Explainability**: We can debug *why* the agent made a prediction.
2.  **Intervention**: `xrtm-eval` can run "What-If" scenarios by modifying nodes in the trace.

## Compliance
Any data provider or agent outputting forecasts **MUST** validate against the `ForecastOutput` Pydantic model.
