"""native 상태/원 proof/온라인 adoption을 독립 검산한다. 생산 OnlineTrial/run_policy 호출 없음."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import traceback
import json
from r037_online_selection import io
from .contracts import demand, digest
from .control_audit import audit_control

VIEW_FIELDS = ('observation', 'raw_value', 'state', 'completed_paths',
               'graph_complete', 'original_proof', 'min_abs_score')


def reachable(obs, truth) -> bool:
    """독립 평가용 reachability. 이 함수나 truth는 온라인 실행기에 전달되지 않는다."""
    seen = {obs['start']}
    changed = True
    while changed:
        changed = False
        for e in obs['edges']:
            if truth[e['id']] and e['source'] in seen and e['target'] not in seen:
                seen.add(e['target']); changed = True
    return obs['goal'] in seen


def information(view) -> dict:
    obs = view['observation']; threshold = view['min_abs_score']
    positive = {e['id']:e['score'] is not None and e['score'] > threshold for e in obs['edges']}
    possible = {e['id']:not(e['score'] is not None and e['score'] < -threshold) for e in obs['edges']}
    yes, maybe = reachable(obs, positive), reachable(obs, possible)
    return dict(identifiable=yes or not maybe, value=True if yes else False if not maybe else None,
                positive_support_path_exists=yes, possible_positive_path_exists=maybe)


def audit_native(run: dict, observation: dict, seed: dict, trial: dict, conditions: dict, case: dict) -> tuple:
    from hcr.prior_policy import read_scope
    from hcr.evaluation.review_audit import packet_states, verify_candidate
    from hcr.evaluation.selection_audit import source_view
    from r035_frozen_selection.audit import audit_result, view_check
    demand(run['backend'] == 'native_hcr' and run['scope'] == trial['scope'] and run['policy'] == trial['policy'],
           'native 실행 조건/종류')
    demand(run['scheduler']==trial['scheduler'],'scheduler trial binding')
    demand(run['budget'] == conditions['budget'], '사전 동결 계산 예산')
    packet = run['packet']; states, native_report = packet_states(packet)
    for c in states.values():
        demand(c['memory'] == seed['memory'] and c['config'] == seed['config'], '동결 memory/config 변경')
        demand(read_scope(c) == trial['scope'] and
               c['switches'] == dict(use_circuits=True, top_down=True, allow_reexpansion=True), 'prior/switches 변경')
        demand(not c['held'] and not c['feedback'] and not c['requests'], '학습/관측/native finish 덮어쓰기')
        if c['pending'] is not None:
            demand(c['pending']['observation'] == observation and c['pending']['mode'] == 'frozen_eval', '입력 provenance')
    demand(run['memory_sha256'] == digest(seed['memory']) and run['config_sha256'] == digest(seed['config']) and
           run['observation_sha256'] == digest(observation), 'trial 입력 hash')
    rows = []; selection_reports = []; candidate_reports = []
    demand(len(run['candidates']) == len(run['selections']), '선택 누락')
    for ordinal, (candidate, output) in enumerate(zip(run['candidates'], run['selections'])):
        demand(candidate['reference']['segment'] == 0, '다중 session 숨김')
        candidate_reports.append(verify_candidate(candidate, packet, states))
        raw = source_view(candidate)
        view = {k:deepcopy(raw[k]) for k in VIEW_FIELDS}; view['schema'] = 'hcr-frozen-proof-view-r035-v1'
        view_check(view)
        demand(output['limits'] == conditions['selection_limits'] and output['policy'] == trial['policy'], '선택 정책/예산')
        report = audit_result(view, output); selection_reports.append(report)
        if trial['policy'] == 'native_saved':
            demand(output['proof'] == view['original_proof'] and
                   output['accepted'] is candidate['readout']['accepted'] and
                   output['value'] is candidate['readout']['value'], 'native 저장 proof/gate 기준선 불일치')
        info = information(view)
        supported = [i for i,p in enumerate(view['completed_paths']) if
                     all(view['observation']['edges'][s]['score'] is not None and
                         view['observation']['edges'][s]['score'] > view['min_abs_score'] for s in p)]
        active = [i for i in supported if all(view['state'][f'e:{s}'] >= .5 for s in view['completed_paths'][i])]
        world_results = {name:dict(expected=reachable(observation, world),
                                  external_correct=None if output['value'] is None else
                                  output['value'] is reachable(observation, world))
                         for name, world in case['worlds'].items()}
        native_correct = {name:None if candidate['readout']['value'] is None else
                          candidate['readout']['value'] is result['expected'] for name,result in world_results.items()}
        rows.append(dict(trial_id=trial['id'], case=trial['case'], scope=trial['scope'], policy=trial['policy'],
            ordinal=ordinal, first_readout=ordinal == 0, last_available_readout=ordinal == len(run['candidates'])-1,
            native_view_sha256=digest(view), raw_value=view['raw_value'],
            native_accepted=candidate['readout']['accepted'], native_value=candidate['readout']['value'],
            policy_accepted=output['accepted'], policy_value=output['value'], policy_reason=output['reason'],
            D_DAG=report['D_DAG'], native_D_DAG=candidate['decision']['proof']['primitive_depth'],
            selected_assumptions=None if output['proof'] is None else output['proof']['assumed_edges'],
            native_assumptions=candidate['decision']['proof']['assumed_edges'],
            selected_path_index=output['selected_path_index'],
            completed_paths=view['completed_paths'], graph_complete=view['graph_complete'],
            supported_completed=supported, activation_eligible_supported=active, information=info,
            raw_conflicts_with_identified_value=info['identifiable'] and view['raw_value'] is not None and
                                               view['raw_value'] is not info['value'],
            recovered_same_value_output=not candidate['readout']['accepted'] and output['accepted'],
            kernel_ticks_at_readout=candidate['decision']['cost']['kernel_ticks'],
            native_proof_nodes=len(candidate['decision']['proof']['nodes']),
            convergence=candidate['decision'].get('convergence'), selection_usage=output['usage'],
            world_results=world_results, native_external_correct=native_correct))
    control_report = audit_control(run, states)
    # terminal packet 검산 비용/시간은 온라인 task 비용에 합산하지 않는다.
    final_truth = {name:dict(expected=reachable(observation, world),
                            external_correct=None if not run['adoption']['accepted'] else
                            run['adoption']['value'] is reachable(observation, world))
                   for name,world in case['worlds'].items()}
    return dict(native=native_report, controller=control_report, candidates=candidate_reports,
                selections=selection_reports, final_world_results=final_truth), rows

