"""기존 두 scheduler의 native/선택/스케줄링이 EXP21 raw와 같은지 검산한다.

R041/R040 외피 schema와 wall-clock 파생 봉인값은 달라도 된다.
경로, priority 전이, activation, 선택 결과와 각 비용은 그대로 대조한다.
"""
from copy import deepcopy
from r038_early_adoption.audit import candidate_view
from r038_early_adoption.metrics import semantic_events
from .contracts import BASELINE_SCHEDULERS, demand, digest


def _scheduler_decisions(base):
    result=[]
    for event in base['events']:
        if event['event']=='schedule_decided':
            # schema와 schema가 들어간 view hash만 버전 차이다. 다른 값은 모두 보존한다.
            result.append({k:deepcopy(v) for k,v in event['decision'].items()
                           if k not in ('schema','input_sha256')})
    return result


def _selectors(base):
    return [{k:v for k,v in s.items() if k!='wall_seconds'} for s in base['selections']]


def compare_parent(current,parent):
    old=parent['run'];a=current['base'];b=old['base'];policy=a['scheduler']
    demand(policy in BASELINE_SCHEDULERS and b['scheduler']==policy,
           'EXP21 대조는 같은 input_order/edge_id_min 조건이어야 합니다.')
    checks=dict(
        native_event_semantics_equal=semantic_events(a['packet']['document']['events'])==semantic_events(b['packet']['document']['events']),
        native_views_equal=[candidate_view(c) for c in a['candidates']]==[candidate_view(c) for c in b['candidates']],
        final_value_equal=(current['final']['value'],current['final']['accepted'],current['final']['reason'])==
                          (old['final']['value'],old['final']['accepted'],old['final']['reason']),
        native_and_selection_costs_equal=current['usage']==old['usage'],
        scheduler_decisions_equal=_scheduler_decisions(a)==_scheduler_decisions(b),
        scheduler_costs_equal=a['scheduler_usage']==b['scheduler_usage'],
        selector_outputs_equal=_selectors(a)==_selectors(b),
        posthoc_status_equal=current['posthoc_status']==old['posthoc_status'],
        posthoc_selection_equal=(None if current['posthoc_selection'] is None else
            {k:v for k,v in current['posthoc_selection'].items() if k!='wall_seconds'})==
            (None if old['posthoc_selection'] is None else
            {k:v for k,v in old['posthoc_selection'].items() if k!='wall_seconds'}))
    demand(all(checks.values()),'EXP21 원자료 회귀 불일치: '+','.join(k for k,v in checks.items() if not v))
    return dict(verified=True,**checks,parent_trial_id=parent['trial']['id'],
                scheduler=policy,wall_clock_hash_identity_required=False,
                wrapper_schema_versions_may_differ=True)
