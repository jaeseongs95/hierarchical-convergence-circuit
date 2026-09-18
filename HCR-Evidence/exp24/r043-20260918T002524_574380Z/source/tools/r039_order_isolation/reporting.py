"""순열 간 ID 기반 경로/시점 차이와, 순열 내부 온라인/사후 비교를 분리한다."""
from collections import defaultdict, Counter
import json
from r038_early_adoption.reporting import compare_trio, csv_text, trial_csv
from .contracts import ARMS,SCOPES,demand,digest


def summarize(records):
    groups=defaultdict(dict)
    for r in records:
        key=(r['trial']['case'],r['trial']['scope']);arm=r['trial']['arm']
        demand(arm not in groups[key],'중복 trial/arm')
        groups[key][arm]=r
    demand(len(groups)==12 and all(set(g)==set(ARMS) for g in groups.values()),'36개 동결 실행/trio 누락')
    pairs=[compare_trio(groups[k]) for k in sorted(groups)]
    bycase={ (p['case'],p['scope']):p for p in pairs }
    for key,g in groups.items():
        p=bycase[key];native=g['native'];online=g['online_support']
        diag=native['order_diagnostics'];first=diag['first_differential_readout']
        p.update(branch_order=diag['branch_order'],support_route_completion_rank=diag['support_route_completion_rank'],
            first_supported_readout_ticks=None if diag['first_supported_available_readout'] is None else diag['first_supported_available_readout']['ticks'],
            first_differential_ticks=None if first is None else first['ticks'],
            remaining_native_ticks_after_first_differential=None if first is None else p['native_ticks']-first['ticks'],
            online_stopped_at_first_differential=None if first is None else online['final']['accepted'] and p['online_ticks']==first['ticks'])
    tables=[];effects=[]
    for scope in SCOPES:
        for arm in ARMS:
            sub=[r for r in records if r['trial']['scope']==scope and r['trial']['arm']==arm]
            count=Counter(r['classification'] for r in sub)
            tables.append(dict(scope=scope,arm=arm,trials=len(sub),correct=count['correct_in_all_declared_worlds'],
                incorrect=count['incorrect_in_some_declared_world'],abstained=count['abstained'],
                native_ticks=sum(r['usage']['native_kernel_ticks'] for r in sub)))
            ticks=[r['usage']['native_kernel_ticks'] for r in sub]
            def token(r):
                d=r['order_diagnostics']
                return digest(dict(completion=d['completion_trace'],readouts=d['readouts']))
            outcomes={(r['final']['value'],r['classification']) for r in sub}
            path_orders={json.dumps([x['path_edge_ids'] for x in r['order_diagnostics']['completion_trace']]) for r in sub}
            effects.append(dict(scope=scope,arm=arm,permutations=len(sub),native_ticks_min=min(ticks),
                native_ticks_max=max(ticks),native_ticks_spread=max(ticks)-min(ticks),
                distinct_completion_orders=len(path_orders),distinct_ID_aligned_trajectories=len({token(r) for r in sub}),
                final_outcome_invariant=len(outcomes)==1,
                native_tick_order_effect_observed=len(set(ticks))>1,
                support_completion_ranks=json.dumps([r['order_diagnostics']['support_route_completion_rank'] for r in sub]),
                claims_ID_irrelevance=False))
    costs=dict(native_kernel_ticks=sum(r['usage']['native_kernel_ticks'] for r in records),
        native_finish_proof_nodes=sum(r['native_finish_proof_nodes'] for r in records),native_capture_scan_checks=None)
    for section in ('online_selection','posthoc_selection'):
        keys=records[0]['usage'][section]
        costs[section]={k:sum(r['usage'][section][k] for r in records) for k in keys}
    compact=[];readout_rows=[]
    for r in records:
        d=r['order_diagnostics']
        compact.append(dict(trial_id=r['trial']['id'],case=r['trial']['case'],scope=r['trial']['scope'],arm=r['trial']['arm'],
            branch_order=d['branch_order'],value=r['final']['value'],accepted=r['final']['accepted'],classification=r['classification'],
            reason=r['final']['reason'],native_ticks=r['usage']['native_kernel_ticks'],
            frontier_count=r['final_frontier_count'],readouts=len(r['readouts']),terminal_pending_ready=r['terminal_pending_ready'],
            final_assumption_counts=r['final_assumption_counts'],usage=r['usage']))
        for row in d['readouts']:
            readout_rows.append(dict(trial_id=r['trial']['id'],scope=r['trial']['scope'],arm=r['trial']['arm'],branch_order=d['branch_order'],
                ordinal=row['ordinal'],native_ticks=row['ticks'],raw_value=row['raw_value'],native_accepted=row['native_accepted'],
                policy_accepted=row['policy_accepted'],native_D_DAG=row['native_D_DAG'],policy_D_DAG=row['policy_D_DAG'],
                frontier_count=row['frontier_count'],differential_opportunity=row['differential_opportunity'],
                completed_paths_edge_ids=json.dumps(row['completed_paths_edge_ids']),
                supported_completed_edge_ids=json.dumps(row['supported_completed_edge_ids'])))
    return dict(schema='hcr-exp20-summary-v1',base_topologies=1,order_variants=6,native_trials=len(records),
        native_readouts=sum(len(r['readouts']) for r in records),paired_trios=len(pairs),paired=pairs,tables=tables,
        costs=costs,trials=compact,readout_rows=readout_rows,order_effects=effects,
        findings=dict(Counter(p['finding'] for p in pairs)),
        interpretation=dict(six_orders_are_not_six_independent_problems=True,ID_effect_not_manipulated=True,
            order_effect_not_required_to_pass_audit=True,not_a_D_axis_sweep=True,
            immutable_raw_and_evaluator_only_ID_alignment=True,cost_units_not_added=True))


def render(s):
    lines=['# EXP-20 / R0.3.9 — identity 고정 · 배열 순서 단독 조작','',
        f"기준 topology 1 / 순열 6 / native 실행 {s['native_trials']} / 실제 readout {s['native_readouts']}",
        'S=지지 가지(e0,e1), M=관측 누락 가지(e2,e3), D=음의 관측 포함 가지(e4,e5,e6).',
        '모든 node/edge/episode ID, 관계, score, world, memory, config를 고정하고 분기 블록 배열만 바꿨다.',
        'observation digest와 내부 slot 번호는 순서에 따라 자연스럽게 달라진다. 이를 host가 고치지 않았다.','',
        '## 최종 결과','', '| prior / arm | 조건 수 | 정답 | 오답 | 보류 | native ticks |', '|---|---:|---:|---:|---:|---:|']
    for r in s['tables']:
        lines.append(f"| {r['scope']}/{r['arm']} | {r['trials']} | {r['correct']} | {r['incorrect']} | {r['abstained']} | {r['native_ticks']} |")
    lines+=['','정답은 모든 선언 world에서 정답이라는 뜻이다. Audit 통과 자체는 정답을 의미하지 않는다.','',
        '## 순열 내부 paired 비교','',
        '| 순서 / prior | 지지 경로 완성 순위(native) | 차등 기회 tick | native / 사후 / 온라인 ticks | 절감 ticks | 온라인 frontier | 판정 |',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in s['paired']:
        lines.append(f"| {r['branch_order']}/{r['scope']} | {r['support_route_completion_rank']} | {r['first_differential_ticks']} | {r['native_ticks']}/{r['posthoc_ticks']}/{r['online_ticks']} | {r['saved_native_ticks']} | {r['online_final_frontier']} | {r['finding']} |")
    lines+=['','차등 기회: raw True + activation 적격 완성 지지 경로 + 남은 frontier + native 보류.',
        '절감 = 사후군 native ticks − 온라인군 native ticks. 같은 정답, prefix, 기준 trace 정합성을 함께 본다.',
        '기회가 없으면 조기 종료를 판별하지 못한 결과이다. 효과 없음/오답/보류도 삭제하지 않는다.','',
        '## 배열 순서 효과','', '| prior / arm | ticks 최소~최대 | 전개 순서 종류 | 최종 결과 불변 | ticks 차이 관찰 |',
        '|---|---:|---:|---|---|']
    for r in s['order_effects']:
        lines.append(f"| {r['scope']}/{r['arm']} | {r['native_ticks_min']}~{r['native_ticks_max']} | {r['distinct_completion_orders']} | {r['final_outcome_invariant']} | {r['native_tick_order_effect_observed']} |")
    lines+=['','ID가 고정된 조건에서 차이가 생기면 이번 범위의 배열 순서 효과다. ID가 무관하다거나 ID 효과의 크기를 측정했다는 뜻은 아니다.',
        '모든 순열이 같아도 검증 실패가 아니다. 최종 결과 불변과 중간 경로/시점 불변은 분리한다.','',
        '## 비용·출처·주장 범위','',f"전체 native ticks: {s['costs']['native_kernel_ticks']}",
        f"원 native finish proof nodes: {s['costs']['native_finish_proof_nodes']}",
        f"온라인 selector: {s['costs']['online_selection']}",f"사후 selector: {s['costs']['posthoc_selection']}",
        '서로 다른 비용 단위를 더해 전체 속도/전력 절감으로 표현하지 않는다. 미계측 scan은 null이다.',
        '최초/후속 readout의 누적 ticks를 중복 합산하지 않는다. 평가 재생 비용은 task 비용이 아니다.',
        '추가 학습·관측 요청·raw 값 반전·prior 전환·새 controller 학습을 하지 않았다.',
        '같은 1개 topology의 6개 배열과 2 prior × 3 arm을 독립 표본 36개로 세지 않는다.',
        'D_DAG와 선택 경로를 기록하지만, 경로 길이나 D축을 조작한 실험이 아니다.',
        'input_isolation은 입력 개입을, records의 order_diagnostics는 ID 대응된 경로/activation을 기록한다.','']
    return '\n'.join(lines)
