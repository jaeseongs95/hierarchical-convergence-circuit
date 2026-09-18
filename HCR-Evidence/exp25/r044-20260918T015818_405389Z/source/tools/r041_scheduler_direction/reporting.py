"""순열 불변성, 같은 결과의 계산 비용, 선택 시점을 별개의 축으로 집계한다."""
from collections import Counter
from copy import deepcopy
from itertools import combinations
import json
from r039_order_isolation.reporting import summarize as old_summarize
from r038_early_adoption.reporting import csv_text
from r040_frontier_schedule.reporting import computational_signature, trial_csv
from .contracts import ARMS,SCOPES,SCHEDULERS,SCHEDULE_USAGE,demand


def _outcome(record):
    return (record['final']['value'],record['final']['accepted'],record['classification'])


def summarize(records):
    demand(len(records)==108 and len({r['trial']['id'] for r in records})==108,'108개 단회 raw population')
    keys=[(r['trial']['scheduler'],r['trial']['case'],r['trial']['scope'],r['trial']['arm']) for r in records]
    demand(len(set(keys))==108 and {k[0] for k in keys}==set(SCHEDULERS),'중복/미등록 scheduler condition')
    summaries={};pairs=[];tables=[];effects=[];trials=[];readouts=[];decisions=[]
    for scheduler in SCHEDULERS:
        sub=[r for r in records if r['trial']['scheduler']==scheduler]
        demand(len(sub)==36,'scheduler별 36개 조건 필요')
        result=old_summarize(sub);summaries[scheduler]=result
        for name,target in (('paired',pairs),('tables',tables),('order_effects',effects),('trials',trials),('readout_rows',readouts)):
            target.extend(dict(scheduler=scheduler,**deepcopy(row)) for row in result[name])
        for e in effects:
            if e['scheduler']!=scheduler: continue
            group=[r for r in sub if r['trial']['scope']==e['scope'] and r['trial']['arm']==e['arm']]
            e['distinct_ID_aligned_trajectories']=len({computational_signature(r) for r in group})
            calls=[r['scheduler_usage']['priority_transitions'] for r in group]
            e.update(priority_transitions_min=min(calls),priority_transitions_max=max(calls),
                     event_seq_excluded_from_computational_signature=True)
    index=dict(zip(keys,records));byid={r['trial']['id']:r for r in records}
    for row in trials: row['scheduler_usage']=deepcopy(byid[row['trial_id']]['scheduler_usage'])
    contrasts=[]
    treatment_keys=sorted({(r['trial']['case'],r['trial']['scope'],r['trial']['arm']) for r in records})
    for left,right in combinations(SCHEDULERS,2):
        for case,scope,arm in treatment_keys:
            a,b=index[(left,case,scope,arm)],index[(right,case,scope,arm)]
            da,db=a['order_diagnostics'],b['order_diagnostics']
            ka=[r['selected_edge_ids'] for r in a['audit']['controller']['scheduler_choices']]
            kb=[r['selected_edge_ids'] for r in b['audit']['controller']['scheduler_choices']]
            divergence=next((i for i,(x,y) in enumerate(zip(ka,kb)) if x!=y),None)
            left_ticks=a['usage']['native_kernel_ticks'];right_ticks=b['usage']['native_kernel_ticks']
            contrasts.append(dict(case=case,branch_order=da['branch_order'],scope=scope,arm=arm,
                left_scheduler=left,right_scheduler=right,left_ticks=left_ticks,right_ticks=right_ticks,
                tick_difference_left_minus_right=left_ticks-right_ticks,
                same_final_outcome=_outcome(a)==_outcome(b),left_value=a['final']['value'],right_value=b['final']['value'],
                left_classification=a['classification'],right_classification=b['classification'],
                both_correct_in_declared_worlds=a['classification']==b['classification']=='correct_in_all_declared_worlds',
                first_scheduler_head_divergence_step=divergence,
                common_scheduler_steps=min(len(ka),len(kb)),scheduler_step_count_difference=len(ka)-len(kb),
                left_completion=json.dumps([x['path_edge_ids'] for x in da['completion_trace']]),
                right_completion=json.dumps([x['path_edge_ids'] for x in db['completion_trace']]),
                left_support_rank=da['support_route_completion_rank'],right_support_rank=db['support_route_completion_rank'],
                left_frontier=a['final_frontier_count'],right_frontier=b['final_frontier_count'],
                left_priority_transitions=a['scheduler_usage']['priority_transitions'],
                right_priority_transitions=b['scheduler_usage']['priority_transitions'],
                left_scheduler_edge_reads=a['scheduler_usage']['edge_id_reads'],right_scheduler_edge_reads=b['scheduler_usage']['edge_id_reads']))
    mediation=[];invariance=[]
    def effect(scheduler,scope,arm):
        return next(e for e in effects if (e['scheduler'],e['scope'],e['arm'])==(scheduler,scope,arm))
    for scope in SCOPES:
        for arm in ARMS:
            origin=effect('input_order',scope,arm)
            for fixed in SCHEDULERS[1:]:
                target=effect(fixed,scope,arm);old,new=origin['native_ticks_spread'],target['native_ticks_spread']
                same=all(c['same_final_outcome'] for c in contrasts if c['scope']==scope and c['arm']==arm
                         and c['left_scheduler']=='input_order' and c['right_scheduler']==fixed)
                finding=('no_input_order_tick_gap' if old==0 else 'tick_gap_removed' if new==0 else
                         'tick_gap_reduced' if new<old else 'tick_gap_not_reduced')
                mediation.append(dict(scope=scope,arm=arm,comparator=fixed,input_order_tick_spread=old,
                    fixed_tick_spread=new,tick_spread_reduction=old-new,
                    input_order_completion_orders=origin['distinct_completion_orders'],
                    fixed_completion_orders=target['distinct_completion_orders'],
                    input_order_trajectories=origin['distinct_ID_aligned_trajectories'],
                    fixed_trajectories=target['distinct_ID_aligned_trajectories'],
                    all_paired_final_outcomes_equal=same,finding=finding,
                    interpretation='controlled_scheduler_intervention; invariance_is_not_efficiency'))
            lo,hi=effect('edge_id_min',scope,arm),effect('edge_id_max',scope,arm)
            related=[c for c in contrasts if c['scope']==scope and c['arm']==arm and
                     c['left_scheduler']=='edge_id_min' and c['right_scheduler']=='edge_id_max']
            same=all(c['same_final_outcome'] for c in related)
            values={s:[index[(s,c,scope,arm)]['usage']['native_kernel_ticks'] for c in sorted({r['trial']['case'] for r in records})]
                    for s in ('edge_id_min','edge_id_max')}
            cost_gap=sum(values['edge_id_max'])-sum(values['edge_id_min'])
            ticks_invariant=lo['native_ticks_spread']==hi['native_ticks_spread']==0
            paths_invariant=lo['distinct_completion_orders']==hi['distinct_completion_orders']==1
            trajectories_invariant=lo['distinct_ID_aligned_trajectories']==hi['distinct_ID_aligned_trajectories']==1
            finding=('fixed_scheduler_tick_invariance_not_both_observed' if not ticks_invariant else
                     'invariant_but_final_outcomes_differ' if not same else
                     'invariant_same_outcome_equal_native_cost' if cost_gap==0 else
                     'invariant_same_outcome_different_native_cost')
            invariance.append(dict(scope=scope,arm=arm,permutations=6,
                min_tick_spread=lo['native_ticks_spread'],max_tick_spread=hi['native_ticks_spread'],
                both_native_tick_invariant=ticks_invariant,both_completion_order_invariant=paths_invariant,
                both_ID_aligned_trajectory_invariant=trajectories_invariant,
                all_paired_final_outcomes_equal=same,
                both_correct_in_declared_worlds=all(c['both_correct_in_declared_worlds'] for c in related),
                min_total_native_ticks=sum(values['edge_id_min']),max_total_native_ticks=sum(values['edge_id_max']),
                min_mean_native_ticks=sum(values['edge_id_min'])/6,max_mean_native_ticks=sum(values['edge_id_max'])/6,
                max_minus_min_total_native_ticks=cost_gap,
                max_is_more_expensive_pairs=sum(x>y for x,y in zip(values['edge_id_max'],values['edge_id_min'])),
                max_is_less_expensive_pairs=sum(x<y for x,y in zip(values['edge_id_max'],values['edge_id_min'])),
                equal_native_cost_pairs=sum(x==y for x,y in zip(values['edge_id_max'],values['edge_id_min'])),
                finding=finding,not_accuracy_or_total_runtime_superiority=True))
    for r in records:
        for step,row in enumerate(r['audit']['controller']['scheduler_choices']):
            decisions.append(dict(trial_id=r['trial']['id'],scheduler=r['trial']['scheduler'],
                branch_order=r['order_diagnostics']['branch_order'],scope=r['trial']['scope'],arm=r['trial']['arm'],
                step=step,before_generation=row['before_generation'],selected_index=row['selected_index'],
                selected_edge_ids=json.dumps(row['selected_edge_ids']),
                frontier_paths_edge_ids=json.dumps(row['frontier_paths_edge_ids']),reordered=row['reordered']))
    costs=dict(native_kernel_ticks=sum(r['usage']['native_kernel_ticks'] for r in records),
               native_finish_proof_nodes=sum(r['native_finish_proof_nodes'] for r in records),native_capture_scan_checks=None)
    for name in ('online_selection','posthoc_selection'):
        costs[name]={k:sum(r['usage'][name][k] for r in records) for k in records[0]['usage'][name]}
    costs['scheduler']={k:sum(r['scheduler_usage'][k] for r in records) for k in SCHEDULE_USAGE}
    return dict(schema='hcr-exp22-summary-v1',base_topologies=1,order_variants=6,scheduler_count=3,native_trials=len(records),
        native_readouts=sum(len(r['readouts']) for r in records),paired_trios=len(pairs),paired=pairs,tables=tables,
        order_effects=effects,trials=trials,readout_rows=readouts,scheduler_contrasts=contrasts,mediation=mediation,
        invariance_efficiency=invariance,scheduler_decisions=decisions,costs=costs,
        parent_regression_checked=sum(r['parent_regression'] is not None for r in records),
        findings=dict(Counter(p['finding'] for p in pairs)),
        interpretation=dict(single_topology_not_108_independent_problems=True,
            priority_is_declared_intervention_not_ID_correction=True,cost_units_not_added=True,
            invariant_is_not_efficient=True,ID_extrema_not_learned_or_optimal_policy=True,
            ticks_gap_reduction_not_total_runtime_claim=True,first_pool_policy_not_modified=True,
            direction_or_improvement_not_required_for_audit=True))


def render(s):
    lines=['# EXP-22 / R0.4.1 — 순열 불변성과 계산 효율의 분리','',
        f"동일 topology 1 / 입력 순열 6 / scheduler 3 / native 실행 {s['native_trials']} / readout {s['native_readouts']}",
        'input_order: 기존 head, edge_id_min: ID 경로 최소값, edge_id_max: ID 경로 최대값.',
        '입력·ID·관측·world·memory를 바꾸지 않고, 이미 생성된 frontier head만 공개 API로 이동한다.',
        'S/M/D와 score·raw·정답을 scheduler에 주지 않는다. 첫 후보 pool은 변경하지 않는다.','',
        '## 최종 채택','',
        '| scheduler / prior / arm | 조건 | 정답 | 오답 | 보류 | native ticks |','|---|---:|---:|---:|---:|---:|']
    for r in s['tables']:
        lines.append(f"| {r['scheduler']}/{r['scope']}/{r['arm']} | {r['trials']} | {r['correct']} | {r['incorrect']} | {r['abstained']} | {r['native_ticks']} |")
    lines+=['','## 불변성과 효율','',
        '| prior / arm | min/max ticks 범위 폭 | 두 고정 정책의 결과 일치 | min/max 평균 ticks | max−min 합계 | 관찰 |',
        '|---|---|---|---|---:|---|']
    for r in s['invariance_efficiency']:
        lines.append(f"| {r['scope']}/{r['arm']} | {r['min_tick_spread']}/{r['max_tick_spread']} | {r['all_paired_final_outcomes_equal']} | {r['min_mean_native_ticks']:.2f}/{r['max_mean_native_ticks']:.2f} | {r['max_minus_min_total_native_ticks']} | {r['finding']} |")
    lines+=['','범위 폭 0은 이 여섯 순열의 비용 불변성이다. 적은 평균 비용·정확도·수렴 안정성과 동일하지 않다.',
        'max−min은 같은 조건의 native ticks 차이이며 양수는 max 쪽이 더 많이 계산했다는 뜻이다.','',
        '## 기존 배열 의존 격차와 고정 scheduler','',
        '| prior / arm / 고정 정책 | 기존/고정 ticks 범위 폭 | 기존/고정 경로순서 종류 | 결과 유지 | 관찰 |',
        '|---|---|---|---|---|']
    for r in s['mediation']:
        lines.append(f"| {r['scope']}/{r['arm']}/{r['comparator']} | {r['input_order_tick_spread']}/{r['fixed_tick_spread']} | {r['input_order_completion_orders']}/{r['fixed_completion_orders']} | {r['all_paired_final_outcomes_equal']} | {r['finding']} |")
    lines+=['','## 온라인 선택 시점','',
        '| scheduler / 순서 / prior | native / 사후 / 온라인 ticks | 차등 기회 | 사후−온라인 | 판정 |',
        '|---|---:|---|---:|---|']
    for r in s['paired']:
        lines.append(f"| {r['scheduler']}/{r['branch_order']}/{r['scope']} | {r['native_ticks']}/{r['posthoc_ticks']}/{r['online_ticks']} | {r['differential_opportunity']} | {r['saved_native_ticks']} | {r['finding']} |")
    lines+=['','## 비용·원자료·주장 범위','',
        f"EXP21 원 raw와 일치한 기존 input_order/edge_id_min 대조: {s['parent_regression_checked']}개.",
        f"전체 native ticks: {s['costs']['native_kernel_ticks']}",
        f"Native finish proof nodes: {s['costs']['native_finish_proof_nodes']}",
        f"Scheduler inventory: {s['costs']['scheduler']}",
        f"온라인 selector: {s['costs']['online_selection']}",f"사후 selector: {s['costs']['posthoc_selection']}",
        '여기서 원인 분리는 고정 ID의 최소/최대 우선순위와 계산 결과의 관계에 한정한다.',
        '두 ID 방향 모두 최적/학습된 정책이 아니다. 불변하지만 더 느린 결과도 유효한 실험 결과다.',
        'min/max의 의미적 유불리를 미리 판정해 경로나 결과를 수정하지 않는다.',
        '순서 효과·성능·예측에 맞는 방향은 audit 통과 조건이 아니다. 오답/보류/비용 증가도 보존한다.',
        'Native ticks, 스케줄러 검사, selector/proof 생성 비용은 서로 다른 단위다. 합산하지 않는다.',
        '미계측 native capture scan은 null이다. priority_match_scans는 모든 CPU 연산/시간을 뜻하지 않는다.',
        '순열·prior·arm·scheduler·world·readout을 108개 독립 문제로 세지 않는다.',
        '원 native 판단과 terminal adoption을 구분하고, raw 값 반전·관측 추가·학습·자동 retry를 하지 않는다.',
        'D_DAG는 기록하지만 이 실험은 D축 조작이 아니다. 인간/LLM 내부 회로의 실증이 아니다.',
        '계산 궤적 비교에서는 priority bookkeeping event_seq만 제외한다. 원문 event와 참조는 그대로 보존한다.','']
    return '\n'.join(lines)
