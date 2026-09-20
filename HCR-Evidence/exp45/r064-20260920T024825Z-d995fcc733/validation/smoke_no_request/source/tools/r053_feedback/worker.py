"""Counterfactual kernel only; never copy or infer native proof/adoption."""
import argparse
from copy import deepcopy
from pathlib import Path
from hcr.codec import plain
from hcr.dynamics import settle
from hcr.model import Config, Cost, Group, Link, Program
from tools.r050_review_boundary.common import dump, fingerprint, load, require, seal, sha, unseal


def parent_path(label, case='r052-c001'):
    return ('study/baselines/' + case + '.json' if label == 'baseline'
            else 'study/raw/' + case + '/' + label + '.json')


def read_network(path):
    # Only the network input is extracted; prior ticks/candidates never select an arm.
    record = load(path)
    events = record['execution']['packet']['document']['events']
    networks = [event['payload'] for event in events if event['event'] == 'r02_network']
    require(len(networks) == 1 and networks[0]['kind'] == 'decision', 'One decision network required')
    return deepcopy(networks[0]['program']), deepcopy(networks[0]['drives'])


def masked_program(program, mask, partition):
    result = deepcopy(program)
    levels = {group['id']: group['level'] for group in program['groups']}
    categories = {tuple(pair): category for category, pairs in partition.items() for pair in pairs}
    pairs = [(link['source'], link['target']) for link in program['links'] if link['kind'] == 'top_down']
    require(len(categories) == sum(map(len, partition.values())) == len(pairs)
            and len(set(pairs)) == len(pairs) and set(pairs) == set(categories),
            'Exact disjoint/exhaustive directed feedback partition')
    active, removed, kept = [], [], []
    for link in program['links']:
        if link['kind'] == 'top_down':
            require(levels[link['source']] == 1 and levels[link['target']] in (0, 1),
                    'Unexpected feedback levels')
            kind = categories[(link['source'], link['target'])]
            require((levels[link['target']] == 0) == (kind == 'edge_local'), 'Partition level mismatch')
            if not mask[kind]:
                removed.append(link)
                continue
            active.append(link)
        kept.append(link)
    result['links'] = kept
    return result, active, removed


def execute(program, drives, config, initial):
    native = Program(tuple(Group(**g) for g in program['groups']),
                     tuple(Link(**link) for link in program['links']),
                     tuple(tuple(path) for path in program['paths']), program['edge_count'])
    cost, ticks = Cost(), []
    state, convergence = settle(native, drives, Config(**config), cost, top_down=True,
        initial=initial, observe=lambda number, values, residual, stable: ticks.append(dict(
            tick=number, state=dict(values), residual=residual, stable_steps=stable)))
    return dict(ticks=ticks, final_state=state, convergence=plain(convergence),
        cost={name: getattr(cost, name) for name in (
            'kernel_ticks', 'group_updates', 'normalization_ops', 'signal_transmissions')})


def produce(run):
    plan = unseal(load(run/'plan.json'), 'hcc-r053-plan-v1')
    spec = plan['spec']
    smoke = plan['purpose'] == 'implementation_validation'
    conditions = spec['implementation_validation_conditions'] if smoke else spec['research_conditions']
    for condition in spec['conditions']:
        if condition['id'] not in conditions:
            continue
        path = run/'parents'/parent_path(condition['parent_label'])
        original, drives = read_network(path)
        for mask in spec['masks']:
            program, active, removed = masked_program(original, mask, spec['feedback_partition'])
            initial = {group['id']: spec['initial_activation'] for group in program['groups']}
            record = dict(schema='hcc-r053-kernel-v1', condition=condition['id'], mask=mask['id'],
                parent_record_sha256=sha(path.read_bytes()), source_program_digest=fingerprint(original),
                program=program, drives=drives, initial_state=initial, top_down=True,
                active_top_down_links=active, removed_top_down_links=removed,
                counterfactual=True, native_session_packet=None, proof=None, support=None,
                raw_decision=None, adoption=None, actual_energy_joules=None,
                termination_scope='counterfactual_kernel_termination',
                **execute(program, drives, plan['config'], initial))
            dump(run/('smoke' if smoke else 'study')/condition['id']/(mask['id']+'.json'), seal(record))
        print(condition['id'], 'four fixed masks recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
