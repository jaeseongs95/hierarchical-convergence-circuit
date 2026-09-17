"""input_order 대조가 EXP20 원자료의 native 계산을 보존했는지 확인한다."""
from r038_early_adoption.audit import candidate_view
from r038_early_adoption.metrics import semantic_events
from .contracts import demand, digest


def compare_parent(current,parent):
    old=parent['run'];a=current['base'];b=old['base']
    demand(a['scheduler']=='input_order','parent comparison is input_order only')
    same_events=digest(semantic_events(a['packet']['document']['events']))==digest(semantic_events(b['packet']['document']['events']))
    same_views=[candidate_view(c) for c in a['candidates']]==[candidate_view(c) for c in b['candidates']]
    # wall-clock에서 파생된 candidate hash는 비교 기준으로 사용하지 않는다.
    same_value=(current['final']['value'],current['final']['accepted'])==(old['final']['value'],old['final']['accepted'])
    same_usage=current['usage']==old['usage']
    demand(same_events and same_views and same_value and same_usage,'EXP20 기준 native trace/view/value/cost 회귀 불일치')
    return dict(verified=True,native_event_semantics_equal=same_events,native_views_equal=same_views,
                final_value_equal=same_value,native_and_selection_costs_equal=same_usage,
                parent_trial_id=parent['trial']['id'],wall_clock_hash_identity_required=False)
