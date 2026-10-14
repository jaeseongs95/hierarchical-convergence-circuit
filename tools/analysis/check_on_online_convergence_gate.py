"""현재 입력만의 지역 인증을 저장 궤적에서 검사한다. 스트리밍 실행 증거는 아니다."""
from __future__ import annotations

import argparse
import ast
import builtins
from datetime import datetime, timedelta, timezone
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

PROTOCOL_SHA = '45321c82d20a145bb9b7a5484f4aba3118415358438d69d4751a83a6f25cb7c0'
BASE = 'experiments/exp-62-top-down/'
DISTANCE_PROTOCOL = BASE + 'on-fixed-point-distance-entry-protocol-20261014.json'
DISTANCE_RECORD = BASE + 'on-fixed-point-distance-entry-certificates-20261014.json'
DISTANCE_CHECKER = 'tools/analysis/check_on_fixed_point_distance_entry.py'
DISTANCE_PRODUCER = 'tools/analysis/on_fixed_point_distance_entry.py'
ROOT_CHECKER = 'tools/analysis/check_on_fixed_points.py'
GATE_CHECKER = 'tools/analysis/check_on_convergence_gate.py'
ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
EPSILONS = ['1/1000000', '1/100000000']
TICKS = [1848, 5155, 5156, 5170, 5171]
RADII = ['1/1000000', '1/100000']
ACTUAL_FIRST = dict(zip(EPSILONS, (5156, 5171)))
OLD_GATE_FIRST = dict(zip(EPSILONS, (5161, 5173)))
PAYLOAD_FIELDS = {'model', 'current_x_box', 'radius_x_exact', 'epsilon_p_exact'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: require(False, 'nonfinite JSON'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def file_pin(path):
    data = Path(path).read_bytes()
    return {'path': str(Path(path).resolve()), 'sha256': digest(data), 'bytes': len(data)}


def pinned(repo, ref):
    require(isinstance(ref, dict) and set(ref) == {'path', 'sha256', 'bytes'}, 'pin fields')
    require(isinstance(ref['path'], str) and isinstance(ref['sha256'], str)
            and re.fullmatch('[0-9a-f]{64}', ref['sha256'])
            and type(ref['bytes']) is int and ref['bytes'] > 0, 'pin types')
    relative = Path(ref['path'])
    require(not relative.is_absolute() and '..' not in relative.parts, 'pin traversal')
    path = (repo / relative).resolve()
    require(path.is_relative_to(repo), 'pin outside repository')
    data = path.read_bytes()
    require(len(data) == ref['bytes'] and digest(data) == ref['sha256'], 'pin bytes/hash')
    return data


def outward(value, upper=True):
    value = Q(value)
    scaled = value.numerator * 10**40
    integer = -((-scaled) // value.denominator) if upper else scaled // value.denominator
    whole, decimal = divmod(abs(integer), 10**40)
    return ('-' if integer < 0 else '') + f'{whole}.{decimal:040d}'


def rational(value):
    require(isinstance(value, str) and len(value) <= 200
            and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*|\.[0-9]+)?', value),
            'rational text')
    result = Q(value)
    require(not (result == 0 and value.startswith('-')), 'negative zero')
    return result


def validatepayload(payload):
    require(isinstance(payload, dict) and set(payload) == PAYLOAD_FIELDS, 'local payload fields')
    model = payload['model']
    require(isinstance(model, dict) and set(model) == {'b', 'G', 'd'}, 'model fields')
    require(isinstance(model['b'], list) and isinstance(model['G'], list)
            and len(model['b']) == len(model['G']) == 7
            and all(isinstance(row, list) and len(row) == 7 for row in model['G']), 'whole7 model')
    b = list(map(rational, model['b']))
    G = [list(map(rational, row)) for row in model['G']]
    d = rational(model['d'])
    require(0 < d <= 1, 'damping domain')
    encoded = payload['current_x_box']
    require(isinstance(encoded, list) and len(encoded) == 7, 'whole current box')
    current = []
    for pair in encoded:
        require(isinstance(pair, list) and len(pair) == 2, 'current endpoint pair')
        require(all(isinstance(v, str) and re.fullmatch(r'-?(?:0|[1-9][0-9]*)\.[0-9]{30}', v)
                    for v in pair), 'current grid30')
        lo, hi = map(rational, pair)
        require(-1 <= lo <= hi <= 1, 'current domain/order')
        current.append((lo, hi))
    radius = rational(payload['radius_x_exact'])
    require(radius > 0, 'positive radius')
    eps = payload['epsilon_p_exact']
    require(isinstance(eps, list) and eps and len(set(eps)) == len(eps), 'epsilon inventory')
    require(all(rational(v) > 0 for v in eps), 'positive epsilon')
    return (b, G, d), current, radius


def solve_comparison(K, r):
    """qK<1 supplies Neumann positivity; exact elimination supplies one checked solution."""
    require(isinstance(K, list) and isinstance(r, list) and len(K) == len(r) == 7
            and all(isinstance(row, list) and len(row) == 7 for row in K), 'comparison dimensions')
    K = [[Q(v) for v in row] for row in K]
    r = list(map(Q, r))
    qK = max(map(sum, K))
    require(all(v >= 0 for row in K for v in row) and all(v >= 0 for v in r)
            and 0 <= qK < 1, 'nonnegative comparison/qK strict')
    A = [[Q(i == j)-K[i][j] for j in range(7)] + [r[i]] for i in range(7)]
    for col in range(7):
        pivot = next((i for i in range(col, 7) if A[i][col]), None)
        require(pivot is not None, 'comparison singular')
        A[col], A[pivot] = A[pivot], A[col]
        denominator = A[col][col]
        A[col] = [v/denominator for v in A[col]]
        for i in range(7):
            if i != col:
                coefficient = A[i][col]
                A[i] = [v-coefficient*w for v, w in zip(A[i], A[col])]
    v = [row[-1] for row in A]
    require(all(value >= 0 for value in v), 'negative comparison solution')
    require(all(v[i]-sum(K[i][j]*v[j] for j in range(7)) == r[i]
                for i in range(7)), 'comparison equation')
    require(max(v) <= max(r)/(1-qK), 'sameK scalar domination')
    return v


def gatebound(valid, exact, epsilon, reason=None):
    eps = rational(epsilon)
    require(eps > 0 and type(valid) is bool, 'gate inputs')
    public = outward(exact) if exact is not None else None
    reasons = []
    if not valid:
        reasons.append(reason or 'region/comparison not proved')
    elif exact is None:
        reasons.append('bound not evaluated')
    else:
        require(exact >= 0 and Q(public) >= exact, 'bound outward')
        if exact > eps or Q(public) > eps:
            reasons.append('exact/public distance bound exceeds epsilon')
    return {'epsilon_p_exact': epsilon, 'status': 'NOT_CERTIFIED' if reasons else 'CERTIFIED_WITHIN_EPS',
            'E_p_exact': str(exact) if exact is not None else None,
            'E_p_upper40': public, 'reasons': reasons}


def build_arithmetic(root_source, gate_source, guard=lambda: None):
    """Compile only pinned arithmetic defs into namespaces without loader/IO globals."""
    safe = {name: getattr(builtins, name) for name in
            ('abs', 'all', 'any', 'dict', 'divmod', 'enumerate', 'int', 'isinstance',
             'len', 'list', 'map', 'max', 'min', 'range', 'str', 'sum', 'zip', 'ValueError')}
    def select(source, names, scope, count_tanh=False):
        tree = ast.parse(source)
        chosen = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        require({node.name for node in chosen} == set(names), 'arithmetic function inventory')
        require(all(not node.decorator_list for node in chosen), 'arithmetic decorators')
        for node in chosen:
            require(not any(isinstance(child, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal))
                            for child in ast.walk(node)), 'arithmetic forbidden syntax')
            if count_tanh and node.name == 'tanh_bounds':
                node.body.insert(0, ast.Expr(ast.Call(ast.Name('_guard', ast.Load()), [], [])))
        module = ast.fix_missing_locations(ast.Module(body=chosen, type_ignores=[]))
        exec(compile(module, '<pinned-local-arithmetic>', 'exec'), scope)
        return {name: scope[name] for name in names}
    root_scope = {'__builtins__': safe, 'Q': Q, 'DEGREE': 96, 'PLACES': 40, '_guard': guard}
    roots = select(root_source, ('outward', 'exp_positive', 'tanh_bounds', 'slope_upper', 'check_box'),
                   root_scope, True)
    residual_scope = {'__builtins__': safe, 'Q': Q}
    residuals = select(gate_source, ('require', 'outward', 'residual_upper'), residual_scope)
    return {'check_box': roots['check_box'], 'tanh_bounds': roots['tanh_bounds'],
            'residual_upper': residuals['residual_upper'],
            'root_namespace': root_scope, 'residual_namespace': residual_scope}


def informationaudit(arithmetic):
    require(set(arithmetic) == {'check_box', 'tanh_bounds', 'residual_upper',
                                'root_namespace', 'residual_namespace'}, 'arithmetic API fields')
    require(set(arithmetic['root_namespace']) == {'__builtins__', 'Q', 'DEGREE', 'PLACES', '_guard',
            'outward', 'exp_positive', 'tanh_bounds', 'slope_upper', 'check_box'}, 'root globals barrier')
    require(set(arithmetic['residual_namespace']) == {'__builtins__', 'Q', 'require', 'outward',
                                                    'residual_upper'}, 'residual globals barrier')
    for key, names in (('root_namespace', ('outward', 'exp_positive', 'tanh_bounds', 'slope_upper', 'check_box')),
                       ('residual_namespace', ('require', 'outward', 'residual_upper'))):
        scope = arithmetic[key]
        require('open' not in scope['__builtins__'] and '__import__' not in scope['__builtins__'],
                'IO builtins barrier')
        require(all(scope[name].__globals__ is scope and scope[name].__closure__ is None
                    for name in names), 'arithmetic closure/cache barrier')
    require(arithmetic['check_box'] is arithmetic['root_namespace']['check_box']
            and arithmetic['tanh_bounds'] is arithmetic['root_namespace']['tanh_bounds']
            and arithmetic['residual_upper'] is arithmetic['residual_namespace']['residual_upper'],
            'arithmetic callback identity')
    return {'arithmetic_defs_only': True, 'file_IO_builtins_absent': True,
            'helper_closures_absent': True, 'cache': 'OFF',
            'budget_callback': 'operational guard only; cannot supply numerical data',
            'payload_fields': sorted(PAYLOAD_FIELDS), 'streaming_execution_claim': False}


def current_residual(payload, arithmetic):
    (b, G, _), current, _ = validatepayload(payload)
    eH, witness = arithmetic['residual_upper'](b, G, current, arithmetic['tanh_bounds'])
    return {'model': payload['model'], 'current_x_box': payload['current_x_box'],
            'eH': str(eH), 'witness': witness}


def local_certificate(payload, arithmetic, residual=None):
    """No tick, anchor, old certificate or filesystem argument enters this numerical API."""
    (b, G, d), current, radius = validatepayload(payload)
    informationaudit(arithmetic)
    mids = [(lo+hi)/2 for lo, hi in current]
    lower, upper = [m-radius for m in mids], [m+radius for m in mids]
    require(all(-1 < lo < hi < 1 and (lo*10**31).denominator == 1
                and (hi*10**31).denominator == 1 for lo, hi in zip(lower, upper)), 'region geometry/grid31')
    entry = all(lo < bl <= bh < hi for lo, hi, (bl, bh) in zip(lower, upper, current))
    proof = arithmetic['check_box'](b, G, d, lower, upper, [Q(1)]*7)
    require(isinstance(proof, dict) and type(proof.get('accepted')) is bool, 'region proof shape')
    if not proof['accepted']:
        require(proof.get('reason') in {'strict self-inclusion failed', 'exact contraction failed',
                'public self-inclusion insufficient', 'public contraction insufficient'}, 'region proof failure')
    if residual is None:
        residual = current_residual(payload, arithmetic)
    require(set(residual) == {'model', 'current_x_box', 'eH', 'witness'}
            and residual['model'] == payload['model']
            and residual['current_x_box'] == payload['current_x_box'], 'shared residual current context')
    r = list(map(Q, residual['witness']['coordinate_residual_x_upper']))
    require(len(r) == 7 and all(v >= 0 for v in r) and max(r) == Q(residual['eH'])
            and residual['witness']['all7'] is True, 'shared wholeB residual shape')
    valid = entry and proof['accepted']
    result = {'region': {'lower_exact': list(map(str, lower)), 'upper_exact': list(map(str, upper)),
                         'weights': [1]*7}, 'all7_strict_entry': entry, 'region_valid': valid,
              'local_proof': proof, 'current_residual': residual['witness'],
              'same_orbit_limit_argument': 'accepted current orbit state in F-invariant current C; unique local limit',
              'comparison': {'evaluated': False}, 'bounds': {}}
    scalar = vector = None
    vector_valid = False
    reason = ('all7 strict current entry failed' if not entry else proof.get('reason')) if not valid else None
    if valid:
        qH = Q(proof['qH_upper'])
        require(0 <= qH < 1 and proof['exact_qH_lt_one'] is True
                and proof['exact_qF_lt_one'] is True, 'accepted contraction shape')
        scalar = max(r)/(2*(1-qH))
        slopes = list(map(Q, proof['slope_upper']))
        require(len(slopes) == 7 and all(0 <= s <= 1 for s in slopes), 'slope witnesses')
        K = [[slopes[i]*abs(G[i][j]) for j in range(7)] for i in range(7)]
        qK = max(map(sum, K))
        qF = 1-d+d*qK
        comparison = {'evaluated': False, 'K_exact': [list(map(str, row)) for row in K],
                      'r_exact': list(map(str, r)), 'qK_exact': str(qK), 'qF_K_exact': str(qF),
                      'qF_K_upper40': outward(qF), 'legacy_qH_independently_rounded': True}
        if qK < 1 and Q(outward(qF)) < 1:
            v = solve_comparison(K, r)
            KF = [[(1-d)*Q(i == j)+d*K[i][j] for j in range(7)] for i in range(7)]
            require(all(Q(i == j)-KF[i][j] == d*(Q(i == j)-K[i][j])
                        for i in range(7) for j in range(7)), 'entrywise damping identity')
            require(all(v[i]-sum(KF[i][j]*v[j] for j in range(7)) == d*r[i]
                        for i in range(7)), 'damped residual solution')
            vector, vector_valid = max(v)/2, True
            comparison.update(evaluated=True, v_exact=list(map(str, v)),
                              positive_inverse_basis='K>=0/qK<1 Neumann; no fullinverse computed',
                              equation_checked=True, v_nonnegative=True, damping_identity_checked=True,
                              sameK_scalar_p_exact=str(max(r)/(2*(1-qK))), sameK_domination=True)
        else:
            comparison['reason'] = 'strict exact/public comparison contraction not proved'
        result['comparison'] = comparison
    result['bounds']['legacy_scalar'] = [gatebound(valid, scalar, eps, reason) for eps in payload['epsilon_p_exact']]
    result['bounds']['component_vector'] = [gatebound(vector_valid, vector, eps,
        reason or result['comparison'].get('reason')) for eps in payload['epsilon_p_exact']]
    for gate in result['bounds']['component_vector']:
        gate['permanence'] = gate['status'] == 'CERTIFIED_WITHIN_EPS' and vector_valid
    return result


def load_binding(repo, protocol, guard):
    refs = {ref['path']: ref for ref in protocol['sources']}
    require(len(refs) == len(protocol['sources']) == 34, '34 unique source pins')
    data = {}
    for name, ref in refs.items():
        guard()
        data[name] = pinned(repo, ref)
    require(len(protocol['raw']) == 2, 'two raw pins')
    for ref in protocol['raw']:
        guard()
        pinned(repo, {key: ref[key] for key in ('path', 'sha256', 'bytes')})
    legacy_protocol = decode(data[DISTANCE_PROTOCOL])
    require(protocol['legacy_distance_protocol'] == refs[DISTANCE_PROTOCOL]
            and protocol['raw'] == legacy_protocol['raw'] and set(refs) ==
            {ref['path'] for ref in legacy_protocol['sources']} |
            {DISTANCE_PROTOCOL, DISTANCE_RECORD, DISTANCE_CHECKER, DISTANCE_PRODUCER}, 'legacy closure')
    sys.dont_write_bytecode = True
    legacy = {'__name__': 'online_gate_custody', '__file__': str(repo/DISTANCE_CHECKER)}
    exec(compile(data[DISTANCE_CHECKER], str(repo/DISTANCE_CHECKER), 'exec'), legacy)
    require(digest(data[DISTANCE_PROTOCOL]) == legacy['PROTOCOL_SHA'], 'legacy protocol hash')
    model, model_digest, inventory, _ = legacy['load_binding'](repo, legacy_protocol, guard)
    record = decode(data[DISTANCE_RECORD])
    frozen = record['frozen_execution']
    require(record['schema'] == 'HCCONFixedPointDistanceEntryCertificates.v1'
            and record['source_commit'] == legacy_protocol['source_commit']
            and frozen['protocol'] == refs[DISTANCE_PROTOCOL]
            and type(frozen['numerical_runs_before_freeze']) is int
            and frozen['numerical_runs_before_freeze'] == 0
            and len(frozen['files']) == 3
            and {ref['path']: ref for ref in frozen['files']} ==
            {name: refs[name] for name in (DISTANCE_PROTOCOL, DISTANCE_CHECKER, DISTANCE_PRODUCER)},
            'legacy frozen binding')
    checked = record['independent_verification']
    require(checked['schema'] == 'HCCONFixedPointDistanceEntryCheck.v1'
            and checked['accepted'] is True and checked['status'] == 'CERTIFIED_EARLIEST_DISTANCE_ENTRY'
            and checked['full_scan_complete'] is True and checked['model_digest'] == model_digest
            and checked['state_order'] == ORDER and checked['sample_id'] == protocol['sample_id']
            and checked['norm'] == 'p_infinity_all7' and checked['all7'] is True
            and checked['epsilon_p_exact'] == EPSILONS and checked['first_ticks'] == ACTUAL_FIRST
            and checked['source_pins'] == legacy_protocol['sources']
            and checked['raw_pins'] == protocol['raw'] and checked['boxes_digest'] == digest(canonical(inventory))
            and checked['checker_pin'] == file_pin(repo/DISTANCE_CHECKER), 'accepted actual distance trust')
    require(checked['protocol_sha256'] == refs[DISTANCE_PROTOCOL]['sha256']
            and checked['proposal_sha256'] == digest((json.dumps(record['proposal'], ensure_ascii=False,
                    indent=2, allow_nan=False)+'\n').encode('utf-8')), 'legacy canonical proposal')
    require(all(legacy_protocol[key] == protocol[key] for key in
            ('initial_x', 'network_id', 'state_order', 'sample_id', 'score_hex', 'drive_hex', 'norm', 'epsilon_p_exact')),
            'legacy orbit identity')
    journal_pin = checked['journal_pin']
    journal_rows = record['committed_proof_journal']
    journal_data = ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n'
                           for row in journal_rows).encode('utf-8')
    require(len(journal_data) == journal_pin['bytes'] and digest(journal_data) == journal_pin['sha256'],
            'embedded trusted distance journal bytes/hash')
    rows = checked['distance_results']
    require(rows == journal_rows and len(rows) == 6145, 'whole old distance journal/record')
    for tick, row in enumerate(rows):
        guard()
        require(type(row['tick']) is int and row['tick'] == tick, 'old predecessor gap/order')
    for eps, first in ACTUAL_FIRST.items():
        require(all(row['classification'][eps] == 'OUTSIDE' and Q(row['lower_p_exact']) > Q(eps)
                    for row in rows[:first]), 'old whole predecessor outside')
        require(rows[first]['classification'][eps] == 'INSIDE'
                and Q(rows[first]['upper_p_exact']) <= Q(eps), 'old actual positive')
        summary = next(s for s in checked['summaries'] if s['epsilon_p_exact'] == eps)
        require(summary['first_tick'] == first and summary['status'] == 'CERTIFIED_EARLIEST_DISTANCE_ENTRY'
                and summary['predecessor_coverage'] == {'range': [0, first-1], 'count': first, 'complete': True}
                and summary['old_fixed_gate_first_tick'] == OLD_GATE_FIRST[eps], 'old actual summary coverage')
    return model, model_digest, inventory, data


def verify(args, result, guard):
    require(args.protocol_sha256 == PROTOCOL_SHA, 'fixed protocol argument')
    protocol_data = Path(args.protocol).read_bytes()
    require(digest(protocol_data) == PROTOCOL_SHA, 'protocol frozen hash')
    protocol = decode(protocol_data)
    require(protocol['schema'] == 'HCCONOnlineConvergenceGateProtocol.v1'
            and protocol['state_order'] == ORDER and protocol['initial_x'] == '0'
            and protocol['ticks'] == TICKS and protocol['radii_x_exact'] == RADII
            and protocol['epsilon_p_exact'] == EPSILONS and protocol['norm'] == 'p_infinity_all7', 'fixed contract')
    proposal_data = Path(args.input).read_bytes()
    proposal = decode(proposal_data)
    require(set(proposal) == {'schema', 'protocol_sha256', 'sample_id', 'score_hex', 'drive_hex',
                            'ticks', 'radii_x_exact', 'epsilon_p_exact'}, 'proposal fields')
    require(proposal['schema'] == 'HCCONOnlineConvergenceGateProposal.v1'
            and proposal['protocol_sha256'] == PROTOCOL_SHA
            and all(proposal[key] == protocol[key] for key in
                ('sample_id', 'score_hex', 'drive_hex', 'ticks', 'radii_x_exact', 'epsilon_p_exact')),
            'proposal fixed binding')
    counters = result['counters']
    counters['binding_scalar_sanity'] = counters['scalar_calls'] = 1
    repo = Path(args.repo).resolve()
    model, model_digest, inventory, data = load_binding(repo, protocol, guard)
    def scalar_guard():
        guard()
        require(counters['scalar_calls'] < 65536, 'scalar cap exhausted')
        counters['scalar_calls'] += 1
        guard()
    arithmetic = build_arithmetic(data[ROOT_CHECKER], data[GATE_CHECKER], scalar_guard)
    audit = informationaudit(arithmetic)
    b, G, d = model
    model_payload = {'b': list(map(str, b)), 'G': [list(map(str, row)) for row in G], 'd': str(d)}
    result.update(proposal_sha256=digest(proposal_data), source_pins=protocol['sources'], raw_pins=protocol['raw'],
                  model_digest=model_digest, boxes_digest=digest(canonical(inventory)), state_order=ORDER,
                  sample_id=protocol['sample_id'], epsilon_p_exact=EPSILONS, norm=protocol['norm'], all7=True,
                  information_boundary=audit, limits=protocol['scope_limits'],
                  trusted_dependencies=protocol['trusted_dependencies'], old_actual_first=ACTUAL_FIRST,
                  old_fixed_gate_first=OLD_GATE_FIRST, old_trajectory_rerun=0, native_replays=0,
                  prior_census_rerun=False, new_full_first_scan=False)
    journal = Path(str(args.output)+'.partial.jsonl')
    result['journal_path'] = str(journal.resolve())
    with journal.open('x', encoding='utf-8', newline='\n') as stream:
        def commit(row):
            guard()
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
            guard()
        commit({'kind': 'source_bound_header', 'protocol_sha256': PROTOCOL_SHA,
                'model_digest': model_digest, 'boxes_digest': result['boxes_digest'],
                'local_information': audit})
        for tick in TICKS:
            guard()
            payload = {'model': model_payload, 'current_x_box': inventory[tick]['x_box'],
                       'radius_x_exact': RADII[0], 'epsilon_p_exact': EPSILONS}
            require(counters['wholeB_residuals'] < 5, 'residual cap exhausted')
            counters['wholeB_residuals'] += 1
            residual = current_residual(payload, arithmetic)
            for radius in RADII:
                guard()
                payload = dict(payload, radius_x_exact=radius)
                require(counters['fresh_region_proofs'] < 10, 'region cap exhausted')
                counters['fresh_region_proofs'] += 1
                cell = local_certificate(payload, arithmetic, residual)
                cell.update(tick=tick, radius_x_exact=radius, current_x_box=payload['current_x_box'],
                            local_payload_sha256=digest(canonical(payload)))
                require(all(tick >= ACTUAL_FIRST[g['epsilon_p_exact']]
                            for gates in cell['bounds'].values() for g in gates
                            if g['status'] == 'CERTIFIED_WITHIN_EPS'),
                        'fresh positive conflicts with trusted actual predecessor OUTSIDE')
                commit({'kind': 'local_cell', 'cell': cell})
                result['cells'].append(cell)
                counters['committed_cells'] += 1
                guard()
    require(counters['wholeB_residuals'] == 5 and counters['fresh_region_proofs'] == 10
            and counters['committed_cells'] == 10, 'incomplete frozen grid')
    firstness = []
    for radius in RADII:
        for bound in ('legacy_scalar', 'component_vector'):
            for eps, actual in ACTUAL_FIRST.items():
                positive = any(c['tick'] == actual and c['radius_x_exact'] == radius
                    and c['region_valid'] and any(g['epsilon_p_exact'] == eps and
                    g['status'] == 'CERTIFIED_WITHIN_EPS' for g in c['bounds'][bound]) for c in result['cells'])
                firstness.append({'radius_x_exact': radius, 'bound': bound, 'epsilon_p_exact': eps,
                    'first_tick': actual if positive else None,
                    'status': 'CERTIFIED_EARLIEST_BY_TRUSTED_EXCLUSIONS' if positive else 'NOT_ESTABLISHED',
                    'delay_ticks': 0 if positive else None,
                    'old_delay_ticks': OLD_GATE_FIRST[eps]-actual,
                    'basis': 'fresh current local positive + trusted retrospective all predecessor OUTSIDE + same orbit limit',
                    'new_full_first_scan': False})
    result.update(accepted=True, status='CERTIFIED_SAMPLED_ONLINE_ELIGIBLE_ANALYSIS',
                  grid_complete=True, firstness=firstness)
    guard()


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--remaining-seconds', type=float, default=180)
    args = parser.parse_args()
    started, utc = time.monotonic(), datetime.now(timezone.utc)
    valid_budget = math.isfinite(args.remaining_seconds) and 0 < args.remaining_seconds <= 180
    deadline = utc+timedelta(seconds=args.remaining_seconds) if valid_budget else utc
    result = {'schema': 'HCCONOnlineConvergenceGateCheck.v1', 'accepted': False, 'status': 'INCONCLUSIVE',
              'protocol_sha256': args.protocol_sha256, 'checker_pin': file_pin(__file__),
              'started_at_utc': utc.isoformat(), 'deadline_utc': deadline.isoformat(), 'cells': [],
              'grid_complete': False, 'firstness': [], 'counters': {'binding_scalar_sanity': 0,
              'scalar_calls': 0, 'fresh_region_proofs': 0, 'wholeB_residuals': 0, 'committed_cells': 0}}
    output, journal = Path(args.output), Path(str(args.output)+'.partial.jsonl')
    pending = Path(str(args.output)+'.pending')
    require(not output.exists() and not journal.exists() and not pending.exists(), 'immutable outputs exist')
    def guard():
        require(valid_budget and time.monotonic()-started < args.remaining_seconds
                and datetime.now(timezone.utc) < deadline, 'absolute scientific budget expired/invalid')
        c = result['counters']
        require(c['binding_scalar_sanity'] <= 1 and c['scalar_calls'] <= 65536
                and c['fresh_region_proofs'] <= 10 and c['wholeB_residuals'] <= 5, 'frozen cap exceeded')
    try:
        guard()
        verify(args, result, guard)
        result['journal_pin'] = file_pin(journal)
        result['elapsed_seconds'] = time.monotonic()-started
        payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        guard()
        with pending.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        guard()
        pending.rename(output)
    except (ValueError, KeyError, TypeError, IndexError, OSError, OverflowError, ZeroDivisionError, StopIteration) as error:
        result.update(accepted=False, status='INCONCLUSIVE', reason=str(error), grid_complete=False, firstness=[])
        result['cells'] = result['cells'][:result['counters']['committed_cells']]
        if journal.exists():
            result['journal_pin'] = file_pin(journal)
        result['elapsed_seconds'] = time.monotonic()-started
        if not output.exists():
            with output.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
    print(json.dumps({'accepted': result['accepted'], 'status': result['status'],
                      'reason': result.get('reason')}, ensure_ascii=False), flush=True)
    if not result['accepted']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
