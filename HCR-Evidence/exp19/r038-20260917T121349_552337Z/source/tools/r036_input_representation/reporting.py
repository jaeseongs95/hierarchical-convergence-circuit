"""실행 수·관측 gap·paired 불변성·비용을 분리 보고한다."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import io
import json


def fingerprint(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))


def summarize(rows, native_reports, trial_specs, seed_audit) -> dict:
    groups={}
    for phase,flag in [('first_readout','first_readout'),('last_available_readout','last_available_readout')]:
        selected=[r for r in rows if r[flag]]
        for scope in ('legacy','route_only'):
            part=[r for r in selected if r['scope']==scope]
            for policy in ('native_saved','native_rebuild','support_first'):
                confirmed=sum(r['canonical']['outputs'][policy]['accepted'] for r in part)
                # 여러 world의 판정을 문제 수로 합산하지 않는다.
                all_correct=sum(bool(r['world_results'][policy]) and all(x['external_correct'] is True for x in r['world_results'][policy].values()) for r in part)
                any_wrong=sum(any(x['external_correct'] is False for x in r['world_results'][policy].values()) for r in part)
                groups[f'{phase}/{scope}/{policy}']=dict(states=len(part),confirmed=confirmed,abstained=len(part)-confirmed,
                    correct_in_all_declared_worlds=all_correct,wrong_in_any_declared_world=any_wrong)
    paired=[]
    for phase,flag in [('first_readout','first_readout'),('last_available_readout','last_available_readout')]:
        by=defaultdict(list)
        for r in rows:
            if r[flag]:by[(r['case'],r['scope'])].append(r)
        for (case,scope),part in sorted(by.items()):
            part.sort(key=lambda r:r['variant']);identity=next((r for r in part if r['variant']=='i000'),None)
            def invariant(fn):return len({fingerprint(fn(r)) for r in part})==1
            common=0;difference=None
            if identity:
                ref=identity['canonical']['edge_activation'];deltas=[]
                for r in part:
                    cur=r['canonical']['edge_activation']
                    for k in set(ref)&set(cur):
                        if ref[k] is not None and cur[k] is not None:
                            common+=1;deltas.append(abs(ref[k]-cur[k]))
                if deltas:difference=max(deltas)
            expected_count=sum(t['case']==case and t['scope']==scope for t in trial_specs)
            paired.append(dict(case=case,scope=scope,phase=phase,observed_variants=len(part),
                expected_variants=expected_count,all_variants_have_native_readout=len(part)==expected_count,
                route_set_invariant=invariant(lambda r:r['canonical']['completed_route_set']),
                route_order_invariant=invariant(lambda r:r['canonical']['completed_route_order']),
                raw_value_invariant=invariant(lambda r:r['canonical']['raw_value']),
                native_output_invariant=invariant(lambda r:r['canonical']['outputs']['native_saved']['value']),
                support_output_invariant=invariant(lambda r:r['canonical']['outputs']['support_first']['value']),
                support_route_invariant=invariant(lambda r:r['canonical']['outputs']['support_first']['route']),
                paired_selection_recoveries=sum(r['diagnostic']['recovered_same_value_output'] for r in part),
                max_edge_activation_absolute_difference=difference,activation_pairs_compared=common,
                diagnostic_counts=dict(Counter(r['diagnostic']['label'] for r in part))))
    usage=defaultdict(lambda:Counter())
    unmeasured=Counter()
    for r in rows:
        for policy,counters in r['selection_usage'].items():
            for k,v in counters.items():
                if v is None:unmeasured[f'{policy}/{k}']+=1
                else:usage[policy][k]+=v
    return dict(schema='hcr-exp17-summary-v1',native_trials=len(native_reports),native_readouts=len(rows),
        selector_evaluations=3*len(rows),
        initial_without_readout=sum(x['status']=='initial_budget_exhausted' for x in native_reports.values()),
        unique_native_task_kernel_ticks=sum(x['kernel_ticks'] for x in native_reports.values()),
        initial_native_kernel_ticks=sum(x['kernel_ticks']-x['extra_kernel_ticks'] for x in native_reports.values()),
        extra_native_kernel_ticks=sum(x['extra_kernel_ticks'] for x in native_reports.values()),
        native_advances=sum(x['advances'] for x in native_reports.values()),
        historical_training_cost_not_rerun=True,groups=groups,paired=paired,
        selection_usage={k:dict(v) for k,v in usage.items()},unmeasured_counter_rows=dict(unmeasured),
        stop_reasons=dict(Counter(x['stop_reason'] for x in native_reports.values())),
        source_seed_audit=seed_audit,rows=rows,
        boundaries=dict(input_transform_before_native=True,posthoc_state_transport=False,
            selector_controls_native_work=False,autonomous_repair_controller=False,
            paired_representations_are_not_independent_tasks=True,source_names_are_analysis_labels_only=True))


def render(s) -> str:
    lines=['# EXP-17 / R0.3.6 — 입력 재표현과 native Graph 형성', '',
        '각 재표현 입력에서 native 엔진을 새로 실행했다. 동결된 memory만 EXP-15에서 재사용했다.',
        '선택기는 실제 native readout 후에만 적용했고, 후속 전개량이나 종료를 제어하지 않았다.',
        '같은 입력의 재표현·두 prior 조건·여러 world 평가는 독립 문제 수로 합산하지 않는다.', '',
        f"native 실행 {s['native_trials']} / 실제 native readout {s['native_readouts']} / 선택 비교 {s['selector_evaluations']}",
        f"최초 판단 이전 예산 종료 {s['initial_without_readout']}",
        f"새 task kernel ticks {s['initial_native_kernel_ticks']} + {s['extra_native_kernel_ticks']} = {s['unique_native_task_kernel_ticks']}", '',
        '| 단계 / prior / 선택 | 상태 | 확정 | 보류 | 모든 선언 world 정답 | 하나 이상 오답 |',
        '|---|---:|---:|---:|---:|---:|']
    for k,g in sorted(s['groups'].items()):
        lines.append(f"| {k} | {g['states']} | {g['confirmed']} | {g['abstained']} | {g['correct_in_all_declared_worlds']} | {g['wrong_in_any_declared_world']} |")
    lines+=['','첫/마지막 readout 표는 같은 실행을 서로 다른 시점에서 본 것이다. 두 표의 비용·표본을 다시 합산하지 않는다.',
        '`last_available_readout`은 가장 나중에 얻은 판단이며, 예산 종료 시점의 미완성 상태와 구별한다.', '',
        '## 입력 재표현별 paired 비교','',
        '| 입력 / prior / 단계 | readout 변형 | 경로 집합 불변 | raw 값 불변 | native 출력 불변 | support 출력 불변 | 선택 회복 |',
        '|---|---:|---|---|---|---|---:|']
    for p in s['paired']:
        lines.append(f"| {p['case']}/{p['scope']}/{p['phase']} | {p['observed_variants']}/{p['expected_variants']} | {p['route_set_invariant']} | {p['raw_value_invariant']} | {p['native_output_invariant']} | {p['support_output_invariant']} | {p['paired_selection_recoveries']} |")
    lines+=['','## 해석할 때 유지할 구분','',
        '후보 pool에서 제안한 경로, workspace의 완성 경로, activation 적격 경로, 최종 proof는 별도 필드다.',
        'gap label은 관찰 위치의 분류이며 학습 편향 등 원인을 확정한 진단이 아니다.',
        '입력의 전체 판별 가능성과 숨은 world 정답은 independent evaluator만 계산한다.',
        '동일 상태 native 재구성 불일치는 evaluator disagreement로 중단한다. 재표현 결과 불변성은 성공 조건으로 강제하지 않는다.',
        '경로·edge 검사, proof 생성, native kernel ticks는 다른 비용 단위다. 미계측 scan은 null이며 0이 아니다.',
        '추가 전개는 기존 expand_only 정책이다. native 지지 출력이 나오면 종료하므로 모든 trial의 Graph 완성을 보장하지 않는다.',
        '새로운 topology 또는 자율적인 expand/observe/review/select 선택 능력은 이 실험의 검증 범위가 아니다.','']
    return '\n'.join(lines)


def csv_text(rows):
    f=io.StringIO(newline='');w=csv.writer(f,lineterminator='\n')
    w.writerow(['trial','case','scope','variant','readout_ordinal','first','last_available','raw_value',
                'native_output','support_output','gap','supported_completed','active_supported_completed','kernel_ticks_at_readout'])
    for r in rows:
        c=r['canonical'];d=r['diagnostic']
        w.writerow([r['trial_id'],r['case'],r['scope'],r['variant'],r['ordinal'],r['first_readout'],r['last_available_readout'],
                    c['raw_value'],c['outputs']['native_saved']['value'],c['outputs']['support_first']['value'],d['label'],
                    len(d['completed_supported_indices']),len(d['completed_activation_eligible_supported_indices']),r['native_kernel_ticks_at_readout']])
    return f.getvalue()
