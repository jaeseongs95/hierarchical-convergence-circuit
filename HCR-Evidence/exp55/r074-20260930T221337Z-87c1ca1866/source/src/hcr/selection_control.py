"""R0.3.4의 순수 작업 선택 규칙. 공개 관측/정답 값조차 받지 않는 작은 제어 계약."""
from __future__ import annotations
from .selection import require


def choose_action(*,arm,ready,failed,frontier,candidate_id,native_accepted,
                  selection_accepted,checked,restarts,extra_advances,extra_ticks,
                  max_advances,max_ticks,tick_reservation):
    require(arm in ('hold','expand_only','restart_same','restart_route_only','select_only','expand_then_select','continue'), 'controller arm')
    require(all(type(x)is bool for x in (ready,failed,frontier,native_accepted,selection_accepted,checked)), 'controller flags')
    require(all(type(x)is int and x>=0 for x in (restarts,extra_advances,extra_ticks,max_advances,max_ticks,tick_reservation)), 'controller budgets')
    require(candidate_id is None or isinstance(candidate_id,str) and candidate_id, 'controller candidate identity')
    require(not ready or candidate_id is not None, 'ready without a captured native candidate')
    require(not selection_accepted or ready and candidate_id is not None, 'selection without a ready source')
    affordable=extra_advances<max_advances and extra_ticks+tick_reservation<=max_ticks
    if ready and native_accepted:return 'stop_supported_native'
    if selection_accepted:return 'stop_supported_selection'
    if arm=='hold':return 'stop_hold'
    if failed:return 'stop_engine_failure'
    if not ready:return 'advance' if affordable else 'stop_compute_budget'
    if arm in ('restart_same','restart_route_only'):
        return 'stop_restart_finished' if restarts else 'restart' if affordable else 'stop_compute_budget'
    if arm in ('select_only','expand_then_select') and not checked:return 'select_existing_proof'
    if arm=='select_only':return 'stop_no_supported_selection'
    if frontier:return 'continue_dependency' if affordable else 'stop_compute_budget'
    return 'stop_frontier_exhausted'
