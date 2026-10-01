"""Produce native sessions without evaluator imports or answer labels."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require, seal, unseal
from tools.r050_review_boundary.worker import execute_session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--arm', choices=['full', 'drop_P_prefix'], required=True)
    args = parser.parse_args()
    plan = unseal(load(args.run/'plan.json'), 'hcc-r062-plan-v1')
    for case in plan['cases']:
        require(set(case) == {'id', 'top_down', 'observation'}, 'Public case fields only')
        execution = execute_session(plan, case, case['observation'],
            args.run/'raw'/args.arm/case['id']/'progress', args.arm, 0)
        dump(args.run/'raw'/args.arm/case['id']/'execution.json', seal(dict(
            schema='hcc-r062-execution-v1', plan_sha256=load(args.run/'plan.json')['sha256'],
            arm=args.arm, case_id=case['id'], execution=execution,
            automatic_retry=False, learned=False, actual_energy_joules=None)))
        print(case['id'], args.arm, 'recorded', flush=True)


if __name__ == '__main__':
    main()
