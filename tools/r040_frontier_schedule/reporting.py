"""scheduler 내부 채택 비교와 scheduler 사이의 순서 민감도 비교를 분리한다."""
from collections import Counter
from copy import deepcopy
import json
from r039_order_isolation.reporting import summarize as old_summarize
from r038_early_adoption.reporting import csv_text
from .contracts import ARMS,SCOPES,SCHEDULERS,SCHEDULE_USAGE,demand,digest


def computational_signature(record):
    """priority의 기록 event 번호는 제거하되 계산 단계/경로/activation/ticks는 유지한다."""
    d=record['order_diagnostics']
    completion=[{k:x[k] for k in ('rank','expansion','path_edge_ids')} for x in d['completion_trace']]
    return digest(dict(completion=completion,readouts=d['readouts']))


def summarize(records):
    demand(len(records)==72 and len({r['trial']['id'] for r in records})==72,'72개 단회 raw population')
    summaries={};all_pairs=[];tables=[];effects=[];trials=[];readouts=[];decisions=[]
    for scheduler in SCHEDULERS:
        sub=[r for r in records if r['trial']['scheduler']==scheduler]
        demand(len(sub)==36,'scheduler별 36개 native 조건 필요')
        result=old_summarize(sub);summaries[scheduler]=result
        for name,target in (('paired',all_pairs),('tables',tables),('order_effects',effects),('trials',trials),('readout_rows',readouts)):
            target.extend(dict(scheduler=scheduler,**deepcopy(row)) for row in result[name])
        for e in effects:
            if e['scheduler']!=scheduler:continue
            group=[r for r in sub if r['trial']['scope']==e['scope'] and r['trial']['arm']==e['arm']]
            e['distinct_ID_aligned_trajectories']=len({computational_signature(r) for r in group})
            calls=[r['scheduler_usage']['priority_transitions'] for r in group]
            e.update(priority_transitions_min=min(calls),priority_transitions_max=max(calls),
                     event_seq_excluded_from_computational_signature=True)
    index={(r['trial']['scheduler'],r['trial']['case'],r['trial']['scope'],r['trial']['arm']):r for r in records}
    byid={r['trial']['id']:r for r in records}
    for row in trials: row['scheduler_usage']=deepcopy(byid[row['trial_id']]['scheduler_usage'])
    contrasts=[]
    for case,scope,arm in sorted({(r['trial']['case'],r['trial']['scope'],r['trial']['arm']) for r in records}):
        a,b=[index[(s,case,scope,arm)] for s in SCHEDULERS]
        da,db=a['order_diagnostics'],b['order_diagnostics']
        ka=[r['selected_edge_ids'] for r in a['audit']['controller']['scheduler_choices']]
        kb=[r['selected_edge_ids'] for r in b['audit']['controller']['scheduler_choices']]
        divergence=next((i for i,(x,y) in enumerate(zip(ka,kb)) if x!=y),None)
        same=(a['final']['value'],a['classification'])==(b['final']['value'],b['classification'])
        contrasts.append(dict(case=case,branch_order=da['branch_order'],scope=scope,arm=arm,
            input_order_ticks=a['usage']['native_kernel_ticks'],edge_id_min_ticks=b['usage']['native_kernel_ticks'],
            native_tick_difference=a['usage']['native_kernel_ticks']-b['usage']['native_kernel_ticks'],
            input_order_value=a['final']['value'],edge_id_min_value=b['final']['value'],
            input_order_classification=a['classification'],edge_id_min_classification=b['classification'],
            same_final_outcome=same,first_scheduler_head_divergence_step=divergence,
            input_order_completion=json.dumps([x['path_edge_ids'] for x in da['completion_trace']]),
            edge_id_min_completion=json.dumps([x['path_edge_ids'] for x in db['completion_trace']]),
            input_order_support_rank=da['support_route_completion_rank'],edge_id_min_support_rank=db['support_route_completion_rank'],
            input_order_frontier=a['final_frontier_count'],edge_id_min_frontier=b['final_frontier_count'],
            edge_id_min_priority_transitions=b['scheduler_usage']['priority_transitions'],
            input_order_scheduler_edge_reads=a['scheduler_usage']['edge_id_reads'],
            edge_id_min_scheduler_edge_reads=b['scheduler_usage']['edge_id_reads']))
    mediation=[]
    for scope in SCOPES:
        for arm in ARMS:
            a,b=[next(e for e in effects if (e['scheduler'],e['scope'],e['arm'])==(s,scope,arm)) for s in SCHEDULERS]
            old,new=a['native_ticks_spread'],b['native_ticks_spread']
            same=all(c['same_final_outcome'] for c in contrasts if c['scope']==scope and c['arm']==arm)
            finding=('no_input_order_tick_gap' if old==0 else 'tick_gap_removed' if new==0 else
                     'tick_gap_reduced' if new<old else 'tick_gap_not_reduced')
            mediation.append(dict(scope=scope,arm=arm,input_order_tick_spread=old,edge_id_min_tick_spread=new,
                tick_spread_reduction=old-new,input_order_completion_orders=a['distinct_completion_orders'],
                edge_id_min_completion_orders=b['distinct_completion_orders'],
                input_order_trajectories=a['distinct_ID_aligned_trajectories'],
                edge_id_min_trajectories=b['distinct_ID_aligned_trajectories'],
                all_paired_final_outcomes_equal=same,finding=finding,
                interpretation='controlled_scheduler_intervention; not_complete_causal_mediation_proof'))
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
    return dict(schema='hcr-exp21-summary-v1',base_topologies=1,order_variants=6,native_trials=len(records),
        native_readouts=sum(len(r['readouts']) for r in records),paired_trios=len(all_pairs),paired=all_pairs,
        tables=tables,order_effects=effects,trials=trials,readout_rows=readouts,scheduler_contrasts=contrasts,
        mediation=mediation,scheduler_decisions=decisions,costs=costs,
        parent_regression_checked=sum(r['parent_regression'] is not None for r in records),
        findings=dict(Counter(p['finding'] for p in all_pairs)),
        interpretation=dict(single_topology_not_72_independent_problems=True,
            priority_is_declared_intervention_not_ID_correction=True,cost_units_not_added=True,
            ticks_gap_reduction_not_total_runtime_claim=True,ID_min_not_optimal_policy=True,
            first_pool_policy_not_modified=True,gap_reduction_not_required_for_audit=True))


def trial_csv(rows):
    flattened=[]
    for r in rows:
        row={k:v for k,v in r.items() if k not in ('usage','final_assumption_counts','scheduler_usage')}
        for k in ('assumptions_checked','supported_assumptions','unsupported_assumptions'):
            row[k]=None if r['final_assumption_counts'] is None else r['final_assumption_counts'][k]
        for section in ('online_selection','posthoc_selection'):
            row.update({section+'_'+k:v for k,v in r['usage'][section].items()})
        row.update({'scheduler_'+k:v for k,v in r['scheduler_usage'].items()})
        flattened.append(row)
    return csv_text(flattened)


def render(s):
    lines=['# EXP-21 / R0.4.0 — frontier scheduling 개입','',
        f"동일 topology 1 / 입력 순열 6 / scheduler 2 / native 실행 {s['native_trials']} / readout {s['native_readouts']}",
        'input_order는 기존 삽입 순서, edge_id_min은 이미 등록된 frontier 중 edge-ID 경로 tuple 최소값을 선택한다.',
        '입력 자체를 정렬하지 않고 공개 prioritize_frontier API만 호출한다. score/world/raw를 scheduler에 주지 않는다.',
        '전체 frontier를 미리 정렬하거나 첫 후보 pool 정책을 변경한 실험이 아니다.','',
        '## 최종 채택','',
        '| scheduler / prior / arm | 조건 | 정답 | 오답 | 보류 | native ticks |',
        '|---|---:|---:|---:|---:|---:|']
    for r in s['tables']:
        lines.append(f"| {r['scheduler']}/{r['scope']}/{r['arm']} | {r['trials']} | {r['correct']} | {r['incorrect']} | {r['abstained']} | {r['native_ticks']} |")
    lines+=['','## 순열 사이의 격차','',
        '| prior / arm | 기존 ticks 범위 폭 | ID-min ticks 범위 폭 | 기존/ID-min 경로순서 종류 | 최종 결과 유지 | 관찰 |',
        '|---|---:|---:|---|---|---|']
    for r in s['mediation']:
        lines.append(f"| {r['scope']}/{r['arm']} | {r['input_order_tick_spread']} | {r['edge_id_min_tick_spread']} | {r['input_order_completion_orders']}/{r['edge_id_min_completion_orders']} | {r['all_paired_final_outcomes_equal']} | {r['finding']} |")
    lines+=['','## 같은 scheduler 안의 온라인/사후 선택 비교','',
        '| scheduler / 순서 / prior | native / 사후 / 온라인 ticks | 차등 기회 | 사후−온라인 | 판정 |',
        '|---|---:|---|---:|---|']
    for r in s['paired']:
        lines.append(f"| {r['scheduler']}/{r['branch_order']}/{r['scope']} | {r['native_ticks']}/{r['posthoc_ticks']}/{r['online_ticks']} | {r['differential_opportunity']} | {r['saved_native_ticks']} | {r['finding']} |")
    lines+=['','## 비용·정합성·주장 범위','',
        f"EXP20 원 raw와 일치한 input_order 대조: {s['parent_regression_checked']}개.",
        f"전체 native ticks: {s['costs']['native_kernel_ticks']}",
        f"Native finish proof nodes: {s['costs']['native_finish_proof_nodes']}",
        f"Scheduler inventory: {s['costs']['scheduler']}",
        f"온라인 selector: {s['costs']['online_selection']}",f"사후 selector: {s['costs']['posthoc_selection']}",
        'Scheduler 검사/비교/native priority scan은 별도 inventory 단위이다. native ticks에 더하지 않는다.',
        'priority_match_scans는 기존 API의 경로 일치 검사 횟수이며 딥카피·직렬화·모든 CPU 연산을 포괄하지 않는다.',
        'ID 정렬이 이 고정 문제에서 지지 경로를 앞세워도 최적/학습된 탐색 정책으로 해석하지 않는다.',
        '격차 감소/소실은 이 개입 범위의 원인 분리를 지지한다. 남은 pool/slot/수치 효과까지 제거했다고 단정하지 않는다.',
        '배열 순서 효과 없음, 보류, 오답, 개선 없음도 보존한다. audit 통과 조건은 계약/원자료/독립 재생의 일치이다.',
        '입력 identity와 관측을 고정하며 새 학습·관측 요청·raw 값 반전·자동 retry는 하지 않는다.',
        '미계측 비용은 null이다. 전력/전체 실행시간 절감, D축 검증, 인간/LLM 내부 회로 검증을 주장하지 않는다.',
        'order_effects의 계산 궤적은 priority로 달라진 event_seq를 제외하지만 경로/expansion/activation/ticks를 보존한다.',
        '개별 priority 원자료와 generation 참조는 records 및 scheduler_decisions.csv에 보존한다.','']
    return '\n'.join(lines)
