"""Predeclared single-link removals; numerical outcomes only."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, fingerprint, load, require, seal, sha, unseal
from tools.r053_feedback.worker import execute, parent_path, read_network


def masked_program(original, mask, feedback_links):
    pair_to_id = {(item['source'], item['target']): item['id'] for item in feedback_links}
    pairs = [(link['source'], link['target']) for link in original['links'] if link['kind'] == 'top_down']
    require(len(pairs) == len(set(pairs)) == len(pair_to_id) == len(feedback_links)
            and set(pairs) == set(pair_to_id), 'Exact feedback identity set required')
    removed_ids = mask['remove']
    require(len(removed_ids) == len(set(removed_ids))
            and set(removed_ids) <= set(pair_to_id.values()), 'Invalid removal IDs')
    program = deepcopy(original)
    kept, active, removed = [], [], []
    for link in original['links']:
        if link['kind'] == 'top_down':
            if pair_to_id[(link['source'],link['target'])] in removed_ids:
                removed.append(deepcopy(link))
                continue
            active.append(deepcopy(link))
        kept.append(deepcopy(link))
    program['links'] = kept
    return program, active, removed


def produce(run):
    plan = unseal(load(run/'plan.json'),'hcc-r054-plan-v1')
    spec = plan['spec']
    smoke = plan['purpose'] == 'implementation_validation'
    ids = spec['implementation_validation_conditions'] if smoke else spec['research_conditions']
    for condition in spec['conditions']:
        if condition['id'] not in ids:
            continue
        path = run/'parents'/parent_path(condition['parent_label'])
        original, drives = read_network(path)
        for mask in spec['masks']:
            program, active, removed = masked_program(original,mask,spec['feedback_links'])
            initial = {group['id']:spec['initial_activation'] for group in original['groups']}
            record = dict(schema='hcc-r054-kernel-v1',condition=condition['id'],mask=mask['id'],
                parent_record_sha256=sha(path.read_bytes()),source_program_digest=fingerprint(original),
                program=program,drives=drives,initial_state=initial,top_down=True,
                active_top_down_links=active,removed_top_down_links=removed,
                counterfactual=True,native_session_packet=None,proof=None,support=None,
                raw_decision=None,adoption=None,actual_energy_joules=None,
                termination_scope='counterfactual_kernel_termination',
                **execute(program,drives,plan['config'],initial))
            dump(run/('smoke' if smoke else 'study')/condition['id']/(mask['id']+'.json'),seal(record))
        print(condition['id'],'six fixed masks recorded',flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,required=True)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
