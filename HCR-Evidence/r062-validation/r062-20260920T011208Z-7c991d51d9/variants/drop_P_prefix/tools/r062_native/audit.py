"""Independent native replay, strict source grammar and numerical bridge."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from tools.r050_review_boundary.audit import NativeVerifier, candidate_measures, counter_values, numerical_comparison, FORBIDDEN
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha, unseal
from tools.r053_feedback.audit import _close


def verify_record(plan, record, case, arm):
    body = unseal(record, 'hcc-r062-execution-v1')
    require(body['plan_sha256'] == fingerprint(plan), 'Plan binding')
    require(body['arm'] == arm and body['case_id'] == case['id'], 'Arm/case binding')
    require(body['automatic_retry'] is False and body['learned'] is False
            and body['actual_energy_joules'] is None, 'Intervention boundary')
    NativeVerifier(plan).execution(body['execution'], case, case['observation'], 0, arm)
    return body['execution']


def negative_checks(plan, record, case, arm):
    """Reseal outer hashes so semantic checks, not only checksums, are exercised."""
    from tools.r050_review_boundary.common import seal
    mutations = {
        'source_binding': lambda e: e['packet']['document']['source_hashes'].update({'unexpected.py': '0'*64}),
        'advance_count': lambda e: e.update(advances=e['advances']+1),
        'ready_state': lambda e: e.update(ready=not e['ready']),
        'native_value': lambda e: e['packet']['document']['engine']['pending'].update(value=not e['packet']['document']['engine']['pending']['value']),
        'proof_depth': lambda e: e['candidate']['decision']['proof'].update(primitive_depth=99),
        'support': lambda e: e['candidate']['diagnostic'].update(support_gap_edges=['invented-edge']),
        'adoption': lambda e: e['candidate']['readout'].update(accepted=not e['candidate']['readout']['accepted']),
        'tick_state': lambda e: next(x for x in e['packet']['document']['events'] if x['event']=='r02_tick')['payload']['state'].update(goal=0.123),
    }
    rejected = []
    for name, mutate in mutations.items():
        body = unseal(deepcopy(record), 'hcc-r062-execution-v1')
        mutate(body['execution'])
        packet = body['execution']['packet']
        packet['sha256'] = fingerprint(packet['document'])
        bad = seal(body)
        try:
            verify_record(plan, bad, case, arm)
        except (ValueError, AssertionError, RuntimeError) as exc:
            rejected.append(dict(test=name, exception=type(exc).__name__))
        else:
            raise AssertionError('Undetected mutation: '+name)
    return rejected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--arm', choices=['full', 'drop_P_prefix'], required=True)
    args = parser.parse_args()
    run, arm = args.run, args.arm
    plan = unseal(load(run/'plan.json'), 'hcc-r062-plan-v1')
    spec = plan['spec']
    require(files(run/'parents') == {spec['parent_aliases'][k]:v for k,v in spec['parent_files'].items()}, 'Pinned R052 evidence')
    require(files(run/'anchors') == {spec['anchor_aliases'][k]:v for k,v in spec['anchor_files'].items()}, 'Pinned R054 evidence')
    require(sha((run/'source_manifest.json').read_bytes()) == plan['source_manifest_sha256'], 'Base manifest binding')
    require(sha((run/'variant_manifest.json').read_bytes()) == plan['variant_manifest_sha256'], 'Variant manifest binding')
    base = load(run/'source_manifest.json')['files']
    variant = load(run/'variant_manifest.json')
    require(set(variant['files']) == set(base), 'Variant path coverage')
    difference = {k for k in base if base[k] != variant['files'][k]}
    require(difference == set(spec['source_patch_preimages']) == set(variant['changed']), 'Only two declared source files may differ')
    for path in difference:
        change = variant['changed'][path]
        require(change['before'] == base[path] == spec['source_patch_preimages'][path]
                and change['after'] == variant['files'][path], 'Source patch hash chain')
        original = (run/'source'/path).read_text(encoding='utf-8')
        actual = (run/'variants/drop_P_prefix'/path).read_text(encoding='utf-8')
        require(original.count(change['before_text']) == 1 and actual.count(change['after_text']) == 1
                and actual.replace(change['after_text'],change['before_text']) == original, 'Exact textual patch only')
    source = run/'source' if arm == 'full' else run/'variants'/arm
    expected = load(run/'source_manifest.json')['files'] if arm == 'full' else load(run/'variant_manifest.json')['files']
    require(files(source) == expected, 'Exact frozen source variant')
    rows = []
    for case in plan['cases']:
        record = load(run/'raw'/arm/case['id']/'execution.json')
        execution = verify_record(plan, record, case, arm)
        events = execution['packet']['document']['events']
        networks = [e['payload'] for e in events if e['event'] == 'r02_network']
        require(len(networks) == 1, 'Fixed single-chain network count')
        program = networks[0]['program']
        links = program['links']
        removed = [l for l in links if (l['source'], l['target'], l['kind']) == ('p:0:1','p:0:0','top_down')]
        require(len(removed) == (1 if arm == 'full' else 0), 'Exact feedback intervention')
        require(len(links) == (8 if arm == 'full' else 7), 'No extra structural intervention')
        # Ordinary toy signed-edge reference is computed here, never in producer.
        truth = all(e['score'] > 0 for e in case['observation']['edges'])
        row = dict(case=case['id'], arm=arm, measures=candidate_measures(execution, truth),
                   cost=counter_values(execution), reference_scope='two-edge signed toy input; not external world truth')
        if plan['purpose'] == 'research':
            anchor = unseal(load(run/'anchors'/case['id']/(arm+'.json')), 'hcc-r054-kernel-v1')
            ticks = [{k:e['payload'][k] for k in ('tick','state','residual','stable_steps')}
                     for e in events if e['event'] == 'r02_tick']
            require(_close(program, anchor['program']) and _close(ticks, anchor['ticks']), 'R054 full trajectory bridge')
            require(_close(row['measures']['numeric_state'], anchor['final_state']), 'R054 final-state bridge')
            row['r054_full_trajectory_matches'] = True
            if arm == 'full':
                parent_name = 'start_edge' if case['id'] == 'startstrong' else 'goal_edge'
                parent = load(run/'parents'/(parent_name+'.json'))['execution']
                parent_plan = load(run/'parents/plan.json')
                parent_case = next(c for c in parent_plan['spec']['cases'] if c['id']=='r052-c001')
                NativeVerifier(parent_plan).execution(parent, parent_case, case['observation'], 1, parent_name)
                comparison = numerical_comparison(execution, parent, {'abs_tol':1e-12,'rel_tol':1e-12})
                require(comparison['trajectory_close'] and comparison['terminal_equal'], 'R052 native bridge')
                row['r052_native_bridge'] = comparison
        else:
            row['rejected_mutations'] = negative_checks(plan, record, case, arm)
        rows.append(row)
    require(not (FORBIDDEN | {'tools.r062_native.worker'}) & set(sys.modules), 'Auditor imported native producer')
    dump(run/'audit'/(arm+'.json'), dict(verified=True, rows=rows,
        independent_formula_replay=True, independent_process=True, independent_researcher=False))
    print(arm, 'independent native audit passed', flush=True)


if __name__ == '__main__':
    main()
