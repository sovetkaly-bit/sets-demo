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
python tests.py        # rule modules: Eq. (2), Section 6, Eq. (7) and the earlier v8 checks
python tests_ui.py     # headless Streamlit AppTest: Scenario A and the implementation-admission path
python seed_demo.py
streamlit run app.py
```

## Rules aligned with the manuscript

- **Eq. (2) red flag.** `RED_FLAG` only when the current deviation reaches the negative threshold (guest stay: D ≤ −30%), **and** P ≥ 2 consecutive negative transitions, **and** S ≥ 2 independent source types confirming the *same observed signal*. S counts source types of the signal (PMS stay records are one type); a guest comment or a staff log about the *cause* is evidence for a hypothesis and does not raise S. Owner priority only changes review order (`signals.review_queue`); it never raises S and never substitutes for corroboration. Scenario A (6 → 3 → 2 nights) gives P = 2, S = 1 → `WARNING`, with or without owner priority.
- **Section 6 episodes.** `apply_evidence(..., episode_id=...)` keys evidence by episode (without `episode_id`, by evidence type + source reference). A hypothesis receives the multiplier of one episode once; a second record of the same episode, or the same record resubmitted, is logged with `applied = 0` and leaves the posterior unchanged. Independent episodes count separately: with the Scenario A multipliers H3 = 0.50 after one episode and ≈ 0.667 after two independent ones, in either order.
- **Eq. (7) implementation.** `Implement` requires an explicit Critical Gate = `PASS` (recorded by a named human with a basis, `verification.set_critical_gate`) **and** a pilot outcome `validated`. A missing Gate is not a pass. The earlier low-risk fast-track (`Owner_selected → Implement`) is removed, and `no_action` is an observation that is never implemented. The Streamlit page "Анализ → Допуск к внедрению" calls the same functions and shows the block reason.
- Eq. (4)–(6) remain the manuscript's computational part and are not implemented in this prototype.
- Existing databases are migrated on start (`database.init_schema` adds the new columns).

## Suggested live demo

1. **Guest longitudinal** — show 6 → 3 → 2 nights, service-use change and persistence.
2. **Evidence & hypotheses** — H3 rises but remains `Inferred`; neutral evidence is not convergence.
3. **Employee** — show understaffing/overtime/queue context before any individual-blame conclusion.
4. **Competitor** — enter own +0.2 vs competitor +0.6/+0.3/+0.4 and show RCG = −0.2.
5. **Decision & pilot** — owner chooses the reversible pilot; move through Verify/Test; record pilot outcome.
6. **Scenarios** — compare status quo vs selected vs one alternative across 0–1 / 1–3 / 3–5 / 5–10 years.

## Central contribution being tested

> SETDS separates confidence in a causal explanation from confidence in an intervention, and makes implementation permission contingent on action-specific verification and observed pilot outcomes rather than on causal confidence alone.
