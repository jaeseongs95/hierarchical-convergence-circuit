"""Single coordinate intervention followed by uninterrupted existing kernel ticks."""
import argparse
from pathlib import Path
from hcr.dynamics import tick
from hcr.model import Config, Cost, Group, Link, Program
from tools.r050_review_boundary.common import dump, load, require, seal, sha, unseal
from tools.r053_feedback.worker import read_network


def execute(program, drives, config, anchor_state, arm, horizon):
    state = dict(anchor_state)
    if arm['coordinate'] is not None:
        state[arm['coordinate']] += arm['delta']
    require(all(0 <= v <= 1 for v in state.values()), 'Intervention outside state range; no clipping')
    initial = dict(state)
    native = Program(tuple(Group(**g) for g in program['groups']),
                     tuple(Link(**link) for link in program['links']),
                     tuple(tuple(path) for path in program['paths']), program['edge_count'])
    cfg, cost, stable, ticks = Config(**config), Cost(), 0, []
    for number in range(1, horizon + 1):
        nxt = tick(native, state, drives, cfg, cost, top_down=True)
        residual = max(abs(nxt[k] - state[k]) for k in state)
        stable = stable + 1 if residual <= cfg.residual_tolerance else 0
        ticks.append(dict(tick=number, state=dict(nxt), residual=residual, stable_steps=stable))
        state = nxt
    return dict(initial_state=initial, final_state=state, ticks=ticks,
                cost={k: getattr(cost, k) for k in ('kernel_ticks', 'group_updates',
                      'normalization_ops', 'signal_transmissions')})


def produce(run):
    plan = unseal(load(run/'plan.json'), 'hcc-r059-plan-v1')
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
            record = dict(schema='hcc-r059-kernel-v1', condition=condition, arm=arm,
                anchor_record_sha256=sha(path.read_bytes()), anchor_tick=512,
                program=program, drives=anchor['drives'], anchor_state=anchor['final_state'],
                intervention=spec['intervention'], horizon=spec['horizon'], top_down=True,
                completion='fixed_horizon_completed', counterfactual=True,
                **{key: None for key in spec['unmeasured']},
                **execute(program, anchor['drives'], plan['config'], anchor['final_state'], arm, spec['horizon']))
            dump(run/('smoke' if smoke else 'study')/condition/(arm['id']+'.json'), seal(record))
        print(condition, 'coordinate interventions recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
