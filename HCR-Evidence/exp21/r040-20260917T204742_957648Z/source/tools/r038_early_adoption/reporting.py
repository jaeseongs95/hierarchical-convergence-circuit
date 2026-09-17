"""서로 다른 비용 단위·반복 readout·paired 조건을 독립 표본으로 합치지 않는다."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import io as text_io
from .contracts import ARMS, SCOPES, demand


def compare_trio(group: dict) -> dict:
    a,b,c = (group[k] for k in ARMS)
    aa,bb,cc = (r['native_event_semantic_hashes'] for r in (a,b,c))
    av,bv,cv = ([x['native_view_sha256'] for x in r['readouts']] for r in (a,b,c))
    full_equal = aa == bb and av == bv
    prefix_equal = len(cc) <= len(aa) and cc == aa[:len(cc)] and len(cv) <= len(av) and cv == av[:len(cv)]
    first_equal = av[0] == bv[0] == cv[0] if all((av,bv,cv)) else None
    opportunities = [r for r in a['readouts'] if r['supported_frontier_opportunity']]
    differential = [r for r in a['readouts'] if r['differential_opportunity']]
    saving = b['usage']['native_kernel_ticks'] - c['usage']['native_kernel_ticks']
    # native_cost의 wall_seconds는 pending에서 보통 0이지만 시간 비교 기준으로 사용하지 않는다.
    native_same_cost = {k:v for k,v in a['native_cost'].items() if k != 'wall_seconds'} == {
                       k:v for k,v in b['native_cost'].items() if k != 'wall_seconds'}
    same_output = b['final']['accepted'] and c['final']['accepted'] and b['final']['value'] is c['final']['value']
    both_correct = b['classification'] == c['classification'] == 'correct_in_all_declared_worlds'
    unconfounded = full_equal and prefix_equal and native_same_cost and first_equal is True
    if not unconfounded: finding = 'paired_execution_not_comparable'
    elif not differential: finding = 'no_differential_opportunity_observed'
    elif same_output and saving > 0:
        finding = 'correct_output_preserving_tick_saving' if both_correct else 'supported_wrong_output_preserving_tick_saving'
    elif same_output and saving == 0: finding = 'opportunity_without_tick_saving'
    else: finding = 'opportunity_without_output_preserving_saving'
    return dict(case=a['trial']['case'],cohort=a['cohort'],scope=a['trial']['scope'],
        first_view_equal=first_equal,native_posthoc_full_trace_equal=full_equal,
        native_posthoc_cost_equal=native_same_cost,online_is_native_prefix=prefix_equal,
        supported_frontier_opportunity=bool(opportunities),differential_opportunity=bool(differential),
        first_opportunity_ordinal=opportunities[0]['ordinal'] if opportunities else None,
        first_differential_ordinal=differential[0]['ordinal'] if differential else None,
        native_value=a['final']['value'],posthoc_value=b['final']['value'],online_value=c['final']['value'],
        native_accepted=a['final']['accepted'],posthoc_accepted=b['final']['accepted'],online_accepted=c['final']['accepted'],
        native_ticks=a['usage']['native_kernel_ticks'],posthoc_ticks=b['usage']['native_kernel_ticks'],
        online_ticks=c['usage']['native_kernel_ticks'],saved_native_ticks=saving,
        saved_native_expansions=b['native_cost']['expansions']-c['native_cost']['expansions'],
        saved_native_advances=b['audit']['controller']['native_advances']-c['audit']['controller']['native_advances'],
        online_final_frontier=c['final_frontier_count'],
        online_stopped_with_frontier=c['final']['accepted'] and c['final_frontier_count'] > 0,
        same_supported_output=same_output,both_correct_in_declared_worlds=both_correct,
        observation_supported_saving=unconfounded and same_output and saving > 0,
        correct_output_preserving_tick_saving=unconfounded and same_output and both_correct and saving > 0,
        finding=finding)


def summarize(records: list[dict]) -> dict:
    groups = defaultdict(dict)
    for r in records:
        key = (r['trial']['case'],r['trial']['scope']); arm = r['trial']['arm']
        demand(arm not in groups[key], '중복 trial/arm')
        groups[key][arm] = r
    demand(all(set(g) == set(ARMS) for g in groups.values()), 'paired trio 누락')
    pairs = [compare_trio(groups[k]) for k in sorted(groups)]
    tables = []
    for cohort in ('all','baseline_control','new_topology'):
        for scope in SCOPES:
            for arm in ARMS:
                subset = [r for r in records if r['trial']['scope'] == scope and r['trial']['arm'] == arm and
                          (cohort == 'all' or r['cohort'] == cohort)]
                counts = Counter(r['classification'] for r in subset)
                tables.append(dict(cohort=cohort,scope=scope,arm=arm,trials=len(subset),
                    correct=counts['correct_in_all_declared_worlds'],incorrect=counts['incorrect_in_some_declared_world'],
                    abstained=counts['abstained'],no_readout=sum(not r['readouts'] for r in subset),
                    terminal_incomplete=sum(not r['terminal_pending_ready'] for r in subset),
                    native_ticks=sum(r['usage']['native_kernel_ticks'] for r in subset)))
    costs = dict(native_kernel_ticks=sum(r['usage']['native_kernel_ticks'] for r in records),
                 native_finish_proof_nodes=sum(r['native_finish_proof_nodes'] for r in records),
                 native_capture_scan_checks=None)
    for name in ('online_selection','posthoc_selection'):
        keys = records[0]['usage'][name] if records else {}
        costs[name] = {k:sum(r['usage'][name][k] for r in records) for k in keys}
    compact = [dict(trial_id=r['trial']['id'],case=r['trial']['case'],scope=r['trial']['scope'],arm=r['trial']['arm'],
        cohort=r['cohort'],value=r['final']['value'],accepted=r['final']['accepted'],reason=r['final']['reason'],
        base_stop_reason=r['base_stop_reason'],classification=r['classification'],
        native_ticks=r['usage']['native_kernel_ticks'],frontier_count=r['final_frontier_count'],
        readouts=len(r['readouts']),terminal_pending_ready=r['terminal_pending_ready'],
        final_assumption_counts=r['final_assumption_counts'],usage=r['usage']) for r in records]
    return dict(schema='hcr-exp19-summary-v1',base_cases=len({r['trial']['case'] for r in records}),
        native_trials=len(records),native_readouts=sum(len(r['readouts']) for r in records),
        paired_trios=len(pairs),tables=tables,paired=pairs,trials=compact,costs=costs,
        findings=dict(Counter(p['finding'] for p in pairs)),
        interpretation=dict(no_opportunity_is_not_refutation=True,
            correctness_not_guaranteed_by_support=True,cost_units_not_added=True,
            prior_arm_world_readout_not_independent_samples=True,
            new_cases_are_predeclared_diagnostics_not_random_population_sample=True))


def csv_text(rows: list[dict]) -> str:
    out = text_io.StringIO(newline='')
    if rows:
        writer = csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    return out.getvalue()


def trial_csv(rows: list[dict]) -> str:
    flattened = []
    for r in rows:
        row = {k:v for k,v in r.items() if k not in ('usage','final_assumption_counts')}
        for k in ('assumptions_checked','supported_assumptions','unsupported_assumptions'):
            row[k] = None if r['final_assumption_counts'] is None else r['final_assumption_counts'][k]
        for name in ('online_selection','posthoc_selection'):
            row.update({name+'_'+k:v for k,v in r['usage'][name].items()})
        flattened.append(row)
    return csv_text(flattened)


def render(summary: dict) -> str:
    lines = ['# EXP-19 / R0.3.8 — proof 선택과 조기 종료의 분리', '',
        f"기본 입력 {summary['base_cases']} / fresh native 실행 {summary['native_trials']} / readout {summary['native_readouts']}",
        '기존 대조 8개 + 사전 정의한 신규 topology 6개. 2개 prior × 3개 실험군은 paired 조건이다.', '',
        '## 최종 채택', '', '| 입력군 / prior / 실험군 | trial | 정답 | 오답 | 보류 | readout 없음 | 미완성 종료 | native ticks |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary['tables']:
        lines.append(f"| {r['cohort']}/{r['scope']}/{r['arm']} | {r['trials']} | {r['correct']} | {r['incorrect']} | {r['abstained']} | {r['no_readout']} | {r['terminal_incomplete']} | {r['native_ticks']} |")
    lines += ['', '보류/미관측/미완성 종료 열은 서로 배타적인 총합 항목이 아니다. 정답/오답/보류만 trial 수로 합산한다.',
        '정답은 모든 선언 world에서 정답이라는 뜻이며 관측 지지와 별도로 평가했다.', '',
        '## 선택 시점 paired 비교', '',
        '| 입력 / prior | 차등 기회 발생 | 첫 view/전체 기준 trace/온라인 prefix 일치 | native/posthoc/online ticks | 절감 ticks | 온라인 종료 frontier | 판정 |',
        '|---|---|---|---:|---:|---:|---|']
    for p in summary['paired']:
        same = f"{p['first_view_equal']}/{p['native_posthoc_full_trace_equal']}/{p['online_is_native_prefix']}"
        lines.append(f"| {p['case']}/{p['scope']} | {p['differential_opportunity']} | {same} | {p['native_ticks']}/{p['posthoc_ticks']}/{p['online_ticks']} | {p['saved_native_ticks']} | {p['online_final_frontier']} | {p['finding']} |")
    lines += ['', '차등 기회 = raw True + 완성된 관측 지지/activation 적격 경로 + 남은 frontier + native 보류.',
        '기회가 발생하지 않은 경우에는 조기 종료 가설의 반증으로 처리하지 않는다.',
        '절감 ticks = posthoc − online. 양수라도 출력/정답/prefix가 보존됐는지 함께 본다.', '',
        '## 비용과 해석 범위', '',
        f"최종 누적 native ticks 합계: {summary['costs']['native_kernel_ticks']}",
        f"원 native finish가 만든 proof node: {summary['costs']['native_finish_proof_nodes']}",
        f"온라인 selector 계측: {summary['costs']['online_selection']}",
        f"사후 selector 계측: {summary['costs']['posthoc_selection']}",
        'Native ticks, 경로/edge 검사, proof 생성/재사용은 다른 비용 단위다. 합산 총비용/전력 절감으로 해석하지 않는다.',
        'Native capture 내부 미계측 scan은 null이다. 반복 readout 누적 ticks를 더하지 않는다.',
        'Wall time에는 Python·직렬화·보존 비용이 포함된다. 반복 timing 실험이 아니므로 순수 속도 우위로 일반화하지 않는다.',
        '검증 통과는 원자료·seed·상태·제어·proof·계수 정합성이다. 기회 발생/정답/개선을 통과 조건으로 삼지 않는다.',
        '기존 R035 auditor의 supported_assumptions 명명 오류는 신규 보고에서 검사/지원/비지원 수로 분리했다. 기존 raw/analysis는 수정하지 않았다.',
        '학습된 자율 repair, native kernel 교체, raw 값 반전, 외부 관측 요청, LLM/인간 뇌 검증은 포함하지 않는다.', '']
    return '\n'.join(lines)
