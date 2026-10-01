"""Independent raw replay. Never import the worker or its intervention policy."""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import io
from pathlib import Path
import sys
from tools.r050_review_boundary.common import (dump, files, fingerprint, git_tree,
    load, publish, require, sha, unseal, SRC_TREE, TEST_TREE)
from tools.r050_review_boundary.audit import (NativeVerifier, candidate_measures,
    counter_values, check_progress, numerical_comparison, FORBIDDEN)

ARMS = ('hold', 'revision_only', 'edge0', 'edge1')
FORBIDDEN = FORBIDDEN | {'tools.r051_edge_controls.worker'}


def validate_spec(spec):
    from hcr import codec
    from hcr.model import AdaptiveConfig
    require(spec['schema'] == 'hcc-r051-frozen-spec-v1', 'Spec schema')
    require(spec['contract'] == 'r051-fixed-edge-controls-v1' and
            spec['frozen_before_research_execution'] is True, 'Frozen contract')
    require(fingerprint(spec['config']) == fingerprint(codec.plain(AdaptiveConfig())),
            'Exact default config including numeric representation')
    require(spec['arms'] == list(ARMS), 'Arm matrix')
    require(spec['limits'] == dict(max_advances_per_session=8,
        max_kernel_ticks_per_session=1280), 'Budget contract')
    require(spec['numeric_comparison'] == dict(abs_tol=1e-12, rel_tol=1e-12), 'Tolerance')
    expected = []
    for strength in (0.02,):
        for identity in (0, 1):
            for td in (False, True):
                number = len(expected)
                nodes = ('v0', 'v1', 'v2') if identity == 0 else ('v2', 'v1', 'v0')
                ids = ('a-edge', 'z-edge') if identity == 0 else ('z-edge', 'a-edge')
                expected.append(dict(id=f'r051-c{number:03d}', strength=strength,
                    relation='++', identity_variant=identity, top_down=td,
                    observation=dict(episode_id=f'r051-c{number:03d}', revision=0,
                        start=nodes[0], goal=nodes[2], edges=[dict(id=ids[i], source=nodes[i],
                            target=nodes[i+1], score=strength) for i in (0, 1)])))
    require(fingerprint(spec['cases']) == fingerprint(expected), 'Predeclared positive chain matrix')


def expected_observation(observation, arm):
    require(arm in ARMS, 'Arm whitelist')
    obs = deepcopy(observation)
    if arm != 'hold':
        obs['revision'] = 1
    if arm == 'edge0':
        obs['edges'][0]['score'] = 1.0
    if arm == 'edge1':
        obs['edges'][1]['score'] = 1.0
    return obs


def validate_record(record, baseline, case, arm):
    raw = unseal(record, 'hcc-r051-arm-v1')
    require(set(raw) == {'schema', 'case_id', 'arm', 'baseline_sha256', 'observation',
                        'measurement_calls', 'automatic_retry', 'execution'}, 'Arm fields')
    require(raw['case_id'] == case['id'] and raw['arm'] == arm
            and raw['baseline_sha256'] == baseline['sha256'], 'Paired baseline identity')
    require(raw['observation'] == expected_observation(case['observation'], arm),
            'Input differs from fixed intervention')
    require(type(raw['measurement_calls']) is int and raw['measurement_calls'] == 0
            and raw['automatic_retry'] is False, 'Hidden measurement or retry')
    require((raw['execution'] is None) == (arm == 'hold'), 'Fixed restart count')
    return raw


def audit(run):
    manifest = load(run / 'source_manifest.json')
    require(files(run / 'source') == manifest['files'], 'Frozen source inventory/hash')
    require(git_tree(run / 'source/src') == SRC_TREE and
            git_tree(run / 'source/tests') == TEST_TREE, 'Core/test tree drift')
    plan = unseal(load(run / 'plan.json'), 'hcc-r051-plan-v1')
    require(plan['source_manifest_sha256'] == sha((run / 'source_manifest.json').read_bytes()),
            'Plan/source binding')
    spec = load(run / 'source/experiments/exp-32-edge-controls/frozen_spec.json')
    require(plan['spec'] == spec, 'Frozen spec binding')
    validate_spec(spec)
    from hcr import codec
    from hcr.model import AdaptiveConfig
    from hcr.circuits import AdaptiveMemory
    require(plan['config'] == spec['config'] == codec.plain(AdaptiveConfig()) and
            plan['empty_memory'] == AdaptiveMemory.empty(AdaptiveConfig()).document()
            and plan['limits'] == spec['limits'], 'Native config or memory drift')
    require(plan['purpose'] in ('implementation_validation', 'research'), 'Run purpose')
    smoke = plan['purpose'] == 'implementation_validation'
    root = run / ('smoke' if smoke else 'study')
    cases = spec['cases'][:2] if smoke else spec['cases']
    raw_manifest = load(run / 'raw_manifest.json')
    require(raw_manifest['schema'] == 'hcc-r051-raw-manifest-v1' and
            files(root) == raw_manifest['files'], 'Raw inventory/hash')
    require(set(files(root / 'baselines')) == {c['id']+'.json' for c in cases}, 'Baseline inventory')
    expected_names = {c['id']+'/'+a+'.json' for c in cases for a in ARMS}
    require(set(files(root / 'raw')) == expected_names and
            set(files(root / 'interventions')) == expected_names, 'Arm/receipt inventory')
    verifier = NativeVerifier(plan)
    progress, rows, comparisons = set(), [], []
    by_case = {}
    baseline_cost, extra_cost = Counter(), Counter()
    for case in cases:
        baseline = load(root / 'baselines' / (case['id']+'.json'))
        base = unseal(baseline, 'hcc-r051-baseline-v1')
        require(set(base) == {'schema', 'case', 'execution'} and base['case'] == case, 'Baseline fields')
        initial = base['execution']
        verifier.execution(initial, case, case['observation'], 0, 'baseline')
        progress.update(check_progress(root, case['id'], 'baseline', initial))
        baseline_cost.update(counter_values(initial))
        executions = {}
        for arm in ARMS:
            raw = validate_record(load(root / 'raw' / case['id'] / (arm+'.json')), baseline, case, arm)
            receipt = {k:v for k,v in raw.items() if k not in ('schema', 'execution')}
            require(receipt == load(root / 'interventions' / case['id'] / (arm+'.json')), 'Intervention receipt')
            execution = raw['execution']
            if execution is not None:
                verifier.execution(execution, case, raw['observation'], 1, arm)
                progress.update(check_progress(root, case['id'], arm, execution))
            final = initial if arm == 'hold' else execution
            executions[arm] = final
            counters = counter_values(execution)
            extra_cost.update(counters)
            rows.append(dict(case_id=case['id'], strength=case['strength'], top_down=case['top_down'],
                identity_variant=case['identity_variant'], arm=arm,
                baseline_sha256=baseline['sha256'], initial=candidate_measures(initial, True),
                final=candidate_measures(final, True), restarts=int(execution is not None),
                changed_slots=[i for i in (0, 1) if raw['observation']['edges'][i]['score'] !=
                               case['observation']['edges'][i]['score']],
                baseline_counters=counter_values(initial), additional_counters=counters,
                actual_energy_joules=None, measurement_calls=0))
        for left, right in (('hold', 'revision_only'), ('revision_only', 'edge0'),
                            ('revision_only', 'edge1'), ('edge0', 'edge1')):
            comparisons.append(dict(case_id=case['id'], left=left, right=right,
                comparison=numerical_comparison(executions[left], executions[right], spec['numeric_comparison'])))
        by_case[case['id']] = executions
    require(set(files(root / 'progress')) == progress, 'Progress inventory')
    expected_all = {d+'/'+n for d in ('raw', 'interventions') for n in expected_names}
    expected_all |= {'baselines/'+c['id']+'.json' for c in cases}
    expected_all |= {'progress/'+n for n in progress}
    require(set(files(root)) == expected_all, 'Extra raw artifacts')
    require(not (FORBIDDEN & set(sys.modules)), 'Auditor imported a producer')
    cross_case = []
    for axis, pairs in (('top_down', ((0,1),(2,3))), ('identity', ((0,2),(1,3)))):
        for left, right in pairs:
            if right >= len(cases):
                continue
            lc, rc = cases[left]['id'], cases[right]['id']
            for arm in ARMS:
                cross_case.append(dict(axis=axis, left_case=lc, right_case=rc, arm=arm,
                    comparison=numerical_comparison(by_case[lc][arm], by_case[rc][arm], spec['numeric_comparison'])))
    return dict(schema='hcc-r051-audit-v1', verified=True,
        research_experiment=not smoke, purpose=plan['purpose'], baseline_count=len(cases),
        arm_records=len(rows), rows=rows, comparisons=comparisons, cross_case_comparisons=cross_case,
        unique_baseline_counters=dict(baseline_cost), additional_counters=dict(extra_cost),
        independent_samples=False, native_state_replay=True)


def render(report):
    require(report['verified'] is True, 'Verified audit required')
    rows = report['rows']
    lines = ['# EXP-32 / R051', '', '실행 목적: '+report['purpose'], '',
        '독립 원자료 검산을 통과했다. 검산 통과는 가설 지지를 뜻하지 않는다.', '',
        '| 강도 | top-down | 개입 | 채택 | 정답 채택 | 오답 채택 | 보류 | 추가 ticks |',
        '|---|---|---|---:|---:|---:|---:|---:|']
    flat = []
    for row in rows:
        final = row['final']
        flat.append(dict(case_id=row['case_id'], strength=row['strength'],
            top_down=row['top_down'], identity_variant=row['identity_variant'], arm=row['arm'],
            raw_value=final['raw_decision'], proof_valid=final['proof_valid'],
            failure_class=final['failure_class'], edge_conflicts=final['internal_edge_conflicts'],
            accepted=final['accepted'], adopted_correct=final['adopted_correct'],
            restarts=row['restarts'], changed_slots=','.join(map(str,row['changed_slots'])),
            additional_kernel_ticks=row['additional_counters']['kernel_ticks'],
            additional_signal_transmissions=row['additional_counters']['signal_transmissions']))
    for strength in sorted({r['strength'] for r in rows}):
        for td in (False, True):
            for arm in ARMS:
                group = [r for r in rows if (r['strength'],r['top_down'],r['arm']) == (strength,td,arm)]
                lines.append(f'| {strength} | {td} | {arm} | '+ ' | '.join(str(x) for x in (
                    sum(r['final']['accepted'] for r in group),
                    sum(r['final']['adopted_correct'] is True for r in group),
                    sum(r['final']['adopted_correct'] is False for r in group),
                    sum(not r['final']['accepted'] for r in group),
                    sum(r['additional_counters']['kernel_ticks'] for r in group)))+' |')
    lines += ['', '동일 기준선의 분기는 독립 표본이 아니다. 관측 강도 조작은 센서 측정이 아니다.',
        'edge0와 edge1은 변경 edge 수와 총 강도 증가를 맞춘 위치 대조다.',
        '부호 충돌 감소, proof 유효성, 채택을 별도로 해석한다. 구현 검증은 연구 결과로 합산하지 않는다.']
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
    writer.writeheader()
    writer.writerows(flat)
    return {'summary.ko.md': ('\n'.join(lines)+'\n').encode('utf-8'),
            'trials.csv': stream.getvalue().encode('utf-8-sig')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.run)
    dump(args.run / 'analysis/audit.json', report)
    rendered = render(report)
    for name, content in rendered.items():
        publish(args.run / 'analysis' / name, content)
    require(all((args.run/'analysis'/n).read_bytes() == b for n,b in render(load(args.run/'analysis/audit.json')).items()),
            'Derived artifact mismatch')
    dump(args.run/'validation/analysis_consistency.json', dict(verified=True,
        files={n:sha(b) for n,b in rendered.items()}, new_inferences=0))
    print('VERIFIED:', report['baseline_count'], 'baselines /', report['arm_records'], 'arm records')


if __name__ == '__main__':
    main()
