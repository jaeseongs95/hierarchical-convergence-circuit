"""Predeclared interventions; no evaluation or outcome-dependent selection."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require, seal, unseal
from tools.r050_review_boundary.worker import execute_session


def intervention(observation, arm):
    require(arm in ('hold', 'revision_only', 'edge0', 'edge1'), 'Unknown arm')
    out = deepcopy(observation)
    slots = {'hold': [], 'revision_only': [], 'edge0': [0], 'edge1': [1]}[arm]
    if arm != 'hold':
        out['revision'] += 1
    for slot in slots:
        score = out['edges'][slot]['score']
        require(score is not None and score != 0, 'Only public nonzero scores')
        out['edges'][slot]['score'] = 1.0 if score > 0 else -1.0
    return out


def produce(run):
    plan = unseal(load(run / 'plan.json'), 'hcc-r051-plan-v1')
    output = run / ('smoke' if plan['purpose'] == 'implementation_validation' else 'study')
    cases = plan['spec']['cases'][:2] if plan['purpose'] == 'implementation_validation' else plan['spec']['cases']
    for case in cases:
        # Reuse the pinned R050 adapter unchanged. Native IDs retain its r050-
        # prefix; the unique case id starts r051- to distinguish this experiment.
        first = execute_session(plan, case, case['observation'],
                                output / 'progress' / case['id'] / 'baseline', 'baseline', 0)
        baseline = seal(dict(schema='hcc-r051-baseline-v1', case=case, execution=first))
        dump(output / 'baselines' / (case['id'] + '.json'), baseline)
        for arm in plan['spec']['arms']:
            obs = intervention(case['observation'], arm)
            receipt = dict(case_id=case['id'], arm=arm, baseline_sha256=baseline['sha256'],
                           observation=obs, measurement_calls=0, automatic_retry=False)
            dump(output / 'interventions' / case['id'] / (arm + '.json'), receipt)
            # Unconditional fixed matrix: no selection using the resulting answer.
            execution = None if arm == 'hold' else execute_session(
                plan, case, obs, output / 'progress' / case['id'] / arm, arm, 1)
            dump(output / 'raw' / case['id'] / (arm + '.json'), seal(dict(
                schema='hcc-r051-arm-v1', **receipt, execution=execution)))
        print(case['id'], 'recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
