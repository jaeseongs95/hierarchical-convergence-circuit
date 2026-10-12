"""동결 ON 모델의 rational box 인증. 생산 모듈과 후보 생성기를 읽지 않는다."""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import sys

ORDER = ['e:0', 'e:1', 'p:0:0', 'p:0:1', 'goal']
FIELDS = {'schema', 'protocol_sha256', 'model_id', 'state_order', 'lower', 'upper', 'weights'}
DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z')
DEGREE = 96
PLACES = 40


def rational(text):
    if (not isinstance(text, str) or len(text) > 200
            or not DECIMAL.fullmatch(text) or text == '-0'):
        raise ValueError('invalid canonical decimal')
    return Q(text)


def outward(value, upper=False):
    scale = 10 ** PLACES
    numerator = value.numerator * scale
    integer = -((-numerator) // value.denominator) if upper else numerator // value.denominator
    sign = '-' if integer < 0 else ''
    whole, decimal = divmod(abs(integer), scale)
    return f'{sign}{whole}.{decimal:0{PLACES}d}'


def exp_positive(u, degree=DEGREE):
    if u < 0 or degree < 0 or u >= degree + 2:
        raise ValueError('invalid Taylor tail ratio')
    term = total = Q(1)
    for k in range(1, degree + 1):
        term *= u / k
        total += term
    next_term = term * u / (degree + 1)
    return total, total + next_term / (1 - u / (degree + 2))


def tanh_bounds(x):
    if x == 0:
        return Q(0), Q(0)
    if x < 0:
        lower, upper = tanh_bounds(-x)
        return -upper, -lower
    lower, upper = exp_positive(2 * x)
    return (lower - 1) / (lower + 1), (upper - 1) / (upper + 1)


def slope_upper(lower, upper):
    if lower <= 0 <= upper:
        return Q(1)
    closest = min(abs(lower), abs(upper))
    tanh_lower, _ = tanh_bounds(closest)
    return 1 - tanh_lower ** 2


def check_box(b, G, d, lower, upper, weights):
    n = len(b)
    if (n == 0 or len(G) != n or any(len(row) != n for row in G)
            or any(len(v) != n for v in (lower, upper, weights))):
        return {'accepted': False, 'reason': 'dimension mismatch'}
    if not 0 < d <= 1:
        return {'accepted': False, 'reason': 'invalid damping'}
    if any(not -1 < lo < hi < 1 for lo, hi in zip(lower, upper)):
        return {'accepted': False, 'reason': 'invalid box domain'}
    if any(not 0 < w <= 100000000 for w in weights):
        return {'accepted': False, 'reason': 'invalid weight domain'}
    h_lower, h_upper, slopes = [], [], []
    for i in range(n):
        lo = b[i] + sum(min(G[i][j] * lower[j], G[i][j] * upper[j]) for j in range(n))
        hi = b[i] + sum(max(G[i][j] * lower[j], G[i][j] * upper[j]) for j in range(n))
        h_lower.append(tanh_bounds(lo)[0])
        h_upper.append(tanh_bounds(hi)[1])
        slopes.append(slope_upper(lo, hi))
    result = {
        'accepted': False,
        'H_lower': [outward(v) for v in h_lower],
        'H_upper': [outward(v, True) for v in h_upper],
        'slope_upper': [outward(v, True) for v in slopes],
    }
    # MUTATION_TARGET_SELF_INCLUSION
    if any(not lower[i] < h_lower[i] <= h_upper[i] < upper[i] for i in range(n)):
        return dict(result, reason='strict self-inclusion failed')
    q_h = max(slopes[i] * sum(abs(G[i][j]) * weights[j] for j in range(n)) / weights[i]
              for i in range(n))
    q_f = 1 - d + d * q_h
    result.update(qH_upper=outward(q_h, True), qF_upper=outward(q_f, True),
                  exact_qH_lt_one=q_h < 1, exact_qF_lt_one=q_f < 1)
    if not q_h < 1 or not q_f < 1:
        return dict(result, reason='exact contraction failed')
    if any(not lower[i] < Q(result['H_lower'][i]) <= Q(result['H_upper'][i]) < upper[i]
           for i in range(n)):
        return dict(result, reason='public self-inclusion insufficient')
    if Q(result['qH_upper']) >= 1 or Q(result['qF_upper']) >= 1:
        return dict(result, reason='public contraction insufficient')
    return dict(result, accepted=True, reason='certified existence, uniqueness in box and local damped stability')


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def decode(data):
    def invalid_constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(data, object_pairs_hook=no_duplicates, parse_constant=invalid_constant)


def pinned(repo, relative, expected_hash, expected_bytes=None):
    path = (repo / relative).resolve()
    if not path.is_relative_to(repo.resolve()):
        raise ValueError('source path outside repository')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError('source hash mismatch: ' + relative)
    if expected_bytes is not None and len(data) != expected_bytes:
        raise ValueError('source byte count mismatch: ' + relative)
    return data


def binary(value):
    if type(value) not in (int, float):
        raise ValueError('invalid primitive number')
    return Q(*float(value).as_integer_ratio())


def load_models(repo, protocol):
    if (protocol.get('schema') != 'HCCONRootProtocol.v1' or protocol.get('state_order') != ORDER
            or set(protocol['certificate_schema']['fields']) != FIELDS
            or protocol['checker']['taylor_degree'] != DEGREE
            or protocol['checker']['public_decimal_places'] != PLACES):
        raise ValueError('unsupported protocol')
    foundation = protocol['foundation']
    pinned(repo, foundation['path'], foundation['sha256'])
    for source in protocol['sources']:
        pinned(repo, source['path'], source['sha256'], source['bytes'])
    config_source = next(s for s in protocol['sources'] if s['path'].endswith('/frozen_spec.json'))
    config = decode(pinned(repo, config_source['path'], config_source['sha256']))['config']['kernel']
    expected = {'temperature': 1.0, 'damping': 0.45, 'self_excitation': 0.25, 'inhibition': 0.2}
    if any(binary(config[key]) != binary(value) for key, value in expected.items()):
        raise ValueError('unexpected primitive config')
    T, d = binary(config['temperature']), binary(config['damping'])
    diagonal = (binary(config['self_excitation']) + binary(config['inhibition'])) / 2
    models = {}
    expected_ids = ['swapped-s003-td1-off', 'swapped-s004-td1-off']
    if [m['model_id'] for m in protocol['models']] != expected_ids:
        raise ValueError('unexpected model inventory')
    for model in protocol['models']:
        raw = decode(pinned(repo, model['raw_path'], model['raw_sha256'], model['raw_bytes']))
        if raw['cell']['id'] != model['model_id'] or raw['cell']['top_down'] is not True:
            raise ValueError('raw cell binding mismatch')
        events = raw['execution']['packet']['document']['events']
        network = next(e['payload'] for e in events
                       if e.get('event') == 'r02_network' and e['payload'].get('kind') == 'decision')
        program = network['program']
        groups = program['groups']
        ids = [g['id'] for g in groups]
        links = program['links']
        if (network['top_down'] is not True or len(groups) != 7 or len(set(ids)) != 7
                or set(ids) != set(ORDER + ['e:2', 'e:3']) or len(links) != 8):
            raise ValueError('unexpected first-network structure')
        index = {name: i for i, name in enumerate(ORDER)}
        biases = {g['id']: binary(g['bias']) for g in groups}
        drives = network['drives']
        if not set(drives) <= set(ids):
            raise ValueError('unknown drive ID')
        b = [(biases[name] + binary(drives.get(name, 0.0))) / T for name in ORDER]
        G = [[Q(0) for _ in ORDER] for _ in ORDER]
        kinds = []
        for link in links:
            source, target, kind = link['source'], link['target'], link['kind']
            if source not in index or target not in index or kind not in ('support', 'top_down'):
                raise ValueError('removed states coupled or invalid link')
            G[index[target]][index[source]] += binary(link['weight']) / T
            kinds.append(kind)
        if kinds.count('support') != 4 or kinds.count('top_down') != 4:
            raise ValueError('unexpected link kinds')
        for i in range(len(ORDER)):
            G[i][i] += diagonal / T
        models[model['model_id']] = (b, G, d)
    return models


def check_certificate(certificate, index, models, protocol_sha256):
    result = {'index': index, 'model_id': certificate.get('model_id') if isinstance(certificate, dict) else None}
    try:
        if (not isinstance(certificate, dict) or set(certificate) != FIELDS
                or certificate['schema'] != 'HCCONRootBox.v1'
                or certificate['protocol_sha256'] != protocol_sha256
                or certificate['state_order'] != ORDER
                or not isinstance(certificate['model_id'], str)
                or certificate['model_id'] not in models):
            raise ValueError('certificate binding or schema mismatch')
        vectors = []
        for key in ('lower', 'upper', 'weights'):
            values = certificate[key]
            if not isinstance(values, list) or len(values) != len(ORDER):
                raise ValueError('invalid certificate vector')
            vectors.append([rational(v) for v in values])
        result.update(check_box(*models[certificate['model_id']], *vectors))
        return result, (vectors[0], vectors[1]) if result['accepted'] else None
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return dict(result, accepted=False, reason=str(error)), None


def disjoint(a, b):
    return any(a[1][i] < b[0][i] or b[1][i] < a[0][i] for i in range(len(a[0])))


def check_all(document, models, protocol_sha256):
    if not isinstance(document, dict) or set(document) != {'certificates'} or not isinstance(document['certificates'], list):
        raise ValueError('input must contain only certificates array')
    certificates = document['certificates']
    if len(certificates) > 6:
        raise ValueError('certificate count exceeds frozen six attempts')
    results, boxes = [], {}
    for index, certificate in enumerate(certificates):
        result, box = check_certificate(certificate, index, models, protocol_sha256)
        results.append(result)
        if box is not None:
            boxes[index] = box
    counts, chosen = {}, {}
    # ponytail: 최대 6개라 전체 열거한다. 더 큰 인증 집합은 별도 protocol이 필요하다.
    for model_id in models:
        indices = [r['index'] for r in results if r['model_id'] == model_id and r['accepted']]
        best = ()
        for size in range(len(indices), 0, -1):
            best = next((subset for subset in combinations(indices, size)
                         if all(disjoint(boxes[i], boxes[j]) for i, j in combinations(subset, 2))), ())
            if best:
                break
        chosen[model_id], counts[model_id] = list(best), len(best)
    return {'schema': 'HCCONRootCheck.v1', 'protocol_sha256': protocol_sha256,
            'results': results, 'stable_root_lower_bounds': counts,
            'disjoint_certificate_indices': chosen,
            'claim_boundary': '존재·상자 내부 유일성·국소 안정성만 인증; 전체 root 수와 native 초기 .5 basin은 UNKNOWN'}


def self_test():
    def require(condition, label):
        if not condition:
            raise AssertionError(label)
    require(exp_positive(Q(1), 1) == (Q(2), Q(11, 4)), 'Taylor n1')
    require(exp_positive(Q(1), 3) == (Q(8, 3), Q(87, 32)), 'Taylor n3')
    require(exp_positive(Q(0)) == (Q(1), Q(1)), 'Taylor zero')
    pos, neg = tanh_bounds(Q(1)), tanh_bounds(Q(-1))
    require(neg == (-pos[1], -pos[0]), 'negative oddness')
    require(tanh_bounds(Q(0)) == (Q(0), Q(0)), 'tanh zero')
    require(slope_upper(Q(-1), Q(2)) == 1, 'crossing-zero slope')
    require(slope_upper(Q(1), Q(2)) == slope_upper(Q(-2), Q(-1)) < 1, 'slope endpoints')
    try:
        exp_positive(Q(98))
    except ValueError:
        pass
    else:
        raise AssertionError('Taylor ratio boundary')
    require(not check_box([Q(0)], [[Q(0)]], Q(1, 2), [Q(0)], [Q(1, 2)], [Q(1)])['accepted'], 'strict equality')
    require(not check_box([Q(0)], [[Q(0)]], Q(1, 2), [Q(4, 5)], [Q(9, 10)], [Q(1)])['accepted'], 'self-inclusion bypass control')
    require(not check_box([Q(0)], [[Q(1)]], Q(1, 2), [Q(-1, 2)], [Q(1, 2)], [Q(1)])['accepted'], 'q equality')
    accepted = check_box([Q(0)], [[Q(0)]], binary(0.45), [Q(-1, 2)], [Q(1, 2)], [Q(1)])
    require(accepted['accepted'] and accepted['exact_qF_lt_one'], 'valid box')
    exact_qf = 1 - binary(0.45)
    require(Q(accepted['qF_upper']) >= exact_qf and Q(accepted['qF_upper']) < 1, 'exact qF outward')
    require(accepted['qF_upper'] == outward(exact_qf, True), 'qF serialization')
    for text in ('', '+1', ' 1', '1 ', '01', '-0', '-0.0', '0.10', '1.', '.1', '1e-3', 'NaN', 'Inf', '0.' + '1' * 199):
        try:
            rational(text)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid encoding: ' + text)
    require(rational('-0.1') == Q(-1, 10) and rational('100000000') == 100000000, 'valid encoding')
    tiny = Q(1, 10 ** 41)
    require(Q(outward(-tiny)) <= -tiny <= Q(outward(-tiny, True)), 'negative outward')
    require(Q(outward(1 - tiny, True)) == 1, 'rounded contraction boundary')
    require(not check_box([Q(0)], [[1 - tiny]], Q(1, 2), [Q(-1, 2)], [Q(1, 2)], [Q(1)])['accepted'], 'public q boundary')
    require(not disjoint(([Q(0)], [Q(1)]), ([Q(1)], [Q(2)])), 'touching boxes')
    require(disjoint(([Q(0)], [Q(1)]), ([Q(2)], [Q(3)])), 'strictly disjoint boxes')
    for data in ('{"a":1,"a":2}', '{"a":NaN}'):
        try:
            decode(data)
        except ValueError:
            pass
        else:
            raise AssertionError('strict JSON decoding')
    return {'schema': 'HCCONRootCheckSelfTest.v1', 'passed': True,
            'exact_qF_synthetic': str(exact_qf), 'public_qF_upper_synthetic': accepted['qF_upper']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False))
        return
    if any(getattr(args, name) is None for name in ('repo', 'protocol', 'protocol_sha256', 'input', 'output')):
        parser.error('all five file-mode arguments are required')
    data = Path(args.protocol).read_bytes()
    if hashlib.sha256(data).hexdigest() != args.protocol_sha256:
        raise ValueError('protocol hash mismatch')
    models = load_models(Path(args.repo), decode(data))
    result = check_all(decode(Path(args.input).read_bytes()), models, args.protocol_sha256)
    # 기존 결과와 첫 실패 기록을 덮어쓰지 않는다.
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(1)
