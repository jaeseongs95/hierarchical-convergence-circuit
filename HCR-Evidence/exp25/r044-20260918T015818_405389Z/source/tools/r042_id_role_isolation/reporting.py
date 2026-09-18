"""독립 검산된 record에서 집계한다. 결과 역전·정답·불변성을 성공 조건으로 강제하지 않는다."""
from __future__ import annotations
import csv
import io
import json
from .storage import digest, require


def _outcome(record):
    return (record['final']['accepted'],record['final']['value'],record['classification'])


def _probe_equal(a,b):
    left,right = a['diagnostics']['pre_competitive_probe'],b['diagnostics']['pre_competitive_probe']
    return None if left is None or right is None else digest(left) == digest(right)


def contrast(a,b,kind,order):
    da,db = a['diagnostics'],b['diagnostics']
    return dict(comparison=kind, branch_order=order, left_trial=a['trial']['id'],right_trial=b['trial']['id'],
        left_variant=a['id_variant'],left_scheduler=a['trial']['scheduler'],
        right_variant=b['id_variant'],right_scheduler=b['trial']['scheduler'],
        left_native_ticks=a['usage']['native_kernel_ticks'],right_native_ticks=b['usage']['native_kernel_ticks'],
        right_minus_left_ticks=b['usage']['native_kernel_ticks']-a['usage']['native_kernel_ticks'],
        outcome_equal=_outcome(a) == _outcome(b),
        canonical_completion_equal=da['canonical_completion_sha256'] == db['canonical_completion_sha256'],
        canonical_readout_trajectory_equal=da['canonical_trajectory_sha256'] == db['canonical_trajectory_sha256'],
        canonical_final_proof_projection_equal=digest(da['final_proof_projection']) == digest(db['final_proof_projection']),
        pre_competitive_probe_equal=_probe_equal(a,b))


def summarize(records: list[dict]) -> dict:
    variants = ('identity','swap_SD'); schedulers = ('edge_id_min','edge_id_max')
    orders = ('SMD','SDM','MSD','MDS','DSM','DMS')
    require(len(records) == 24, 'reporting trial count')
    cells = {(r['id_variant'],r['branch_order'],r['trial']['scheduler']):r for r in records}
    require(len(cells) == 24 and set(cells) == {(v,o,s) for v in variants for o in orders for s in schedulers},
            'reporting condition population')
    groups = []
    for variant in variants:
        for scheduler in schedulers:
            rows = [cells[(variant,o,scheduler)] for o in orders]
            costs = [r['usage']['native_kernel_ticks'] for r in rows]
            require(all(type(n) is int and n >= 0 for n in costs), 'native tick type/range')
            groups.append(dict(id_variant=variant,scheduler=scheduler,permutations=6,
                min_native_ticks=min(costs),max_native_ticks=max(costs),tick_spread=max(costs)-min(costs),
                total_native_ticks=sum(costs),mean_native_ticks=sum(costs)/6,
                unique_outcomes=len({_outcome(r) for r in rows}),
                unique_canonical_completion_orders=len({r['diagnostics']['canonical_completion_sha256'] for r in rows}),
                unique_canonical_readout_trajectories=len({r['diagnostics']['canonical_trajectory_sha256'] for r in rows})))
    reversals, comparisons, trial_rows, readout_rows, scheduler_rows = [], [], [], [], []
    for order in orders:
        a,b = cells[('identity',order,'edge_id_min')],cells[('identity',order,'edge_id_max')]
        c,d = cells[('swap_SD',order,'edge_id_min')],cells[('swap_SD',order,'edge_id_max')]
        before = b['usage']['native_kernel_ticks']-a['usage']['native_kernel_ticks']
        after = d['usage']['native_kernel_ticks']-c['usage']['native_kernel_ticks']
        reversals.append(dict(branch_order=order,identity_max_minus_min_ticks=before,
            renamed_max_minus_min_ticks=after,strict_cost_order_reversed=before*after < 0,
            exact_cost_exchange=a['usage']['native_kernel_ticks'] == d['usage']['native_kernel_ticks'] and
                                b['usage']['native_kernel_ticks'] == c['usage']['native_kernel_ticks'],
            all_four_outcomes_equal=len({_outcome(r) for r in (a,b,c,d)}) == 1))
        comparisons.extend([contrast(a,c,'same_scheduler_min',order),contrast(b,d,'same_scheduler_max',order),
                            contrast(a,d,'cross_scheduler_min_to_max',order),contrast(b,c,'cross_scheduler_max_to_min',order)])
    for record in records:
        trial = record['trial']; diag = record['diagnostics']; first = diag['first_supported_readout']
        row = dict(trial_id=trial['id'],case=trial['case'],id_variant=record['id_variant'],
            branch_order=record['branch_order'],scheduler=trial['scheduler'],scope=trial['scope'],arm=trial['arm'],
            value=record['final']['value'],accepted=record['final']['accepted'],classification=record['classification'],
            reason=record['final']['reason'],native_ticks=record['usage']['native_kernel_ticks'],
            readouts=len(record['readouts']),final_frontier_count=record['final_frontier_count'],
            support_route_completion_rank=diag['support_route_completion_rank'],
            first_supported_ticks=None if first is None else first['ticks'],
            final_D_DAG=None if diag['final_proof_projection'] is None else diag['final_proof_projection']['D_DAG'])
        for key,value in record['scheduler_usage'].items(): row['scheduler_'+key] = value
        for key,value in record['usage']['online_selection'].items(): row['online_selection_'+key] = value
        usable = diag.get('first_usable_supported_readout')
        row['first_usable_supported_ticks'] = None if usable is None else usable['ticks']
        for key,value in record.get('native_cost',{}).items(): row['native_cost_'+key] = value
        row['reported_wall_seconds'] = record['reported_wall_seconds']
        trial_rows.append(row)
        readout_rows.extend(dict(trial_id=trial['id'],id_variant=record['id_variant'],branch_order=record['branch_order'],
            scheduler=trial['scheduler'],**{k:v for k,v in r.items() if k != 'state'}) for r in diag['canonical_readouts'])
        scheduler_rows.extend(dict(trial_id=trial['id'],id_variant=record['id_variant'],branch_order=record['branch_order'],
            scheduler=trial['scheduler'],**r) for r in diag['scheduler_rows'])
    reversed_count = sum(r['strict_cost_order_reversed'] for r in reversals)
    outcomes_equal = all(r['all_four_outcomes_equal'] for r in reversals)
    cross = [r for r in comparisons if r['comparison'].startswith('cross_')]
    cross_complete = all(r['canonical_completion_equal'] and r['canonical_readout_trajectory_equal'] for r in cross)
    probe_available = all(r['pre_competitive_probe_equal'] is not None for r in comparisons)
    probe_equal = probe_available and all(r['pre_competitive_probe_equal'] for r in comparisons)
    cost_reversal_evidence = 'all_orders' if reversed_count == 6 else 'some_orders' if reversed_count else 'no_order'
    # 기계적 판정은 관찰 표식이다. 반전이 없어도 측정 계약이 유효하면 audit는 성공한다.
    finding = ('supports_role_alignment_with_measured_trajectory_reversal'
               if reversed_count == 6 and outcomes_equal and cross_complete and probe_equal
               else 'cost_reversal_observed_but_simple_mediation_not_established'
               if reversed_count else 'no_cost_reversal_observed')
    return dict(schema='hcr-exp23-summary-v1',native_trials=24,base_topologies=1,
        evidence_level='native_toy_program_not_LLM_or_brain',groups=groups,reversals=reversals,
        comparisons=comparisons,trials=trial_rows,readouts=readout_rows,scheduler_decisions=scheduler_rows,
        finding=finding,cost_reversal_evidence=cost_reversal_evidence,reversal_orders=reversed_count,
        all_outcomes_equal=outcomes_equal,all_group_tick_spreads_zero=all(g['tick_spread']==0 for g in groups),
        crossed_canonical_trajectories_equal=cross_complete,pre_competitive_probe_available=probe_available,
        measured_pre_competitive_probes_equal=probe_equal,
        parent_regression_checked=sum(r['parent_regression'] is not None for r in records),
        wall_time_superiority_claimed=False,unmeasured_cost_is_zero=False,
        total_runtime_or_energy_savings_claimed=False,reversal_required_for_audit=False)


def csv_text(rows: list[dict]) -> str:
    if not rows: return ''
    fields = list(dict.fromkeys(k for row in rows for k in row))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for row in rows:
        writer.writerow({k:(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
                            if isinstance(v,(dict,list,tuple)) else v) for k,v in row.items()})
    return output.getvalue()


def render(summary: dict) -> str:
    rows = ['# EXP-23 / R042 — ID와 경로 역할 분리', '', '## 결론', '',
        f"관찰 분류: `{summary['finding']}`.",
        f"ID 재명명 후 min/max 비용 관계가 뒤집힌 순열: {summary['reversal_orders']}/6.",
        f"모든 4조건군 tick spread=0: {summary['all_group_tick_spreads_zero']}.",
        f"같은 순열의 4조건 모두 최종 결과 동일: {summary['all_outcomes_equal']}.",
        f"교차 scheduler의 측정된 canonical 궤적 동일: {summary['crossed_canonical_trajectories_equal']}.", '',
        '## 관찰', '', '| ID 배치 | Scheduler | 최소 tick | 최대 tick | Spread | 평균 tick |',
        '|---|---|---:|---:|---:|---:|']
    for row in summary['groups']:
        rows.append(f"| {row['id_variant']} | {row['scheduler']} | {row['min_native_ticks']} | {row['max_native_ticks']} | {row['tick_spread']} | {row['mean_native_ticks']:.2f} |")
    rows += ['', '## 해석과 대안 설명', '',
        '배열 순열 불변성, ID 재명명 민감도, 절대 native 계산비용을 분리한다. min 자체의 일반적 우월성을 가정하지 않는다.',
        '비용 관계가 역전되어도, 교차 scheduler의 inverse-ID 궤적과 초기 관측이 함께 대응하는지 comparisons.csv를 확인해야 한다.',
        'pre_competitive_probe는 첫 경쟁 frontier와 그 이전 readout만 비교한다. 전체 초기 상태 동치의 증명은 아니다.',
        '초기 probe 또는 교차 궤적이 다르면 scheduler 외 ID 영향도 설명 후보로 남는다.', '',
        '## 검증과 실패의 구분', '',
        f"identity parent 회귀: {summary['parent_regression_checked']}/12. audit 성공은 반전/정답/불변성 성공을 뜻하지 않는다.",
        '오답과 abstention은 결과로 보존한다. schema/reference/runtime 실패는 failure.json으로 분리하고 최초 실패에서 중단한다.', '',
        '## 현재 주장 가능한 범위', '',
        '고정된 toy topology 1개, ID 배치 2개, 배열 순열 6개, scheduler 2개의 24 paired 조건이다. 독립 문제 24개 또는 LLM 실험이 아니다.',
        'D_DAG는 검산된 proof 의존 깊이이며 tick 수나 계산 단계 수로 대체하지 않는다.',
        'native ticks, scheduler 작업량, selector 작업량, wall time을 별도로 보고한다. 전체 시간·전력 절감률을 주장하지 않는다.',
        'raw ID와 inverse-ID 투영을 함께 보존하며 평가용 투영은 실행 state 또는 proof를 고치지 않는다.', '']
    return '\n'.join(rows)
