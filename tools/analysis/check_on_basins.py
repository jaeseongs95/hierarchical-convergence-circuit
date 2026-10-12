"""동결 first-ON 실수 모델의 초기값 basin 전이를 독립 Fraction 산술로 검산한다."""
from __future__ import annotations

import argparse
import ast
from fractions import Fraction as Q
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
import runpy
import sys

ORDER = ['e:0', 'e:1', 'p:0:0', 'p:0:1', 'goal']
ALL_ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
MODEL_IDS = ['swapped-s003-td1-off', 'swapped-s004-td1-off']
TARGETS = {MODEL_IDS[0]: [0, 2], MODEL_IDS[1]: [3]}
PROTOCOL_SHA256 = 'a1358e1245d61092f2063d32cde0f2ca783ce44dfb9412ca6e015295ff76cf6d'
DEGREE, PLACES, MAX_STEPS = 96, 50, 1000
GRID = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{50}\Z')


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def binary(value):
    if type(value) not in (int, float) or not isfinite(float(value)):
        raise ValueError('invalid finite primitive number')
    return Q(*float(value).as_integer_ratio())


def grid(value):
    if not isinstance(value, str) or len(value) > 60 or not GRID.fullmatch(value):
        raise ValueError('invalid fixed50 endpoint')
    result = Q(value)
    if value.startswith('-') and result == 0:
        raise ValueError('negative zero endpoint')
    if not -1 <= result <= 1:
        raise ValueError('endpoint outside state domain')
    return result


def outward(value, upper=False):
    scale = 10 ** PLACES
    scaled = value.numerator * scale
    integer = -((-scaled) // value.denominator) if upper else scaled // value.denominator
    whole, decimal = divmod(abs(integer), scale)
    return ('-' if integer < 0 else '') + f'{whole}.{decimal:0{PLACES}d}'


def exp_enclosure(u):
    if not 0 <= u < DEGREE + 2:
        raise ValueError('Taylor tail ratio outside frozen domain')
    term = partial = Q(1)
    for divisor in range(1, DEGREE + 1):
        term = term * u / divisor
        partial += term
    tail = term * u / (DEGREE + 1) / (1 - u / (DEGREE + 2))
    return partial, partial + tail


def tanh_enclosure(value):
    if value == 0:
        return Q(0), Q(0)
    if value < 0:
        lo, hi = tanh_enclosure(-value)
        return -hi, -lo
    lo, hi = exp_enclosure(2 * value)
    return (lo - 1) / (lo + 1), (hi - 1) / (hi + 1)


def advance(b, G, d, lo, hi):
    n = len(b)
    if (not n or len(G) != n or any(len(row) != n for row in G)
            or len(lo) != n or len(hi) != n or not 0 < d <= 1
            or any(not -1 <= low <= high <= 1 for low, high in zip(lo, hi))):
        raise ValueError('invalid forward dimensions, damping or domain')
    image_lo, image_hi = [], []
    for i in range(n):
        zlo, zhi = b[i], b[i]
        for coefficient, low, high in zip(G[i], lo, hi):
            zlo += min(coefficient * low, coefficient * high)
            zhi += max(coefficient * low, coefficient * high)
        hlow, hhigh = tanh_enclosure(zlo)[0], tanh_enclosure(zhi)[1]
        image_lo.append((1 - d) * lo[i] + d * hlow)
        image_hi.append((1 - d) * hi[i] + d * hhigh)
    return image_lo, image_hi


def contains_transition(image_lo, image_hi, next_lo, next_hi):
    # MUTATION_TARGET_TRANSITION
    return (bool(image_lo) and len(image_lo) == len(image_hi) == len(next_lo) == len(next_hi)
            and all(next_lo[i] <= image_lo[i] <= image_hi[i] <= next_hi[i]
                    for i in range(len(image_lo))))


def strict_entry(lo, hi, root_lo, root_hi):
    # MUTATION_TARGET_ENTRY
    return (bool(lo) and len(lo) == len(hi) == len(root_lo) == len(root_hi)
            and all(root_lo[i] < lo[i] <= hi[i] < root_hi[i] for i in range(len(lo))))


def pinned(repo, reference):
    if (not isinstance(reference, dict) or set(reference) != {'path', 'sha256', 'bytes'}
            or not isinstance(reference['path'], str)
            or not isinstance(reference['sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', reference['sha256'])
            or type(reference['bytes']) is not int or reference['bytes'] <= 0):
        raise ValueError('invalid source pin fields')
    path = (repo / reference['path']).resolve()
    if not path.is_relative_to(repo.resolve()):
        raise ValueError('pinned path outside repository')
    data = path.read_bytes()
    if len(data) != reference['bytes'] or hashlib.sha256(data).hexdigest() != reference['sha256']:
        raise ValueError('source hash/byte mismatch: ' + reference['path'])
    return data


def initial_source_check(dynamics, runtime):
    tree = ast.parse(dynamics)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    expected = ast.parse('state={g.id:0.5 for g in program.groups} if initial is None else dict(initial)').body[0]
    if not any(isinstance(node, ast.Assign) and ast.dump(node) == ast.dump(expected)
               for node in functions['settle'].body):
        raise ValueError('default initial source mismatch')
    calls = [node for node in ast.walk(functions['settle_recorded'])
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'settle']
    if len(calls) != 1 or any(keyword.arg in ('initial', None) for keyword in calls[0].keywords):
        raise ValueError('recorded adapter initial override')
    advance_nodes = [node for node in ast.walk(ast.parse(runtime))
                     if isinstance(node, ast.FunctionDef) and node.name == 'advance']
    calls = [node for node in ast.walk(advance_nodes[0])
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == 'settle_recorded'] if len(advance_nodes) == 1 else []
    if (len(calls) != 1 or len(calls[0].args) != 8
            or not isinstance(calls[0].args[6], ast.Constant) or calls[0].args[6].value != 'decision'
            or any(keyword.arg in ('initial', None) for keyword in calls[0].keywords)):
        raise ValueError('original decision callsite initial mismatch')


def protocol_check(protocol):
    if (protocol.get('schema') != 'HCCONBasinProtocol.v1'
            or protocol.get('state_order') != ORDER or protocol.get('targets') != TARGETS
            or protocol['budget']['model_order'] != MODEL_IDS
            or protocol['budget']['max_steps_per_model'] != MAX_STEPS
            or any(protocol['budget'][key] is not False
                   for key in ('auto_retry', 'adaptive_precision', 'alternative_initial'))
            or protocol['arithmetic']['taylor_degree'] != DEGREE
            or protocol['arithmetic']['grid_decimal_places'] != PLACES
            or protocol['original_initial']['p'] != '0.5' or protocol['original_initial']['x'] != '0'
            or protocol['original_initial']['all_state_order'] != ALL_ORDER
            or [model['model_id'] for model in protocol['models']] != MODEL_IDS
            or [source['path'] for source in protocol['sources']] != ['src/hcr/dynamics.py', 'src/hcr/runtime.py']):
        raise ValueError('unsupported frozen basin protocol')


def independent_models(repo, protocol, root_protocol):
    sources = {source['path']: pinned(repo, source) for source in protocol['sources']}
    initial_source_check(sources['src/hcr/dynamics.py'], sources['src/hcr/runtime.py'])
    config_pin = next(source for source in root_protocol['sources']
                      if source['path'] == 'experiments/exp-62-top-down/frozen_spec.json')
    config = decode(pinned(repo, {key: config_pin[key] for key in ('path', 'sha256', 'bytes')}))['config']['kernel']
    T, d, excitation, inhibition = [binary(config[key]) for key in
                                   ('temperature', 'damping', 'self_excitation', 'inhibition')]
    if (T != binary(1.0) or d != binary(0.45) or excitation != binary(0.25)
            or inhibition != binary(0.2) or not 0 < d <= 1):
        raise ValueError('primitive kernel mismatch')
    diagonal = (excitation + inhibition) / (2 * T)
    if not 0 <= diagonal < 1:
        raise ValueError('isolated scalar contraction not established')
    q_iso = 1 - d + d * diagonal
    if not q_iso < 1:
        raise ValueError('isolated damped contraction not established')
    result = {}
    for model in protocol['models']:
        raw = decode(pinned(repo, {'path': model['raw_path'], 'sha256': model['raw_sha256'],
                                  'bytes': model['raw_bytes']}))
        if raw['cell']['id'] != model['model_id'] or raw['cell']['top_down'] is not True:
            raise ValueError('raw cell binding mismatch')
        events = raw['execution']['packet']['document']['events']
        event = next(event for event in events if event.get('event') == 'r02_network'
                     and event['payload'].get('kind') == 'decision')
        network = event['payload']
        groups, links, drives = network['program']['groups'], network['program']['links'], network['drives']
        if (event['seq'] != 8 or network['network_id'] != 'network-8'
                or network['top_down'] is not True or [group['id'] for group in groups] != ALL_ORDER
                or len(links) != 8 or not set(drives) <= set(ALL_ORDER)):
            raise ValueError('unexpected first-network structure')
        biases = {group['id']: binary(group['bias']) for group in groups}
        inputs = {name: binary(drives.get(name, 0.0)) for name in ALL_ORDER}
        index = {name: i for i, name in enumerate(ORDER)}
        b = [(biases[name] + inputs[name]) / T for name in ORDER]
        G = [[Q(0) for _ in ORDER] for _ in ORDER]
        kinds = []
        for link in links:
            source, target, kind, weight = link['source'], link['target'], link['kind'], binary(link['weight'])
            if source not in index or target not in index or kind not in ('support', 'top_down'):
                raise ValueError('isolated state has incident link or invalid link')
            G[index[target]][index[source]] += weight / T
            kinds.append(kind)
        if kinds.count('support') != 4 or kinds.count('top_down') != 4:
            raise ValueError('unexpected active link kinds')
        for i in range(len(ORDER)):
            G[i][i] += diagonal
        result[model['model_id']] = (b, G, d, q_iso)
    return result


def reverify_roots(repo, protocol, models, root_protocol):
    checker_path = (repo / protocol['root_checker']['path']).resolve()
    pinned(repo, protocol['root_checker'])
    checker = runpy.run_path(str(checker_path), run_name='basin_root_reverification')
    root_models = checker['load_models'](repo, root_protocol)
    if any(tuple(models[name][:3]) != root_models[name] for name in MODEL_IDS):
        raise ValueError('independent raw model differs from root model')
    certificates = decode(pinned(repo, protocol['root_record']))['discovery']['certificates']
    boxes, results = {}, []
    for name in MODEL_IDS:
        boxes[name] = {}
        for index in TARGETS[name]:
            certificate = certificates[index]
            if certificate.get('model_id') != name:
                raise ValueError('target root/model binding mismatch')
            result, box = checker['check_certificate'](certificate, index, root_models,
                                                      protocol['root_protocol']['sha256'])
            results.append(result)
            if result.get('accepted') is not True or box is None:
                raise ValueError('target root reverification failed: ' + str(index))
            boxes[name][index] = box
    return boxes, {'checker_sha256': protocol['root_checker']['sha256'],
                   'root_protocol_sha256': protocol['root_protocol']['sha256'],
                   'root_record_sha256': protocol['root_record']['sha256'],
                   'independent_model_exact_match': True, 'results': results}


def validate_trace(trace, expected_model):
    fields = {'model_id', 'state_order', 'initial_p', 'initial_x', 'steps',
              'entry_certificate_index', 'proposal_status'}
    if (not isinstance(trace, dict) or set(trace) != fields or trace['model_id'] != expected_model
            or trace['state_order'] != ORDER or trace['initial_p'] != '0.5'
            or trace['initial_x'] != ['0'] * len(ORDER)):
        raise ValueError('trace model/order/original initial binding mismatch')
    status, entry = trace['proposal_status'], trace['entry_certificate_index']
    if (status not in ('entered_box', 'budget_exhausted')
            or (status == 'entered_box' and (type(entry) is not int or entry not in TARGETS[expected_model]))
            or (status == 'budget_exhausted' and entry is not None)):
        raise ValueError('invalid proposal/root binding')
    steps = trace['steps']
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS + 1:
        raise ValueError('invalid bounded step inventory')
    boxes = []
    for number, step in enumerate(steps):
        if (not isinstance(step, dict) or set(step) != {'step', 'lower', 'upper'}
                or type(step['step']) is not int or step['step'] != number
                or any(not isinstance(step[key], list) or len(step[key]) != len(ORDER)
                       for key in ('lower', 'upper'))):
            raise ValueError('nonconsecutive step or coordinate dimension mismatch')
        lo, hi = [list(map(grid, step[key])) for key in ('lower', 'upper')]
        if any(low > high for low, high in zip(lo, hi)):
            raise ValueError('reversed trace endpoints')
        boxes.append((lo, hi))
    if boxes[0] != ([Q(0)] * len(ORDER), [Q(0)] * len(ORDER)):
        raise ValueError('step zero is not exact original initial point')
    if status == 'budget_exhausted' and len(boxes) != MAX_STEPS + 1:
        raise ValueError('budget exhausted before frozen step budget')
    return boxes


def check_trace(trace, expected_model, model, root_boxes):
    result = {'model_id': expected_model, 'accepted': False, 'entry_step': None,
              'entry_certificate_index': None, 'checked_steps': 0,
              'isolated_qF_upper': outward(model[3], True), 'all7_unique_lift': False}
    try:
        boxes = validate_trace(trace, expected_model)
        minimum_slack = None
        first_entry = None
        for number, (lo, hi) in enumerate(boxes):
            if number:
                image_lo, image_hi = advance(*model[:3], *boxes[number - 1])
                if not contains_transition(image_lo, image_hi, lo, hi):
                    return dict(result, reason='forward enclosure not contained at step ' + str(number))
                slack = min([image_lo[i] - lo[i] for i in range(len(ORDER))]
                            + [hi[i] - image_hi[i] for i in range(len(ORDER))])
                minimum_slack = slack if minimum_slack is None else min(minimum_slack, slack)
                result['checked_steps'] = number
            for index, (root_lo, root_hi) in root_boxes.items():
                if strict_entry(lo, hi, root_lo, root_hi):
                    first_entry = (number, index)
                    break
            if first_entry is not None:
                break
        if minimum_slack is not None:
            result['minimum_transition_slack'] = outward(minimum_slack)
        if first_entry is None:
            reason = ('INCONCLUSIVE: frozen budget exhausted without certified entry'
                      if trace['proposal_status'] == 'budget_exhausted' else 'strict target entry not established')
            return dict(result, reason=reason)
        number, index = first_entry
        if (trace['proposal_status'] != 'entered_box' or trace['entry_certificate_index'] != index
                or number != len(boxes) - 1):
            return dict(result, reason='proposal does not terminate at first verified target entry')
        root_lo, root_hi = root_boxes[index]
        lo, hi = boxes[number]
        terminal_slack = min([lo[i] - root_lo[i] for i in range(len(ORDER))]
                             + [root_hi[i] - hi[i] for i in range(len(ORDER))])
        return dict(result, accepted=True,
                    reason='certified exact initial basin and unique seven-state lift in fixed real model',
                    entry_step=number, entry_certificate_index=index, all7_unique_lift=True,
                    terminal_slack=outward(terminal_slack),
                    root_goal_p_enclosure=[outward((root_lo[-1] + 1) / 2),
                                           outward((root_hi[-1] + 1) / 2, True)])
    except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
        return dict(result, reason=str(error))


def check_document(document, models, root_boxes, protocol_sha256):
    if (not isinstance(document, dict) or set(document) != {'schema', 'protocol_sha256', 'models'}
            or document['schema'] != 'HCCONBasinTrace.v1' or document['protocol_sha256'] != protocol_sha256
            or not isinstance(document['models'], list) or len(document['models']) != len(MODEL_IDS)):
        raise ValueError('trace document binding or schema mismatch')
    return [check_trace(trace, name, models[name], root_boxes[name])
            for trace, name in zip(document['models'], MODEL_IDS)]


def self_test():
    def require(condition, label):
        if not condition:
            raise AssertionError(label)

    def rejects(call, label):
        try:
            call()
        except (ValueError, TypeError, KeyError):
            return
        raise AssertionError(label)

    image = advance([Q(0)], [[Q(0)]], Q(1, 2), [Q(-1, 5)], [Q(2, 5)])
    require(image == ([Q(-1, 10)], [Q(1, 5)]), 'damping exact golden case')
    require(contains_transition(*image, [Q(-1, 10)], [Q(1, 5)]), 'valid transition')
    require(not contains_transition(*image, [Q(-9, 100)], [Q(1, 5)]), 'transition inclusion bypass control')
    require(not strict_entry([Q(0)], [Q(1, 2)], [Q(0)], [Q(1)]), 'strict terminal entry control')
    require(strict_entry([Q(0)], [Q(1, 2)], [Q(-1)], [Q(1)]), 'strict entry accepted')
    require(exp_enclosure(Q(0)) == (Q(1), Q(1)), 'exp zero')
    lower, upper = exp_enclosure(Q(1))
    require(Q(8, 3) < lower < upper < Q(11, 4), 'exp1 independent coarse golden bounds')
    require(tanh_enclosure(Q(-1)) == tuple(-x for x in reversed(tanh_enclosure(Q(1)))), 'tanh oddness')
    rejects(lambda: exp_enclosure(Q(98)), 'invalid Taylor tail domain')
    zero = '0.' + '0' * PLACES
    trace = {'model_id': MODEL_IDS[0], 'state_order': list(ORDER), 'initial_p': '0.5',
             'initial_x': ['0'] * len(ORDER), 'steps': [{'step': 0, 'lower': [zero] * 5, 'upper': [zero] * 5}],
             'entry_certificate_index': 0, 'proposal_status': 'entered_box'}
    require(validate_trace(trace, MODEL_IDS[0]) == [([Q(0)] * 5, [Q(0)] * 5)], 'valid initial schema')
    rejects(lambda: validate_trace(dict(trace, initial_x=['0.5'] * 5), MODEL_IDS[0]), 'altered initial rejected')
    rejects(lambda: validate_trace(dict(trace, state_order=list(reversed(ORDER))), MODEL_IDS[0]), 'coordinate reorder rejected')
    rejects(lambda: validate_trace(dict(trace, model_id=MODEL_IDS[1]), MODEL_IDS[0]), 'model swap rejected')
    rejects(lambda: validate_trace(dict(trace, entry_certificate_index=3), MODEL_IDS[0]), 'root swap rejected')
    rejects(lambda: validate_trace(dict(trace, steps=trace['steps'] +
                                      [{'step': 2, 'lower': [zero] * 5, 'upper': [zero] * 5}]), MODEL_IDS[0]),
            'missing step rejected')
    for endpoint in ('0', '+0.' + '0' * 50, '-0.' + '0' * 50, '0.' + '0' * 49, '1e-2', 'NaN'):
        rejects(lambda endpoint=endpoint: grid(endpoint), 'invalid endpoint encoding')
    for data in ('{"a":1,"a":2}', '{"a":NaN}'):
        rejects(lambda data=data: decode(data), 'invalid JSON rejected')
    dynamics_fixture = ("def settle(program, initial=None):\n"
                        "    state={g.id:0.5 for g in program.groups} if initial is None else dict(initial)\n"
                        "def settle_recorded():\n    settle(a,b,c,d)\n")
    runtime_fixture = "def advance():\n    settle_recorded(a,b,c,d,e,f,'decision',h)\n"
    initial_source_check(dynamics_fixture, runtime_fixture)
    rejects(lambda: initial_source_check(dynamics_fixture.replace('0.5 for', '0.4 for'), runtime_fixture),
            'source initial mismatch rejected')
    rejects(lambda: initial_source_check(dynamics_fixture.replace('settle(a,b,c,d)', 'settle(a,b,c,d,initial=x)'),
                                         runtime_fixture), 'source adapter override rejected')
    return {'schema': 'HCCONBasinCheckSelfTest.v1', 'passed': True,
            'forward_golden': ['-0.1', '0.2'], 'synthetic_only': True,
            'controls': ['damping', 'shrunken_nextbox', 'boundary_contact', 'initial',
                         'model_root_binding', 'coordinate_order', 'missing_step', 'encoding', 'JSON']}


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
    result = {'schema': 'HCCONBasinCheck.v1', 'protocol_sha256': args.protocol_sha256,
              'results': [], 'root_reverification': {}}
    try:
        data = Path(args.protocol).read_bytes()
        if args.protocol_sha256 != PROTOCOL_SHA256 or hashlib.sha256(data).hexdigest() != args.protocol_sha256:
            raise ValueError('frozen protocol hash mismatch')
        protocol, repo = decode(data), Path(args.repo).resolve()
        protocol_check(protocol)
        root_protocol = decode(pinned(repo, protocol['root_protocol']))
        pinned(repo, protocol['proposal_helper'])
        models = independent_models(repo, protocol, root_protocol)
        root_boxes, result['root_reverification'] = reverify_roots(repo, protocol, models, root_protocol)
        result['results'] = check_document(decode(Path(args.input).read_bytes()), models, root_boxes,
                                           args.protocol_sha256)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, OSError, SyntaxError) as error:
        result['error'] = str(error)
    with Path(args.output).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    if 'error' in result or any(not item['accepted'] for item in result['results']):
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        sys.exit(1)
