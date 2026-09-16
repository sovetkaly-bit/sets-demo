from __future__ import annotations

VALID_PROVENANCE = {
    'Observed','Guest-reported','Employee-reported','Owner-entered',
    'Public-source','Derived','Illustrative','Pilot-derived','Model-estimated',
}
VALID_EFFECTS = {'supports','refutes','neutral'}
VALID_SIGNAL_RELATIONS = {'corroborates','contradicts','context'}

EVIDENCE_TYPE_CATEGORY = {
    'targeted_question_confirms':'guest_feedback',
    'targeted_question_refutes':'guest_feedback',
    'targeted_question_no_answer':'guest_feedback',
    'guest_rating_change':'guest_behavior',
    'guest_service_usage_change':'guest_behavior',
    'guest_los_change':'guest_behavior',
    'guest_revisit_interval_change':'guest_behavior',
    'operational_data_confirms':'operational_log',
    'employee_data_confirms':'employee_data',
    'shift_workload_data':'employee_data',
    'shift_staffing_data':'employee_data',
    'supervisor_observation':'employee_data',
    'competitor_signal_aligned':'competitor_data',
    'competitor_signal_unrelated':'competitor_data',
    'public_competitor_observation':'competitor_data',
}

class UnknownEvidenceTypeError(ValueError):
    pass

def evidence_category(evidence_type: str) -> str:
    try:
        return EVIDENCE_TYPE_CATEGORY[evidence_type]
    except KeyError as e:
        raise UnknownEvidenceTypeError(f'Unknown evidence_type={evidence_type!r}; register it explicitly.') from e

def validate_provenance(provenance: str) -> None:
    if provenance not in VALID_PROVENANCE:
        raise ValueError(f'Invalid provenance={provenance!r}')

def validate_effect(effect: str) -> None:
    if effect not in VALID_EFFECTS:
        raise ValueError(f'Invalid effect={effect!r}')

def validate_signal_relation(relation: str) -> None:
    if relation not in VALID_SIGNAL_RELATIONS:
        raise ValueError(f'Invalid signal relation={relation!r}')
