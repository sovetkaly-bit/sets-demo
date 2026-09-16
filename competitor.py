from __future__ import annotations
import statistics

def relative_competitive_gap(own_delta: float, competitor_deltas: list[float]) -> dict:
    if not competitor_deltas: raise ValueError('At least one competitor delta is required')
    benchmark=statistics.median(competitor_deltas); gap=own_delta-benchmark
    return {'own_delta':own_delta,'benchmark_delta':benchmark,'gap':gap,'relative_erosion':gap<0}
