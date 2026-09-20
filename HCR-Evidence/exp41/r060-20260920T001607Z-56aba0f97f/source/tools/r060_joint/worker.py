"""Simultaneous coordinate intervention followed by uninterrupted existing kernel ticks."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require, seal, sha, unseal
from tools.r053_feedback.worker import read_network


def execute(program, drives, config, anchor_state, arm, horizon):
    # Reuse the fixed-horizon kernel loop after the explicitly recorded vector intervention.
    from tools.r059_recovery.worker import execute as run_ticks
    require(set(arm['deltas']) == set(anchor_state), 'Exact coordinate inventory')
    state = {k: v + arm['deltas'][k] for k, v in anchor_state.items()}
    require(all(0 <= v <= 1 for v in state.values()), 'Intervention outside state range; no clipping')
    return run_ticks(program, drives, config, state,
                     dict(coordinate=None, delta=0.0), horizon)


def produce(run):
    plan = unseal(load(run/'plan.json'), 'hcc-r060-plan-v1')
    spec = plan['spec']
    smoke = plan['purpose'] == 'implementation_validation'
    program, _ = read_network(run/'parents'/spec['program_parent'])
    for condition in spec['conditions']:
        path = run/'anchors'/f'study/{condition}/full.json'
        anchor = unseal(load(path), 'hcc-r058-kernel-v1')
        require(anchor['program'] == program and anchor['horizon'] == 512, 'Unchanged full program/anchor')
        for arm in spec['arms']:
            if smoke and arm['id'] not in spec['smoke_arms']:
                continue
            record = dict(schema='hcc-r060-kernel-v1', condition=condition, arm=arm,
                anchor_record_sha256=sha(path.read_bytes()), anchor_tick=512,
                program=program, drives=anchor['drives'], anchor_state=anchor['final_state'],
                intervention=spec['intervention'], horizon=spec['horizon'], top_down=True,
                completion='fixed_horizon_completed', counterfactual=True,
                **{key: None for key in spec['unmeasured']},
                **execute(program, anchor['drives'], plan['config'], anchor['final_state'], arm, spec['horizon']))
            dump(run/('smoke' if smoke else 'study')/condition/(arm['id']+'.json'), seal(record))
        print(condition, 'joint interventions recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
