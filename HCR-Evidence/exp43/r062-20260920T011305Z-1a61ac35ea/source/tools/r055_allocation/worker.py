"""Frozen drive overrides in an unchanged numerical program."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, fingerprint, load, seal, sha, unseal
from tools.r053_feedback.worker import execute, read_network
from tools.r054_links.worker import masked_program


def produce(run):
    plan = unseal(load(run/'plan.json'), 'hcc-r055-plan-v1')
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
            initial = {group['id']: spec['initial_activation'] for group in original['groups']}
            drives = dict(condition['drives'])
            record = dict(schema='hcc-r055-kernel-v1', condition=condition['id'], mask=mask['id'],
                input_pair=list(condition['input_pair']), original_drives=dict(original_drives),
                parent_record_sha256=sha(path.read_bytes()), source_program_digest=fingerprint(original),
                program=program, drives=drives, initial_state=initial, top_down=True,
                active_top_down_links=active, removed_top_down_links=removed,
                counterfactual=True, native_session_packet=None, proof=None, support=None,
                raw_decision=None, adoption=None, actual_energy_joules=None,
                termination_scope='counterfactual_kernel_termination',
                **execute(program, drives, plan['config'], initial))
            dump(run/('smoke' if smoke else 'study')/condition['id']/(mask['id']+'.json'), seal(record))
        print(condition['id'], 'two fixed masks recorded', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    produce(parser.parse_args().run)


if __name__ == '__main__':
    main()
