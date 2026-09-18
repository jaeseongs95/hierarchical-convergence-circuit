"""enabled/identity 6조건은 EXP22와 같은 실행을 유지해야 한다. input_order의 동일 입력 회귀만 검사한다."""
from copy import deepcopy
from .storage import require


def _decisions(base):
    return [{k:deepcopy(v) for k,v in event['decision'].items() if k not in ('schema','input_sha256')}
            for event in base['events'] if event['event'] == 'schedule_decided']


def _selections(base):
    return [{k:v for k,v in s.items() if k != 'wall_seconds'} for s in base['selections']]


def compare(current: dict, parent: dict) -> dict:
    from r041_scheduler_direction.trial_audit import candidate_view
    from r038_early_adoption.metrics import semantic_events
    old = parent['run']; a, b = current['base'], old['base']
    require(a['scheduler'] == b['scheduler'] and a['scheduler'] == 'input_order', 'EXP22 동일 scheduler 회귀')
    checks = dict(
        native_event_semantics_equal=semantic_events(a['packet']['document']['events']) == semantic_events(b['packet']['document']['events']),
        native_views_equal=[candidate_view(c) for c in a['candidates']] == [candidate_view(c) for c in b['candidates']],
        outcome_equal=tuple(current['final'][k] for k in ('value','accepted','reason')) == tuple(old['final'][k] for k in ('value','accepted','reason')),
        native_and_selection_usage_equal=current['usage'] == old['usage'],
        scheduler_decisions_equal=_decisions(a) == _decisions(b),
        scheduler_usage_equal=a['scheduler_usage'] == b['scheduler_usage'],
        selector_outputs_equal=_selections(a) == _selections(b),
        no_posthoc=current['posthoc_status'] == old['posthoc_status'] == 'not_applicable' and
                   current['posthoc_selection'] is old['posthoc_selection'] is None)
    require(all(checks.values()), 'EXP22 identity 회귀 불일치: '+','.join(k for k,v in checks.items() if not v))
    return dict(verified=True, checks=checks, parent_trial_id=parent['trial']['id'],
                wall_clock_identity_required=False, research_effect_required=False)
