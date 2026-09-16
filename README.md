# SETDS MVP v8 Demo

A runnable research/demo prototype built from the v7 verification-stable baseline.

## What is new here

- shared evidence registry;
- signal corroboration separated from hypothesis convergence;
- `supports / refutes / neutral` evidence effects;
- provenance labels;
- trend-aware guest longitudinal analysis;
- employee shift context without automatic personnel blame;
- cause confidence separated from action confidence;
- v7-style action lifecycle, pilot gating and Decision Memory;
- Relative Competitive Gap;
- bounded 2–3 path scenario engine;
- Streamlit interface for a live demonstrator.

## Important scientific limits

This is **not** an empirical Altair model. Demo values and probabilities are illustrative. Evidence multipliers are expert-configured weights, not formal likelihood ratios. The Employee pressure score is an explicit demo heuristic, not a validated HR/health scale. Long-horizon outputs are scenarios/foresight, not point forecasts.

## Run

```bash
python -m pip install -r requirements.txt
python tests.py
python seed_demo.py
streamlit run app.py
```

## Suggested live demo

1. **Guest longitudinal** — show 6 → 3 → 2 nights, service-use change and persistence.
2. **Evidence & hypotheses** — H3 rises but remains `Inferred`; neutral evidence is not convergence.
3. **Employee** — show understaffing/overtime/queue context before any individual-blame conclusion.
4. **Competitor** — enter own +0.2 vs competitor +0.6/+0.3/+0.4 and show RCG = −0.2.
5. **Decision & pilot** — owner chooses the reversible pilot; move through Verify/Test; record pilot outcome.
6. **Scenarios** — compare status quo vs selected vs one alternative across 0–1 / 1–3 / 3–5 / 5–10 years.

## Central contribution being tested

> SETDS separates confidence in a causal explanation from confidence in an intervention, and makes implementation permission contingent on action-specific verification and observed pilot outcomes rather than on causal confidence alone.
