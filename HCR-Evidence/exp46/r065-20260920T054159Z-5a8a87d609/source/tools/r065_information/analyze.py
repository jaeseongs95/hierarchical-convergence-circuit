"""Re-score existing packets against authored worlds; never run a native engine."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, fingerprint, load, require, sha, unseal


def reachable(observation, truth):
    require(set(truth) == {e['id'] for e in observation['edges']}, 'Exact truth domain')
    require(all(type(v) is bool for v in truth.values()), 'Boolean reference facts')
    seen = {observation['start']}
    while True:
        added = {e['target'] for e in observation['edges'] if e['source'] in seen and truth[e['id']]} - seen
        if not added:
            return observation['goal'] in seen
        seen.update(added)


def outcome(value, accepted, truth):
    require(value is None or type(value) is bool, 'Boolean or absent decision')
    require(type(accepted) is bool and type(truth) is bool, 'Typed readout/reference')
    return None if not accepted or value is None else value is truth


def analyze(root, out):
    spec = load(out/'spec.json'); parent = root/spec['parent_run']
    plan = unseal(load(parent/'plan.json'), 'hcc-r064-plan-v1')
    rows = []
    for snapshot in spec['snapshots']:
        memory = load(parent/'memory'/f'{snapshot}.json')
        for gate in (False, True):
            for case in plan['cases']:
                identity = f"{snapshot}-{'on' if gate else 'off'}-{case['id']}"
                path = parent/'evaluation'/identity/'inference.json'
                record = unseal(load(path), 'hcc-r064-inference-v1')
                require(record['plan_sha256'] == fingerprint(plan), 'Parent plan binding')
                execution = record['execution']; candidate = execution['candidate']
                require(candidate is not None, 'Missing candidate is not a successful decision')
                engine = candidate['packet']['document']['engine']
                require(engine['memory'] == memory, 'Exact memory snapshot')
                require(engine['feedback'] == {} and engine['requests'] == {}, 'Fresh evaluation session')
                decision = candidate['decision']; readout = candidate['readout']
                obs = case['observation']
                require(decision['observation_digest'] == fingerprint(obs), 'Public observation identity')
                scores = []
                for name, truth in spec['worlds'].items():
                    target = reachable(obs, truth)
                    scores.append(dict(world=name, truth=truth, reachable=target,
                                       adopted_correct=outcome(decision['value'], readout['accepted'], target)))
                rows.append(dict(identity=identity, snapshot=snapshot, case=case['id'], use_circuits=gate,
                    inference_sha256=sha(path.read_bytes()), packet_sha256=fingerprint(candidate['packet']),
                    observation_sha256=fingerprint(obs), memory_sha256=fingerprint(memory),
                    accepted=readout['accepted'], value=decision['value'],
                    circuit_reuses=decision['cost']['circuit_reuses'], expansions=decision['cost']['expansions'],
                    worlds=scores, both_worlds_correct=all(s['adopted_correct'] is True for s in scores)))
    dump(out/'counterfactual.json', dict(schema='hcc-r065-counterfactual-v1', rows=rows,
        existing_packets=len(rows), reference_evaluations=2*len(rows), new_native_research_executions=0,
        new_independent_samples=0, actual_world_intervention=False, reanalysis=True))
    memories = {s: load(parent/'memory'/f'{s}.json') for s in spec['snapshots']}
    deltas = []
    for a, b in zip(spec['snapshots'], spec['snapshots'][1:]):
        x, y = memories[a], memories[b]
        deltas.append(dict(before=a, after=b, changed_top_level=sorted(k for k in x if x[k] != y[k]),
            circuits_equal=x['circuits'] == y['circuits'], pending_equal=x['pending'] == y['pending'],
            patch=y['patches'][-1], version_before=x['version'], version_after=y['version']))
    learning = unseal(load(parent/'revision/corrected_observation/learning.json'), 'hcc-r064-learning-v1')
    corrected = unseal(load(parent/'revision/corrected_observation/inference.json'), 'hcc-r064-inference-v1')['execution']['candidate']['decision']
    measurements = unseal(load(parent/'measurements.json'), 'hcc-r064-measurements-v1')['observations']
    dump(out/'memory_flow.json', dict(schema='hcc-r065-memory-flow-v1', deltas=deltas,
        persistent_fields=sorted(memories['after_correction']), correction_value=corrected['value'],
        correction_feedback=learning['feedback'], correction_patch=learning['patch'],
        corrected_observation=measurements['corrected_observation'],
        same_observation=measurements['same_observation'],
        full_session_preserves_feedback=learning['feedback'] in learning['packet']['document']['engine']['feedback'].values(),
        fresh_sessions_use_memory_only=True, source_flow='experiments/exp-46-information-boundary/FLOW.ko.md'))


def selftest():
    obs = dict(start='a', goal='c', edges=[dict(id='x', source='a', target='b'), dict(id='y', source='b', target='c')])
    for a in (False, True):
        for b in (False, True):
            require(reachable(obs, dict(x=a, y=b)) is (a and b), 'Synthetic chain truth table')
    require(outcome(False, True, False) is True, 'False is a valid adopted answer')
    require(outcome(None, True, False) is None and outcome(False, False, False) is None, 'Absence/rejection is not correction')
    for bad in ({'x': True}, {'x': 1, 'y': True}):
        try:
            reachable(obs, bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid truth accepted')
    return dict(verified=True, chain_cases=4, readout_boundary_cases=3, invalid_truth_rejected=2, research=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--selftest', action='store_true')
    a = p.parse_args()
    if a.selftest: dump(a.out/'validation/selftest.json', selftest())
    else: analyze(a.repo, a.out)
