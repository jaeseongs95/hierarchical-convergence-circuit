"""Preserve first termination, then continue the unchanged kernel to a fixed horizon."""
import argparse
from copy import deepcopy
from pathlib import Path
from hcr.dynamics import tick
from hcr.model import Config, Cost, Group, Link, Program
from tools.r050_review_boundary.common import dump, fingerprint, load, require, seal, sha, unseal
from tools.r053_feedback.worker import execute, read_network
from tools.r054_links.worker import masked_program


def execute_continued(program, drives, config, initial, horizon):
    require(type(horizon) is int and horizon > config['max_ticks'], 'Horizon must exceed original budget')
    prefix = execute(program, drives, config, initial)
    marker = {key: deepcopy(prefix[key]) for key in ('final_state', 'convergence', 'cost')}
    native = Program(tuple(Group(**g) for g in program['groups']),
                     tuple(Link(**link) for link in program['links']),
                     tuple(tuple(path) for path in program['paths']), program['edge_count'])
    cfg = Config(**config)
    cost = Cost(**prefix['cost'])
    state = dict(prefix['final_state'])
    stable = prefix['convergence']['stable_steps']
    ticks = list(prefix['ticks'])
    for number in range(len(ticks)+1, horizon+1):
        nxt = tick(native, state, drives, cfg, cost, top_down=True)
        residual = max(abs(nxt[key]-state[key]) for key in state)
        stable = stable+1 if residual <= cfg.residual_tolerance else 0
        ticks.append(dict(tick=number, state=dict(nxt), residual=residual, stable_steps=stable))
        state = nxt
    totals = {key: getattr(cost, key) for key in prefix['cost']}
    return dict(ticks=ticks, final_state=state, first_termination=marker,
                cost=totals, continuation_cost={key: totals[key]-marker['cost'][key] for key in totals},
                horizon=horizon, completion='fixed_horizon_completed')


def produce(run):
    plan = unseal(load(run/'plan.json'), 'hcc-r058-plan-v1')
    spec = plan['spec']
    smoke = plan['purpose'] == 'implementation_validation'
    ids = spec['implementation_validation_conditions'] if smoke else spec['research_conditions']
    path = run/'parents'/spec['program_parent']
    original, original_drives = read_network(path)
    for condition in spec['conditions']:
        if condition['id'] not in ids:
            continue
        for mask in spec['masks']:
            program, active, removed = masked_program(original, mask, spec['feedback_links'])
            initial = {group['id']: condition['initial_activation'] for group in original['groups']}
            drives = dict(condition['drives'])
            record = dict(schema='hcc-r058-kernel-v1', condition=condition['id'], mask=mask['id'],
                orientation=condition['orientation'], initial_activation=condition['initial_activation'],
                input_pair=list(condition['input_pair']), original_drives=dict(original_drives),
                parent_record_sha256=sha(path.read_bytes()), source_program_digest=fingerprint(original),
                program=program, drives=drives, initial_state=initial, top_down=True,
                active_top_down_links=active, removed_top_down_links=removed,
                counterfactual=True, native_session_packet=None, proof=None, support=None,
                raw_decision=None, adoption=None, actual_energy_joules=None,
                termination_scope='counterfactual_fixed_horizon',
                continuation_intervention=dict(spec['continuation_intervention']),
                **execute_continued(program, drives, plan['config'], initial, spec['horizon']))
            dump(run/('smoke' if smoke else 'study')/condition['id']/(mask['id']+'.json'), seal(record))
        print(condition['id'], 'two fixed-horizon masks recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
