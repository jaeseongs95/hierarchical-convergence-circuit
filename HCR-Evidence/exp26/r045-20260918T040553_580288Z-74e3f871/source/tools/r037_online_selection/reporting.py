"""readout/종료 채택과 paired 수·실제 실행 비용을 분리해서 보고한다."""
from __future__ import annotations
from collections import Counter
import csv
import io


def _counts(items, available, total):
    def correct(x):
        return bool(x['world_results']) and all(w['external_correct'] is True for w in x['world_results'].values())
    return dict(trials=total, available=available, no_readout=total-available,
                confirmed=sum(x['accepted'] for x in items),
                abstained=available-sum(x['accepted'] for x in items),
                correct_all_worlds=sum(correct(x) for x in items),
                wrong_any_world=sum(any(w['external_correct'] is False for w in x['world_results'].values()) for x in items))


def summarize(rows, final_rows) -> dict:
    groups = {}; pairs = []
    for scope in ('legacy', 'route_only'):
        for policy in ('native_saved', 'support_first'):
            finals = [f for f in final_rows if f['trial']['scope'] == scope and f['trial']['policy'] == policy]
            for phase in ('first_readout', 'last_available_readout'):
                part = [r for r in rows if r['scope'] == scope and r['policy'] == policy and r[phase]]
                items = [dict(accepted=r['policy_accepted'], world_results=r['world_results']) for r in part]
                groups[f'{phase}/{scope}/{policy}'] = _counts(items, len(part), len(finals))
            available = [f for f in finals if f['native_readouts']]
            items = [dict(accepted=f['adoption']['accepted'], world_results=f['world_results']) for f in available]
            groups[f'terminal_adoption/{scope}/{policy}'] = _counts(items, len(available), len(finals))
    bykey = {(f['trial']['case'], f['trial']['scope'], f['trial']['policy']): f for f in final_rows}
    for case, scope in sorted({(k[0], k[1]) for k in bykey}):
        a = bykey[(case, scope, 'native_saved')]; b = bykey[(case, scope, 'support_first')]
        ar = sorted((r for r in rows if r['case'] == case and r['scope'] == scope and r['policy'] == 'native_saved'), key=lambda r:r['ordinal'])
        br = sorted((r for r in rows if r['case'] == case and r['scope'] == scope and r['policy'] == 'support_first'), key=lambda r:r['ordinal'])
        common = min(len(ar), len(br))
        first_equal = None if not common else ar[0]['native_view_sha256'] == br[0]['native_view_sha256']
        prefix_equal = None if not common else all(x['native_view_sha256'] == y['native_view_sha256'] for x,y in zip(ar,br))
        pairs.append(dict(case=case, scope=scope, paired_trials=[a['trial']['id'], b['trial']['id']],
            first_native_view_equal=first_equal, common_readouts=common, common_native_view_prefix_equal=prefix_equal,
            native_adopted=a['adoption']['accepted'], support_adopted=b['adoption']['accepted'],
            native_value=a['adoption']['value'], support_value=b['adoption']['value'],
            native_stop=a['adoption']['reason'], support_stop=b['adoption']['reason'],
            native_kernel_ticks=a['costs']['native_kernel_ticks'], support_kernel_ticks=b['costs']['native_kernel_ticks'],
            support_minus_native_kernel_ticks=b['costs']['native_kernel_ticks']-a['costs']['native_kernel_ticks'],
            support_recovery=(not a['adoption']['accepted'] and b['adoption']['accepted']),
            support_regression=(a['adoption']['accepted'] and not b['adoption']['accepted']),
            recovered_correct_all_worlds=(not a['adoption']['accepted'] and b['adoption']['accepted'] and
                bool(b['world_results']) and all(w['external_correct'] is True for w in b['world_results'].values()))))
    usage = Counter()
    for f in final_rows:
        usage.update(f['costs']['selection_usage'])
    return dict(schema='hcr-exp18-summary-v1', native_trials=len(final_rows),
        base_cases=len({f['trial']['case'] for f in final_rows}), prior_policy_pairs=len(pairs),
        native_readouts=len(rows), initial_without_readout=sum(not f['native_readouts'] for f in final_rows),
        unique_native_kernel_ticks=sum(f['costs']['native_kernel_ticks'] for f in final_rows),
        initial_native_kernel_ticks=sum(f['costs']['initial_kernel_ticks'] for f in final_rows),
        extra_native_kernel_ticks=sum(f['costs']['extra_kernel_ticks'] for f in final_rows),
        native_proof_nodes_created=sum(f['native_proof_nodes'] for f in final_rows),
        online_selection_usage=dict(usage),
        stop_reasons=dict(Counter(f['adoption']['reason'] for f in final_rows)),
        groups=groups, paired=pairs, readout_rows=rows, final_rows=final_rows,
        boundaries=dict(native_kernel_unchanged=True, online_adoption_controls_stop=True,
            old_native_decisions_not_overwritten=True, policy_is_predeclared_not_learned=True,
            first_last_and_terminal_are_not_independent_trials=True,
            comparisons_are_paired_not_iid=True, audit_cost_not_task_cost=True,
            kernel_and_scan_and_proof_units_not_added=True, historical_training_not_rerun=True,
            unknown_native_capture_scan_cost=None))


def render(s) -> str:
    lines = ['# EXP-18 / R0.3.7 — 온라인 proof 채택', '',
        '선택 결과가 실제 후속 전개·종료를 제어한다. native kernel/원 finish 판단은 변경하지 않았다.',
        'support_first의 별도 proof/adoption을 원래 native 출력과 구분해 보존한다.', '',
        f"기본 입력 {s['base_cases']} / fresh native 실행 {s['native_trials']} / readout {s['native_readouts']}",
        f"readout 전 예산/엔진 종료 {s['initial_without_readout']}",
        f"native kernel ticks: {s['initial_native_kernel_ticks']} + {s['extra_native_kernel_ticks']} = {s['unique_native_kernel_ticks']}", '',
        '| 시점 / prior / policy | trial | readout 없음 | 확정 | 보류 | 모든 world 정답 | 하나 이상 오답 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for name,g in sorted(s['groups'].items()):
        lines.append(f"| {name} | {g['trials']} | {g['no_readout']} | {g['confirmed']} | {g['abstained']} | {g['correct_all_worlds']} | {g['wrong_any_world']} |")
    lines += ['', 'first/last readout과 terminal adoption은 같은 실행의 서로 다른 관찰이며 합산하지 않는다.',
        '마지막 readout 뒤 pending 계산이 미완성인 경우도 terminal_pending_ready에 별도로 보존한다.', '',
        '## Policy별 paired 비교', '',
        '| 입력 / prior | 첫 view 동일 | 공통 readout prefix 동일 | native 채택 | support 채택 | ticks native/support | 정답 회복 |',
        '|---|---|---|---|---|---:|---|']
    for p in s['paired']:
        lines.append(f"| {p['case']}/{p['scope']} | {p['first_native_view_equal']} | {p['common_native_view_prefix_equal']} | {p['native_adopted']} | {p['support_adopted']} | {p['native_kernel_ticks']}/{p['support_kernel_ticks']} | {p['recovered_correct_all_worlds']} |")
    lines += ['', '## 비용 및 주장 범위', '',
        f"native finish branch에서 생성한 proof node: {s['native_proof_nodes_created']}",
        f"온라인 selector 계측: {s['online_selection_usage']}",
        'Native ticks·경로/edge 검사·proof 생성/재사용은 서로 다른 비용 단위다. 단일 총비용으로 더하지 않는다.',
        '원 native capture 내부의 미계측 scan은 null이며 0이 아니다. evaluator 재생 비용은 task 비용에서 제외한다.',
        '8개 기본 입력의 prior/policy/world/readout 비교를 독립 문제 수로 세지 않는다. 통계적 일반화나 새 topology 검증은 하지 않았다.',
        '부정 raw 값은 기존 proof를 통과시킨다. 이 실험은 raw 값 반전·관측 요청·prior 재검토·학습된 자율 repair를 포함하지 않는다.',
        '보류가 정답 확정으로 회복됐는지, 지원된 오답인지, 계산/선택 예산 소진인지 분리해서 해석한다.',
        '검증 통과는 원자료·계보·제어·proof·비용의 정합성이다. 정답/개선 자체를 통과 조건으로 삼지 않는다.', '']
    return '\n'.join(lines)


def csv_text(rows) -> str:
    buffer = io.StringIO(newline=''); writer = csv.writer(buffer, lineterminator='\n')
    fields = ['trial_id','case','scope','policy','ordinal','first_readout','last_available_readout',
              'raw_value','native_value','policy_value','policy_reason','D_DAG','graph_complete',
              'recovered_same_value_output','kernel_ticks_at_readout']
    writer.writerow(fields)
    for r in rows:
        writer.writerow([r[k] for k in fields])
    return buffer.getvalue()
