"""Propose bounded interval prefixes from original p=.5; independent verification required."""
import argparse
from decimal import Decimal, Context, ROUND_CEILING, ROUND_FLOOR
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import runpy


PLACES = 50
QUANTUM = Decimal('1e-50')
DOWN = Context(prec=80, rounding=ROUND_FLOOR)
UP = Context(prec=80, rounding=ROUND_CEILING)


def grid(box):
    return [(DOWN.quantize(lo, QUANTUM), UP.quantize(hi, QUANTUM)) for lo, hi in box]  # MUTATION_TARGET_GRID


def texts(box):
    return [[format(Decimal(0) if v == 0 else v, '.50f') for v in side] for side in zip(*box)]


def read_pin(repo, record):
    path = repo / record['path']
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record['sha256'] or len(data) != record['bytes']:
        raise ValueError('dependency pin mismatch: ' + record['path'])
    return path, data


def propose(repo, protocol, protocol_hash):
    helper_path, _ = read_pin(repo, protocol['proposal_helper'])
    # Reuse the existing proposal-only arithmetic. The basin checker does not import it.
    helper = runpy.run_path(str(helper_path))
    _, root_protocol_bytes = read_pin(repo, protocol['root_protocol'])
    root_protocol = json.loads(root_protocol_bytes)
    _, root_bytes = read_pin(repo, protocol['root_record'])
    roots = json.loads(root_bytes)['discovery']['certificates']
    for source in protocol['sources']:
        read_pin(repo, source)
    for source in root_protocol['sources']:
        read_pin(repo, source)
    f = root_protocol['foundation']
    helper['pinned'](repo / f['path'], f['sha256'])
    models = []
    for record in protocol['models']:
        bias, matrix, damping = helper['model'](repo, root_protocol, record)
        d = helper['point'](Decimal.from_float(damping))
        one_minus_d = helper['add'](helper['point'](1), helper['neg'](d))
        box = grid([helper['point'](0)] * 5)
        steps = []
        entry = None
        for number in range(protocol['budget']['max_steps_per_model'] + 1):
            lo, hi = texts(box)
            steps.append({'step': number, 'lower': lo, 'upper': hi})
            for index in protocol['targets'][record['model_id']]:
                root = roots[index]
                if root['model_id'] != record['model_id'] or root['state_order'] != protocol['state_order']:
                    raise ValueError('target binding mismatch')
                if all(Decimal(a) < x[0] <= x[1] < Decimal(b)
                       for a, x, b in zip(root['lower'], box, root['upper'])):
                    entry = index
                    break
            if entry is not None or number == protocol['budget']['max_steps_per_model']:
                break
            z = helper['preactivation'](bias, matrix, box)
            image = [helper['tanh_interval'](a) for a in z]
            # Synchronous map: all new coordinates use the same previous box.
            box = grid([helper['add'](helper['mul'](one_minus_d, old), helper['mul'](d, h))
                        for old, h in zip(box, image)])
        models.append({'model_id': record['model_id'], 'state_order': protocol['state_order'],
                       'initial_p': '0.5', 'initial_x': ['0'] * 5, 'steps': steps,
                       'entry_certificate_index': entry,
                       'proposal_status': 'entered_box' if entry is not None else 'budget_exhausted'})
    return {'schema': 'HCCONBasinTrace.v1', 'protocol_sha256': protocol_hash, 'models': models}


def self_test():
    value = Context(prec=80).divide(Decimal(1), Decimal(3))
    low, high = grid([(value, value)])[0]
    assert Fraction(low) <= Fraction(1, 3) <= Fraction(high), 'grid omitted outward ceiling'
    low, high = grid([(value.copy_negate(), value.copy_negate())])[0]
    assert Fraction(low) <= Fraction(-1, 3) <= Fraction(high), 'negative grid omitted outward floor'
    assert grid([(Decimal(0), Decimal(0))])[0] == (Decimal(0), Decimal(0))
    print('PASS proposal outward grid positive/negative/zero checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--protocol-sha256')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not all((args.protocol, args.protocol_sha256, args.output)):
        parser.error('--protocol, --protocol-sha256 and --output are required')
    data = args.protocol.read_bytes()
    if hashlib.sha256(data).hexdigest() != args.protocol_sha256:
        raise ValueError('protocol pin mismatch')
    protocol = json.loads(data)
    if (protocol['schema'] != 'HCCONBasinProtocol.v1'
            or protocol['arithmetic']['grid_decimal_places'] != PLACES
            or protocol['original_initial']['x'] != '0'):
        raise ValueError('unsupported frozen protocol')
    result = propose(args.repo, protocol, args.protocol_sha256)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps([{'model_id': m['model_id'], 'steps': len(m['steps']) - 1,
                       'entry_certificate_index': m['entry_certificate_index']} for m in result['models']]))


if __name__ == '__main__':
    main()
