MAGNITUDE_THRESHOLDS = {'guest':0.30,'operational':1.0,'employee':0.30,'competitor':0.10}
RED_FLAG_PERSISTENCE_THRESHOLD = 3

def classify(deviation_score: float, persistence_count: int,
             corroborating_source_types_count: int, impact_dimension: str,
             owner_priority_set: set[str] | None = None,
             hard_gate_triggered: bool = False, signal_type: str = 'operational',
             worsening: bool = False) -> str:
    if hard_gate_triggered:
        return 'CRITICAL'
    owner_priority_set = owner_priority_set or set()
    threshold = MAGNITUDE_THRESHOLDS.get(signal_type, 1.0)
    magnitude_ok = abs(deviation_score) >= threshold
    if not magnitude_ok and persistence_count < 2:
        return 'NONE'
    watch = magnitude_ok and persistence_count == 1
    warning = persistence_count >= 2 or (corroborating_source_types_count >= 2 and magnitude_ok) or (worsening and magnitude_ok)
    red_flag = persistence_count >= RED_FLAG_PERSISTENCE_THRESHOLD or (
        warning and impact_dimension in owner_priority_set and
        (corroborating_source_types_count >= 2 or worsening)
    )
    if red_flag: return 'RED_FLAG'
    if warning: return 'WARNING'
    if watch: return 'WATCH'
    return 'NONE'
