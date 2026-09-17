"""독립 검산 뒤에만 호출되는 보고서 생성. correlated 조건을 독립 시행으로 세지 않는다."""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import io


def summarize(rows, snapshots, native_audit, upstream_hash):
    groups = defaultdict(Counter)
    for r in rows:
        g = groups[r['group']+'/'+r['policy']]
        g['conditions'] += 1; g['accepted'] += r['accepted']; g['abstained'] += not r['accepted']
        g['applicable'] += r['applicable']; g['proof_nodes_created'] += r['usage']['proof_nodes_created']
        g['proof_nodes_reused'] += r['usage']['proof_nodes_reused']
        for k in ('ranked_paths','path_checks','edge_checks'):
            if r['usage'][k] is None: g[k+'_uninstrumented_conditions'] += 1
            else: g[k+'_recorded_inventory'] += r['usage'][k]
    full = {(r['snapshot_id'],r['variant'],r['policy']):r for r in rows if r['group']=='main'}
    paired = []
    for s in snapshots:
        variants = sorted({r['variant'] for r in rows if r['snapshot_id']==s['id'] and r['group']=='main'})
        for variant in variants:
            native = full[s['id'],variant,'native_saved']; rebuilt = full[s['id'],variant,'native_rebuild']; selected = full[s['id'],variant,'support_first']
            paired.append(dict(snapshot_id=s['id'],case=s['case'],scope=s['scope'],phase=s['phase'],variant=variant,
                native_saved_value=native['value'],native_rebuild_value=rebuilt['value'],support_first_value=selected['value'],
                reconstruction_changed_output=native['value'] is not rebuilt['value'],
                selection_only_recovery=native['value'] is None and rebuilt['value'] is None and selected['value'] is not None,
                semantic_route_changed_by_rebuild=native['source_route']!=rebuilt['source_route'],
                same_value=native['raw_value']==selected['raw_value']))
    families = []
    for s in snapshots:
        p = [x for x in paired if x['snapshot_id']==s['id']]
        outcome_sets = {}
        for policy in ('native_saved','native_rebuild','support_first'):
            rr = [full[s['id'],v,policy] for v in sorted({x['variant'] for x in p})]
            outcome_sets[policy] = len({(r['accepted'],r['value']) for r in rr}) == 1
        families.append(dict(snapshot_id=s['id'],case=s['case'],scope=s['scope'],phase=s['phase'],
            variants=len(p),selection_recovery_conditions=sum(x['selection_only_recovery'] for x in p),
            output_invariant_over_selector_representations=outcome_sets))
    return dict(schema='hcr-exp16-summary-v1',native_snapshots=len(snapshots),conditions=len(rows),
        main_conditions=sum(r['group']=='main' for r in rows),ablation_conditions=sum(r['group']!='main' for r in rows),
        groups={k:dict(v) for k,v in sorted(groups.items())},snapshot_families=families,paired=paired,rows=rows,
        source_native_audit=native_audit,upstream_manifest_sha256=upstream_hash,
        boundaries=dict(new_native_kernel_ticks=0,reused_exp15_states=True,not_independent_problem_replications=True,
            transformations_at_selector_boundary_only=True,not_graph_generation_robustness=True,
            no_autonomous_controller=True,source_cost_not_recounted=True,wall_seconds_not_total_cpu_cost=True))


def render(s):
    lines=['# EXP-16 / R0.3.5 — 동일 상태의 proof 재구성·선택 비교','',
        'EXP-15 원 상태를 재사용한 선택 단계 개입 결과다. 새 native Graph 실행 결과가 아니다.',
        'node/edge ID·slot·경로 순서 변형은 readout 이후에만 적용한다. 입력부터의 Graph 형성 효과와 구별한다.',
        '같은 원 상태의 변형과 여러 world 평가는 독립 문제/독립 반복이 아니다.','',
        f"원 native snapshot: {s['native_snapshots']} / 주 비교: {s['main_conditions']} / 예산 대조: {s['ablation_conditions']}",
        'EXP-16 새 native kernel ticks: 0. proof 생성·선택·검산은 별도 작업이다.','',
        '| 그룹 / 정책 | 조건 | 확정 | 보류 | 새 proof 노드 | 재사용 proof 노드 |',
        '|---|---:|---:|---:|---:|---:|']
    for k,g in s['groups'].items():
        lines.append(f"| {k} | {g['conditions']} | {g['accepted']} | {g['abstained']} | {g['proof_nodes_created']} | {g['proof_nodes_reused']} |")
    lines += ['','## 원 상태별 paired 결과','',
        '회복은 native 보존과 native 재구성이 모두 보류하고 support-first만 확정한 조건이다.',
        '확정이 곧 외부 정답이라는 뜻은 아니다. world별 정확성은 records/rows에 분리했다.','',
        '| 상태 | 입력 | prior | 단계 | 선택만으로 회복한 재표현 조건 | 출력 불변성 saved/rebuild/support |',
        '|---|---|---|---|---:|---|']
    for f in s['snapshot_families']:
        inv=f['output_invariant_over_selector_representations']
        lines.append(f"| {f['snapshot_id']} | {f['case']} | {f['scope']} | {f['phase']} | {f['selection_recovery_conditions']}/{f['variants']} | {inv['native_saved']}/{inv['native_rebuild']}/{inv['support_first']} |")
    lines += ['','## 판정 방법','',
        'identity 조건에서 native 재구성이 보존 proof와 다르면 단순 선택 개선으로 해석하지 않고 evaluator disagreement로 중단한다.',
        '순서 변형에서 활성도 동률의 tie-break가 달라지는 것은 실제 관찰로 남긴다. 불변성을 성공 조건으로 강제하지 않는다.',
        'support-first의 False/None 입력은 새로운 음성 proof를 찾지 않고 기존 native proof를 유지하는 범위 밖 대조다.',
        'native 재구성 내부 scan 카운터는 미계측(null)이다. 0 비용으로 해석하거나 서로 다른 단위를 합산하지 않는다.',
        '이 결과 이후의 새 입력 native Graph 변형 실험과 자율 controller 실험은 별도 단계다.','']
    return '\n'.join(lines)


def csv_text(rows):
    columns=('id','snapshot_id','case','scope','phase','variant','policy','group','raw_value','value','accepted','applicable','D_DAG')
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');w.writeheader()
    w.writerows({k:r[k] for k in columns} for r in rows)
    return stream.getvalue()
