"""Fixed public-input interventions; never repair native indices or states."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require, seal, unseal
from tools.r050_review_boundary.worker import execute_session


def intervention(observation, arm):
    require(arm in ('hold', 'revision_only', 'start_edge', 'goal_edge'), 'Unknown arm')
    out = deepcopy(observation)
    if arm != 'hold':
        out['revision'] += 1
    if arm in ('start_edge', 'goal_edge'):
        matches = [e for e in out['edges'] if
                   (e['source'] == out['start'] if arm == 'start_edge'
                    else e['target'] == out['goal'])]
        require(len(matches) == 1, 'Unique structural target required')
        require(matches[0]['score'] == 0.02, 'Expected fixed weak positive score')
        matches[0]['score'] = 1.0
    return out


def produce(run):
    plan = unseal(load(run/'plan.json'), 'hcc-r052-plan-v1')
    smoke = plan['purpose'] == 'implementation_validation'
    output = run/('smoke' if smoke else 'study')
    all_cases = plan['spec']['cases']
    cases = [all_cases[0], all_cases[2]] if smoke else all_cases
    for case in cases:
        first = execute_session(plan, case, case['observation'],
                                output/'progress'/case['id']/'baseline', 'baseline', 0)
        baseline = seal(dict(schema='hcc-r052-baseline-v1', case=case, execution=first))
        dump(output/'baselines'/(case['id']+'.json'), baseline)
        for arm in plan['spec']['arms']:
            obs = intervention(case['observation'], arm)
            receipt = dict(case_id=case['id'], arm=arm, baseline_sha256=baseline['sha256'],
                           observation=obs, measurement_calls=0, automatic_retry=False)
            dump(output/'interventions'/case['id']/(arm+'.json'), receipt)
            execution = None if arm == 'hold' else execute_session(
                plan, case, obs, output/'progress'/case['id']/arm, arm, 1)
            dump(output/'raw'/case['id']/(arm+'.json'), seal(dict(
                schema='hcc-r052-arm-v1', **receipt, execution=execution)))
        print(case['id'], 'recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
