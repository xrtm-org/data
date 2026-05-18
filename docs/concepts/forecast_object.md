# The Forecast Object Standard

The **Forecast Object** is the atomic unit of exchange in the xrtm ecosystem. It is defined by `xrtm-data` and strictly enforced by Governance.

## Core Schema Components

Every valid forecast result must adhere to this structure:

```python
class ForecastResult(BaseModel):
    forecast_request_id: str
    probability: float              # Main signal (0.0 to 1.0)
    reasoning_trace: ReasoningTrace # Narrative + qualified causal graph
    execution_trace: List[str]      # Workflow stages that produced the result
```

Legacy callers may still use `ForecastOutput`, `question_id`, `reasoning`,
`logical_trace`, `logical_edges`, and `structural_trace`, but new code should
write the canonical request/result and trace vocabulary.

## The reasoning-trace requirement

Unlike simple ML models that output a single number, xrtm agents must output a
**Reasoning Trace**. The canonical serialized field is `reasoning_trace`,
optionally carrying a qualified `causal_graph` of `CausalNode` / `CausalEdge`
records for the forecast path.

Governance v1/v1.1 names this surface `reasoning_trace`. The runtime `ForecastOutput` treats `reasoning_trace` as the canonical serialized shape while keeping the historical `logical_trace`/`logical_edges` fields as compatibility aliases for older callers.

### Why?
1.  **Explainability**: We can debug *why* the agent made a prediction.
2.  **Intervention**: `xrtm-eval` can run "What-If" scenarios by modifying nodes in the trace.

## Compliance
Any data provider or agent outputting forecasts **MUST** validate against the
canonical `ForecastResult` / compatible `ForecastOutput` Pydantic model.
