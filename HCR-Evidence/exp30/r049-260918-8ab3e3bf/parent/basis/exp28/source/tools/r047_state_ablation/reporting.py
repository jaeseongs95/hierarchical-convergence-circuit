"""Descriptive paired reports; hypothesis outcomes never decide audit success."""
from __future__ import annotations
import csv
import io
import json
from collections import Counter
from .storage import digest, require
from .spec import ARMS, SCENARIOS, VARIANTS


def csv_bytes(rows):
    if not rows: return b''
    fields = list(dict.fromkeys(k for row in rows for k in row))
    f = io.StringIO(newline=''); writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
                         for k, v in row.items()})
    return f.getvalue().encode('utf-8')


def state(ok, available=True):
    return 'not_evaluable' if not available else 'supported' if ok else 'falsified'


def summarize(plan, sources, records, audits):
    cases = {x['id']: x for x in plan['cases']}; cells = {}; labels = {}; rows = []; maps = []; scans = []; sigs = []
    for trial in plan['trials']:
        r = records[trial['id']]; a = audits[trial['id']]; c = cases[trial['case']]
        cells[c['scenario'], c['variant'], trial['arm']] = r
        labels[c['scenario'], c['variant'], trial['arm']] = a['classification']
        n = r['native_cost']; b = r['bridge_cost']; sr = sources[trial['source']]
        row = dict(trial_id=trial['id'], scenario=c['scenario'], variant=c['variant'], arm=trial['arm'],
            source_record_sha256=digest(sr), raw_value=r['raw_value'], accepted=r['accepted'],
            classification=a['classification'], censored=r['censored'], termination=r['termination'],
            gate_valid=r['gate_valid'], gate_reason=r['gate_reason'], D_DAG=a['D_DAG'],
            A_ticks=sr['native_cost']['kernel_ticks'], B_ticks=n['kernel_ticks'],
            A_plus_B_ticks=sr['native_cost']['kernel_ticks']+n['kernel_ticks'],
            B_wall_seconds=r['wall_seconds'], energy_joules=None, peak_memory_bytes=None)
        row.update({'native.'+k: v for k, v in n.items() if k != 'wall_seconds'})
        row.update({'carry.'+k: v for k, v in b.items()}); rows.append(row)
        maps.extend(dict(trial_id=trial['id'], **m) for m in r['transfer_map'])
        scans.extend(dict(trial_id=trial['id'], check_index=i+1, **s) for i, s in enumerate(r['dependency_check_trace']))
        sigs.append(dict(trial_id=trial['id'], initial_state_sha256=digest(r['initial_state']),
            program_drives_sha256=digest(dict(program=r['program'], drives=r['effective_drives'])),
            dynamics_sha256=digest(dict(ticks=r['ticks'], convergence=r['convergence'])),
            proof_sha256=digest(r['proof_graph'])))
    require(len(cells) == 42, 'incomplete treatment matrix')
    pairs = []; hypotheses = []; differences = []
    def compare(sc, v, arm, baseline):
        r, c = cells[sc, v, arm], cells[sc, v, baseline]
        observable = r['program'] is not None and c['program'] is not None and not r['censored'] and not c['censored']
        outcome_equal = (r['raw_value'], r['accepted']) == (c['raw_value'], c['accepted'])
        # Saving an incorrect/unsupported outcome is not an efficiency success.
        usable = (observable and outcome_equal and r['accepted'] and c['accepted']
                  and labels[sc,v,arm] == labels[sc,v,baseline] == 'correct')
        delta = r['native_cost']['kernel_ticks']-c['native_cost']['kernel_ticks']
        pairs.append(dict(scenario=sc, variant=v, arm=arm, baseline=baseline,
            delta_ticks=delta, outcome_equal=outcome_equal, efficiency_evaluable=usable,
            program_drives_equal=(r['program'], r['effective_drives']) == (c['program'], c['effective_drives']),
            trajectory_equal=r['ticks'] == c['ticks']))
        for group in ('native_cost', 'bridge_cost'):
            for k in r[group]:
                if k == 'wall_seconds': continue
                differences.append(dict(scenario=sc, variant=v, arm=arm, baseline=baseline,
                    metric=group+'.'+k, treatment=r[group][k], control=c[group][k], delta=r[group][k]-c[group][k]))
        return r, c, observable, usable, delta, outcome_equal
    for sc in SCENARIOS:
        for v in VARIANTS:
            for arm in ARMS[1:]:
                r, c, ob, usable, dt, eq = compare(sc, v, arm, 'cold')
                hypotheses.append(dict(scenario=sc, variant=v, arm=arm, baseline='cold',
                    hypothesis='H_outcome', status=state(eq, ob)))
                if sc == 'extend' and arm.startswith('carry_'):
                    name = {'carry_edge': 'H_edge_ticks', 'carry_prefix': 'H_prefix_ticks', 'carry_both': 'H_carry_both_ticks'}[arm]
                    hypotheses.append(dict(scenario=sc, variant=v, arm=arm, baseline='cold',
                        hypothesis=name, status=state(dt < 0, usable and bool(r['transfer_map']))))
                if sc != 'extend':
                    hypotheses.append(dict(scenario=sc, variant=v, arm=arm, baseline='cold', hypothesis='H_rejection',
                        status=state(not r['gate_valid'] and not r['transfer_map'], ob)))
            if sc == 'extend':
                for mask in ('edge', 'prefix', 'both'):
                    r, c, ob, usable, dt, eq = compare(sc, v, 'carry_'+mask, 'fixed_'+mask)
                    hypotheses.append(dict(scenario=sc, variant=v, arm='carry_'+mask, baseline='fixed_'+mask,
                        hypothesis='H_source_specificity', status=state(dt < 0, usable)))
    interactions = []
    for v in VARIANTS:
        cs = {k: cells['extend', v, k] for k in ('cold', 'carry_edge', 'carry_prefix', 'carry_both')}
        ok = all(not r['censored'] and r['accepted'] and labels['extend',v,k] == 'correct' for k,r in cs.items())
        eq = len({(r['raw_value'], r['accepted']) for r in cs.values()}) == 1
        t = {k: r['native_cost']['kernel_ticks'] for k, r in cs.items()}
        interactions.append(dict(variant=v, evaluable=ok and eq,
            ticks_interaction=t['carry_both']-t['carry_edge']-t['carry_prefix']+t['cold'] if ok and eq else None,
            statistical_independence_claimed=False))
    ids = []
    for sc in SCENARIOS:
        for arm in ARMS:
            a, b = (cells[sc, v, arm] for v in VARIANTS)
            native_equal = {k: x for k, x in a['native_cost'].items() if k != 'wall_seconds'} == {
                            k: x for k, x in b['native_cost'].items() if k != 'wall_seconds'}
            eq = (a['raw_value'], a['accepted']) == (b['raw_value'], b['accepted'])
            trajectory = a['ticks'] == b['ticks']
            ids.append(dict(scenario=sc, arm=arm, native_counts_equal=native_equal, outcome_equal=eq,
                trajectory_equal=trajectory, identity_dependency_checks=a['bridge_cost']['dependency_checks'],
                fresh_dependency_checks=b['bridge_cost']['dependency_checks'],
                all_bridge_counts_equal={k: v for k, v in a['bridge_cost'].items() if not k.endswith('_bytes')} ==
                                        {k: v for k, v in b['bridge_cost'].items() if not k.endswith('_bytes')},
                total_operation_invariance_claimed=False))
            hypotheses.append(dict(scenario=sc, variant='identity_vs_fresh', arm=arm, baseline='identity',
                hypothesis='H_ID_native', status=state(native_equal and eq and trajectory, not a['censored'] and not b['censored'])))
    claims = dict(native_kernel_unchanged=True, proof_reuse_tested=False, preallocated_substrate_tested=False,
        learning_tested=False, learned_context_competition_tested=False, full_HCC_tested=False,
        energy_efficiency_measured=False, peak_memory_measured=False,
        parent_trials_recounted_as_independent=False, randomized_independent_replication=False,
        synthetic_validation_in_research_population=False,
        proof_counts_native_and_bridge_are_aliases_not_additive=True)
    return dict(schema='hcr-exp28-summary-v1', population=plan['population'], sources=2, followups=42,
        unique_native_ticks=sum(r['native_cost']['kernel_ticks'] for r in sources.values())+
                            sum(r['native_cost']['kernel_ticks'] for r in records.values()),
        trials=rows, pairs=pairs, hypotheses=hypotheses, cost_differences=differences,
        interactions=interactions, ID_controls=ids, transfer_maps=maps, dependency_scans=scans,
        signatures=sigs, claims=claims, hypothesis_counts=dict(Counter(h['status'] for h in hypotheses)))


def render(s):
    lines = ['# EXP-28 / R047 — 상태 전달의 기여 분해', '',
        '## 결론', '', f"모집단: `{s['population']}`. A 2회 공유, B 42조건. 독립 무작위 반복 실험이 아닙니다.",
        '전달 없음, edge만, prefix만, 둘 다를 비교하고 각 mask에 고정 초기값 0.99 대조를 둡니다.',
        '가설의 지지/실패는 아래에 전부 표시하며, audit 통과 여부와 구분합니다.', '',
        '## 관찰', '', '| 상황 | ID | 처리 | B ticks | 신규 proof | 초기값 설정 group | 판정 |',
        '|---|---|---|---:|---:|---:|---|']
    for t in s['trials']:
        lines.append(f"| {t['scenario']} | {t['variant']} | {t['arm']} | {t['B_ticks']} | {t['carry.proof_nodes_created']} | {t['carry.initial_groups_written']} | {t['classification']} |")
    lines += ['', '## 사전 가설 전체 판정', '', '| 상황 | ID | 처리/대조 | 가설 | 판정 |', '|---|---|---|---|---|']
    for h in s['hypotheses']:
        lines.append(f"| {h['scenario']} | {h['variant']} | {h['arm']} / {h['baseline']} | {h['hypothesis']} | {h['status']} |")
    lines += ['', '## 상호작용과 ID 검사 비용', '']
    for x in s['interactions']:
        lines.append(f"- {x['variant']}: both − edge − prefix + cold = {x['ticks_interaction']} ticks. 독립성 증명이 아니라 기술적 대조값입니다.")
    for x in s['ID_controls']:
        if not x['all_bridge_counts_equal']:
            lines.append(f"- {x['scenario']} / {x['arm']}: dependency 검사는 identity {x['identity_dependency_checks']}회 / fresh {x['fresh_dependency_checks']}회. 원래의 ID 정렬·조기 종료 효과를 숨기지 않았습니다.")
    lines += ['', '## 해석과 대안 설명', '',
        'actual carry와 fixed 대조의 ticks가 같으면, 이 단일 조건의 tick 절감만으로 A의 정밀한 수치 상태가 필수라고 주장하지 않습니다. 수치 궤적의 동일성과 tick 수의 동일성은 별개입니다.',
        '고정값 대조도 같은 binding, 근거 검사, source packet, target mask를 사용합니다. 이것은 binding이 불필요하다는 실험이 아닙니다.',
        'prefix는 기존 path-prefix signal group입니다. 자연어 의미·인간 사고 깊이·학습된 synaptic strength와 동일시하지 않습니다.',
        '기존 source 전체를 packet으로 전달하므로 부분 mask의 최소 저장/통신비용을 측정한 것이 아닙니다.',
        'D_DAG, ticks, group updates, signals, 검사 수, bytes, wall time은 서로 다른 단위입니다. native/bridge proof node 수는 동일 생성을 가리키는 중복 계수입니다.',
        'wall time에는 Python 기록·fsync 비용이 포함됩니다. 실행시간·전력 효율 주장은 하지 않습니다.', '',
        '## 현재 주장 가능한 범위', '',
        '현재 toy/kernel, 한 A→B 경계에서 상태 성분과 초기값을 분해했습니다. Preallocated substrate, 가소성, 새 회로 학습, 자연어 문맥 경쟁은 미실험입니다.',
        'EXP-27의 H_ID 실패는 별도 parent_review.ko.md에 그대로 유지합니다. 새 결과로 과거 가설을 소급 수정하지 않습니다.', '']
    return '\n'.join(lines).encode('utf-8')
