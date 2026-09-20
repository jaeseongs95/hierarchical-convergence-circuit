"""Independent fixed-chain logic plus existing formula replay, without producer imports."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.reference import assess
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r050_review_boundary.common import dump, fingerprint, load, require, sha, unseal
from tools.r064_retention.audit import final_audit


def check_rows(report, spec, parent):
    plan = unseal(load(parent/'plan.json'), 'hcc-r064-plan-v1')
    expected = {(s, g, c['id']) for s in spec['snapshots'] for g in (False, True) for c in plan['cases']}
    seen = set()
    for row in report['rows']:
        key = (row['snapshot'], row['use_circuits'], row['case'])
        require(key in expected and key not in seen, 'Exact unique cell coverage'); seen.add(key)
        s, g, cid = key; identity = f"{s}-{'on' if g else 'off'}-{cid}"
        path = parent/'evaluation'/identity/'inference.json'
        candidate = unseal(load(path), 'hcc-r064-inference-v1')['execution']['candidate']
        require(candidate is not None, 'Absent native candidate')
        decision = candidate['decision']; obs = next(c['observation'] for c in plan['cases'] if c['id'] == cid)
        # This verifier uses the frozen two-edge conjunction, not the producer's graph traversal.
        require([(e['id'], e['source'], e['target']) for e in obs['edges']] == [('e0','v0','v1'), ('e1','v1','v2')]
                and (obs['start'], obs['goal']) == ('v0','v2'), 'Fixed-chain construct')
        require(row['identity'] == identity and row['inference_sha256'] == sha(path.read_bytes()), 'Raw identity')
        require(row['packet_sha256'] == fingerprint(candidate['packet']) and row['observation_sha256'] == fingerprint(obs)
                and row['memory_sha256'] == fingerprint(load(parent/'memory'/f'{s}.json')), 'Paired input/packet identity')
        require(row['value'] is decision['value'] and row['accepted'] is candidate['readout']['accepted'], 'Readout unchanged')
        require(row['circuit_reuses'] == decision['cost']['circuit_reuses'] and row['expansions'] == decision['cost']['expansions'], 'Raw cost')
        require(len(row['worlds']) == 2 and {w['world'] for w in row['worlds']} == set(spec['worlds']), 'Exact paired worlds')
        for w in row['worlds']:
            truth = spec['worlds'][w['world']]; target = truth['e0'] and truth['e1']
            expected_correct = None if not row['accepted'] or row['value'] is None else row['value'] is target
            external = assess(codec.adaptive_decision_from(decision), codec.observation_from(obs), truth)
            require(w['truth'] == truth and w['reachable'] is target and w['adopted_correct'] is expected_correct, 'Reference rescore')
            if row['accepted']: require(external.correct is expected_correct, 'Independent reference evaluator')
        require(row['both_worlds_correct'] is False and sum(w['adopted_correct'] is True for w in row['worlds']) <= 1, 'Contradictory targets')
    require(seen == expected and report['existing_packets'] == 12 and report['reference_evaluations'] == 24, 'Complete fixed matrix')
    require(report['new_native_research_executions'] == report['new_independent_samples'] == 0
            and report['actual_world_intervention'] is False and report['reanalysis'] is True, 'Evidence counting boundary')


def check_memory(report, spec, parent):
    snapshots = {s: load(parent/'memory'/f'{s}.json') for s in spec['snapshots']}
    for row, (a,b) in zip(report['deltas'], zip(spec['snapshots'], spec['snapshots'][1:])):
        x, y = snapshots[a], snapshots[b]
        require(row == dict(before=a, after=b, changed_top_level=sorted(set(k for k in y if y[k] != x[k])),
            circuits_equal=x['circuits'] == y['circuits'], pending_equal=x['pending'] == y['pending'],
            patch=y['patches'][-1], version_before=x['version'], version_after=y['version']), 'Exact memory delta')
    require(len(report['deltas']) == 2 and report['persistent_fields'] == sorted(snapshots['after_correction']), 'Memory coverage')
    learn = unseal(load(parent/'revision/corrected_observation/learning.json'), 'hcc-r064-learning-v1')
    decision = unseal(load(parent/'revision/corrected_observation/inference.json'), 'hcc-r064-inference-v1')['execution']['candidate']['decision']
    measurements = unseal(load(parent/'measurements.json'), 'hcc-r064-measurements-v1')['observations']
    require(report['correction_patch'] == learn['patch'] and report['correction_feedback'] == learn['feedback']
            and report['correction_value'] is decision['value'], 'Correction provenance')
    require(report['corrected_observation'] == measurements['corrected_observation'] and report['same_observation'] == measurements['same_observation'], 'Observation branch distinction')
    preserved = learn['feedback'] in learn['packet']['document']['engine']['feedback'].values()
    require(report['full_session_preserves_feedback'] is preserved and preserved, 'Session is richer than persistent memory')
    require(report['fresh_sessions_use_memory_only'] is True and report['source_flow'] == 'experiments/exp-46-information-boundary/FLOW.ko.md', 'Source flow binding')
    for path in (parent/'evaluation').glob('*/inference.json'):
        engine = load(path)['execution']['candidate']['packet']['document']['engine']
        require(engine['feedback'] == engine['requests'] == {}, 'Past feedback not carried into fresh sessions')


def main(root, out):
    spec = load(out/'spec.json'); parent = root/spec['parent_run']
    # Existing raw is rechecked; replay is not an extra research run or independent sample.
    plan = unseal(load(parent/'plan.json'), 'hcc-r064-plan-v1')
    original_truth = load(parent/'source/experiments/exp-45-error-retention/reference_worlds.json')['research']
    old = final_audit(parent, plan, original_truth)
    require(old == load(parent/'summary.json'), 'Parent raw replay matches original summary')
    rows = load(out/'counterfactual.json'); memory = load(out/'memory_flow.json')
    check_rows(rows, spec, parent); check_memory(memory, spec, parent)
    rejected = []
    mutations = [
        ('world_truth', lambda r: r['rows'][0]['worlds'][0].update(truth={'e0':False,'e1':False})),
        ('correctness', lambda r: r['rows'][0]['worlds'][0].update(adopted_correct=not r['rows'][0]['worlds'][0]['adopted_correct'])),
        ('memory_binding', lambda r: r['rows'][0].update(memory_sha256='0'*64)),
        ('missing_cell', lambda r: r['rows'].pop()),
        ('duplicate_cell', lambda r: r['rows'].append(deepcopy(r['rows'][0]))),
        ('missing_value', lambda r: r['rows'][0].update(value=None)),
        ('rejected_readout', lambda r: r['rows'][0].update(accepted=False)),
        ('new_sample_claim', lambda r: r.update(new_independent_samples=12)),
    ]
    for name, mutate in mutations:
        bad = deepcopy(rows); mutate(bad)
        try: check_rows(bad, spec, parent)
        except ValueError: rejected.append(name)
        else: raise AssertionError('Mutation not detected: '+name)
    bad = deepcopy(memory); bad['deltas'][1]['changed_top_level'] = []
    try: check_memory(bad, spec, parent)
    except ValueError: rejected.append('hidden_memory_delta')
    else: raise AssertionError('Memory mutation not detected')
    forbidden = FORBIDDEN | {'hcr.learning','hcr.compiler','tools.r065_information.analyze','tools.r064_retention.worker'}
    require(not forbidden & set(sys.modules), 'Verifier imported a producer')
    dump(out/'verification.json', dict(verified=True, existing_packets=12, reference_evaluations=24,
        parent_raw_formula_replay=True, rejected_mutations=rejected, independent_logic=True, independent_process=True,
        independent_researcher=False, new_native_research_executions=0, new_independent_samples=0,
        correction_changes=memory['correction_patch']['changes'], all_pairs_cannot_both_be_correct=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); main(a.repo, a.out)
