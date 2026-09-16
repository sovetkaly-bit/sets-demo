from __future__ import annotations
HORIZONS=[('0–1 year','operational'),('1–3 years','tactical'),('3–5 years','strategic'),('5–10 years','foresight')]

def build_bounded_scenarios(status_quo: dict, selected: dict, alternative: dict | None=None):
    scenarios=[{'name':'Status quo','path':status_quo},{'name':'Selected path','path':selected}]
    if alternative is not None: scenarios.append({'name':'Alternative path','path':alternative})
    if len(scenarios)>3: raise AssertionError('Scenario branching must remain bounded to <=3 paths')
    return scenarios
