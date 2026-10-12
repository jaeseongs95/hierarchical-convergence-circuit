"""Frozen ON root discovery and Decimal interval proposals; not final proofs.

Run with --protocol, --protocol-sha256 and --output. No HCC runtime imports.
The independently implemented Fraction checker makes the certification verdict.
"""
import argparse
from decimal import Context, Decimal, ROUND_CEILING, ROUND_FLOOR
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


PRECISION = 80
NEAR = Context(prec=PRECISION)
DOWN = Context(prec=PRECISION, rounding=ROUND_FLOOR)
UP = Context(prec=PRECISION, rounding=ROUND_CEILING)


def decimal_text(value):
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return '0' if value == 0 else text


def point(value):
    value = Decimal(value)
    return value, value


def add(a, b):
    return DOWN.add(a[0], b[0]), UP.add(a[1], b[1])


def neg(a):
    return a[1].copy_negate(), a[0].copy_negate()


def mul(a, b):
    return (min(DOWN.multiply(x, y) for x in a for y in b),
            max(UP.multiply(x, y) for x in a for y in b))


def div(a, b):
    if b[0] <= 0 <= b[1]:
        raise ValueError('interval division crosses zero')
    return (min(DOWN.divide(x, y) for x in a for y in b),
            max(UP.divide(x, y) for x in a for y in b))


def exp_interval(a):
    # Decimal.exp rounds to nearest even for directed contexts. Widen explicitly.
    lo, hi = NEAR.exp(a[0]), NEAR.exp(a[1])
    return NEAR.next_minus(lo), NEAR.next_plus(hi)  # MUTATION_TARGET_EXP


def tanh_interval(a):
    e = exp_interval(mul(point(2), a))
    # Use endpoint monotonicity to avoid dependency widening.
    low = div(add(point(e[0]), point(-1)), add(point(e[0]), point(1)))[0]
    high = div(add(point(e[1]), point(-1)), add(point(e[1]), point(1)))[1]
    return low, high


def slope_upper(z):
    if z[0] <= 0 <= z[1]:
        return Decimal(1)
    nearest = z[0] if z[0] > 0 else z[1].copy_negate()
    lower = max(Decimal(0), tanh_interval(point(nearest))[0])
    return UP.subtract(Decimal(1), DOWN.multiply(lower, lower))


def pinned(path, sha256, size=None):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha256 or (size is not None and len(data) != size):
        raise ValueError('source pin mismatch: ' + str(path))
    return json.loads(data) if path.suffix == '.json' else data


def model(repo, protocol, record):
    raw = pinned(repo / record['raw_path'], record['raw_sha256'], record['raw_bytes'])
    events = raw['execution']['packet']['document']['events']
    kernel = next(e for e in events if e['event'] == 'r02_engine_created')['payload']['config']['kernel']
    network = next(e for e in events if e['event'] == 'r02_network' and e['payload'].get('kind') == 'decision')['payload']
    groups, links = network['program']['groups'], network['program']['links']
    order = protocol['state_order']
    if not network['top_down'] or len(groups) != 7 or len(links) != 8:
        raise ValueError('unexpected first decision network')
    if [kernel[k] for k in ('temperature', 'damping', 'self_excitation', 'inhibition')] != [1.0, .45, .25, .2]:
        raise ValueError('unexpected kernel')
    if set(g['id'] for g in groups) != set(order) | {'e:2', 'e:3'}:
        raise ValueError('unexpected group set')
    if any(e['source'] not in order or e['target'] not in order for e in links):
        raise ValueError('removed states are coupled')
    # Each binary64 primitive has an exact terminating Decimal representation.
    D = Decimal.from_float
    biases = {g['id']: D(g['bias']) for g in groups}
    bias = [add(point(biases[k]), point(D(network['drives'].get(k, 0.0)))) for k in order]
    matrix = [[point(0) for _ in order] for _ in order]
    for e in links:
        i, j = order.index(e['target']), order.index(e['source'])
        matrix[i][j] = add(matrix[i][j], point(D(e['weight'])))
    half_k = div(add(point(D(kernel['self_excitation'])), point(D(kernel['inhibition']))), point(2))
    for i in range(5):
        matrix[i][i] = add(matrix[i][i], half_k)
    temperature = point(D(kernel['temperature']))
    bias = [div(x, temperature) for x in bias]
    matrix = [[div(x, temperature) for x in row] for row in matrix]
    return bias, matrix, kernel['damping']


def preactivation(bias, matrix, box):
    return [sum_intervals([b] + [mul(g, x) for g, x in zip(row, box)]) for b, row in zip(bias, matrix)]


def sum_intervals(values):
    result = point(0)
    for value in values:
        result = add(result, value)
    return result


def discover(bias, matrix, damping, seed, settings):
    b = [float(x[0]) for x in bias]
    g = [[float(x[0]) for x in row] for row in matrix]
    x = [float(seed)] * 5
    reason = 'iteration_budget'
    for count in range(1, settings['max_iterations'] + 1):
        h = [math.tanh(v + sum(a * t for a, t in zip(row, x))) for v, row in zip(b, g)]
        nxt = [(1 - damping) * a + damping * c for a, c in zip(x, h)]
        change = max(abs(a - c) for a, c in zip(nxt, x))
        x = nxt
        if not all(map(math.isfinite, x)):
            raise ValueError('nonfinite discovery')
        if change <= settings['step_tolerance']:
            reason = 'step_tolerance'
            break
    h = [math.tanh(v + sum(a * t for a, t in zip(row, x))) for v, row in zip(b, g)]
    jacobian = [[(1 - h[i] ** 2) * a for a in row] for i, row in enumerate(g)]
    weights = [1.0] * 5
    for _ in range(settings['weight_iterations']):
        weights = [1 + sum(a * w for a, w in zip(row, weights)) for row in jacobian]
        if any(not math.isfinite(w) or w <= 0 or w > settings['weight_max'] for w in weights):
            return {'seed': seed, 'iterations': count, 'stop_reason': reason, 'center': x,
                    'last_step_change': change, 'proposal_status': 'invalid_weight'}, None
    center = [Decimal.from_float(a) for a in x]
    ws = [Decimal.from_float(w) for w in weights]
    radius = [mul(point(settings['base_radius']), point(w)) for w in ws]
    box = [add(point(c), (r[1].copy_negate(), r[1])) for c, r in zip(center, radius)]
    zs = preactivation(bias, matrix, box)
    image = [tanh_interval(z) for z in zs]
    q = max(sum_intervals([div(mul(point(slope_upper(z)), mul((min(a[0].copy_abs(), a[1].copy_abs()), max(a[0].copy_abs(), a[1].copy_abs())), point(w))), point(ws[i]))
                          for a, w in zip(row, ws)])[1] for i, (z, row) in enumerate(zip(zs, matrix)))
    attempt = {'seed': seed, 'iterations': count, 'stop_reason': reason, 'center': x,
               'last_step_change': change, 'proposal_status': 'submitted',
               'diagnostic_strict_self_inclusion': all(a[0] < h[0] and h[1] < a[1] for a, h in zip(box, image)),
               'diagnostic_qH_upper': decimal_text(q),
               'diagnostic_H_bounds': [[decimal_text(y) for y in h] for h in image]}
    return attempt, {'lower': [decimal_text(a[0]) for a in box],
                     'upper': [decimal_text(a[1]) for a in box],
                     'weights': [decimal_text(w) for w in ws]}


def self_test():
    # Independent exact Taylor enclosure at 1 is narrower than 80-digit rounding.
    s, term = Fraction(1), Fraction(1)
    for n in range(1, 65):
        term /= n
        s += term
    tail = term / 65 / (1 - Fraction(1, 66))
    lo, hi = exp_interval(point(1))
    assert Fraction(lo) <= s and s + tail <= Fraction(hi), 'exp enclosure lost directed neighbours'
    assert add(point(1), point(-1)) == point(0)
    assert slope_upper((Decimal(-1), Decimal(1))) == 1
    for a in ('0', '1.5', '-0.25'):
        assert decimal_text(Decimal(a)) == a
    print('PASS generator independent exp enclosure and interval boundary checks')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--protocol', type=Path)
    ap.add_argument('--protocol-sha256')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not all((args.protocol, args.protocol_sha256, args.output)):
        ap.error('--protocol, --protocol-sha256 and --output are required')
    protocol = pinned(args.protocol, args.protocol_sha256)
    pinned(args.repo / protocol['foundation']['path'], protocol['foundation']['sha256'])
    for record in protocol['sources']:
        pinned(args.repo / record['path'], record['sha256'], record['bytes'])
    attempts, certificates = [], []
    for record in protocol['models']:
        bias, matrix, damping = model(args.repo, protocol, record)
        for seed in protocol['discovery']['seeds']:
            attempt, certificate = discover(bias, matrix, damping, seed, protocol['discovery'])
            attempt.update(model_id=record['model_id'], attempt_index=len(attempts))
            if certificate is not None:
                attempt['certificate_index'] = len(certificates)
                certificate.update(schema='HCCONRootBox.v1', protocol_sha256=args.protocol_sha256,
                                   model_id=record['model_id'], state_order=protocol['state_order'])
                certificates.append(certificate)
            attempts.append(attempt)
    result = {'schema': 'HCCONRootDiscovery.v1', 'protocol_sha256': args.protocol_sha256,
              'attempts': attempts, 'certificates': certificates,
              'notice': 'Decimal diagnostics and finite floating discovery are proposals, not final proofs.'}
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'attempts': len(attempts), 'certificates': len(certificates)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
