"""Signal classification, Eq. (2) of the SETDS manuscript (Section 5.3).

RED_FLAG iff  B_t = 1  and  P_t >= 2  and  S_t >= 2, where
  B_t  the current deviation crosses the adverse threshold,
  P_t  consecutive evaluable transitions ending at t that cross it,
  S_t  independent source types that corroborate the SAME observed signal.

Owner priority only orders the review queue (review_order_key); it never raises
S_t and never replaces corroboration.
"""
MAGNITUDE_THRESHOLDS = {'guest':0.30,'operational':1.0,'employee':0.30,'competitor':0.10}
# Direction in which a deviation is adverse. Guest stay length: only shortening counts (D <= -delta).
# Signal types not listed keep the earlier two-sided magnitude test.
ADVERSE_DIRECTION = {'guest':'down'}
RED_FLAG_MIN_PERSISTENCE = 2
RED_FLAG_MIN_SOURCE_TYPES = 2
SEVERITY_RANK = {'NONE':0,'WATCH':1,'WARNING':2,'RED_FLAG':3,'CRITICAL':4}
_EPS = 1e-9

def crosses_threshold(deviation_score: float, signal_type: str = 'operational') -> bool:
    threshold = MAGNITUDE_THRESHOLDS.get(signal_type, 1.0)
    if ADVERSE_DIRECTION.get(signal_type) == 'down':
        return deviation_score <= -threshold + _EPS
    return abs(deviation_score) >= threshold - _EPS

def classify(deviation_score: float, persistence_count: int,
             corroborating_source_types_count: int, impact_dimension: str,
             owner_priority_set: set[str] | None = None,
             hard_gate_triggered: bool = False, signal_type: str = 'operational',
             worsening: bool = False) -> str:
    # impact_dimension and owner_priority_set are accepted for compatibility; they do not change the status.
    if hard_gate_triggered:
        return 'CRITICAL'
    if not crosses_threshold(deviation_score, signal_type):
        return 'NONE'
    if persistence_count >= RED_FLAG_MIN_PERSISTENCE and corroborating_source_types_count >= RED_FLAG_MIN_SOURCE_TYPES:
        return 'RED_FLAG'
    # Threshold crossing without both persistence and corroboration stays WATCH/WARNING.
    if persistence_count >= RED_FLAG_MIN_PERSISTENCE or corroborating_source_types_count >= RED_FLAG_MIN_SOURCE_TYPES or worsening:
        return 'WARNING'
    return 'WATCH'

def review_order_key(status: str, impact_dimension: str, owner_priority_set: set[str] | None = None):
    """Sort key for the review queue: severity first, owner priority breaks ties. Never changes a status."""
    priority = 1 if impact_dimension in (owner_priority_set or set()) else 0
    return (-SEVERITY_RANK.get(status, 0), -priority)
