"""Independent rational verification of a connected local first-ON fold.

The proposal generator is never imported. Pinned earlier Fraction/Taylor and
raw-model checkers are reused; conditional derivatives and all new proof
obligations are evaluated here. No native HCC modules are imported.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys


PLACES, SCALE, TUBES, MAX_QUERIES = 70, 10 ** 70, 64, 400
ORDER = ['e:0', 'e:1', 'p:0:0', 'p:0:1', 'goal']
COND_ORDER = ['e:0', 'p:0:0', 'e:1', 'goal']
IDS = ['swapped-s003-td1-off', 'swapped-s004-td1-off']
RADIUS, GUARD, HALF = Q(1, 10 ** 8), Q(1, 10 ** 6), Q(1, 50)
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), label + ' fields mismatch')


def rational(value):
    require(isinstance(value, str) and len(value) <= 250 and NUMBER.fullmatch(value),
            'invalid rational encoding')
    number = Q(value)
    require(str(number) == value, 'noncanonical rational encoding')
    return number


def vector(value, count):
    require(isinstance(value, list) and len(value) == count, 'vector dimension mismatch')
    return [rational(entry) for entry in value]


def interval(value):
    lo, hi = vector(value, 2)
    require(lo <= hi, 'reversed interval')
    return lo, hi


def point(value):
    value = Q(value)
    return value, value


def rounded(lo, hi):
    # Every arithmetic operation ends on an outward rational 70-place grid.
    lower = Q((lo.numerator * SCALE) // lo.denominator, SCALE)
    upper = Q(-((-hi.numerator * SCALE) // hi.denominator), SCALE)
    require(lower <= upper, 'invalid arithmetic interval')
    return lower, upper


def add(a, b):
    return rounded(a[0] + b[0], a[1] + b[1])


def neg(a):
    return rounded(-a[1], -a[0])


def sub(a, b):
    return add(a, neg(b))


def mul(a, b):
    products = [x * y for x in a for y in b]
    return rounded(min(products), max(products))


def div(a, b):
    require(not b[0] <= 0 <= b[1], 'interval division crosses zero')
    quotients = [x / y for x in a for y in b]
    return rounded(min(quotients), max(quotients))


def square(a):
    lo = Q(0) if a[0] <= 0 <= a[1] else min(a[0] ** 2, a[1] ** 2)
    return rounded(lo, max(a[0] ** 2, a[1] ** 2))


def total(values):
    result = point(0)
    for value in values:
        result = add(result, value)
    return result


def scaled(coefficient, value):
    return mul(point(coefficient), value)


def maxabs(value):
    return max(abs(value[0]), abs(value[1]))


def encode(value):
    return [str(value[0]), str(value[1])]


def pinned(repo, reference):
    fields(reference, {'path', 'sha256', 'bytes'}, 'source pin')
    require(isinstance(reference['path'], str)
            and isinstance(reference['sha256'], str)
            and re.fullmatch('[0-9a-f]{64}', reference['sha256'])
            and type(reference['bytes']) is int and reference['bytes'] > 0,
            'invalid source pin')
    path = (repo / reference['path']).resolve()
    require(path.is_relative_to(repo.resolve()), 'pinned path outside repository')
    data = path.read_bytes()
    require(len(data) == reference['bytes']
            and hashlib.sha256(data).hexdigest() == reference['sha256'],
            'source hash/byte mismatch: ' + reference['path'])
    return data


def protocol_check(protocol):
    require(protocol.get('schema') == 'HCCONFoldProtocol.v1'
            and protocol.get('state_order') == ORDER
            and protocol.get('conditional_order') == COND_ORDER
            and protocol.get('initial_root_index') == 0,
            'unsupported fold protocol binding')
    require(protocol.get('arithmetic') == {'interval_decimal_places': PLACES, 'taylor_degree': 96}
            and protocol.get('budget') == {'newton_iterations': 40,
                                         'conditional_iterations': 200,
                                         'branch_bisections': 80,
                                         'tube_count': TUBES,
                                         'max_queries': MAX_QUERIES,
                                         'auto_retry': False},
            'unsupported frozen arithmetic/budget')
    require(vector(protocol['fold_radius'], 2) == [RADIUS, RADIUS]
            and rational(protocol['parameter_guard']) == GUARD
            and rational(protocol['local_y_halfwidth']) == HALF
            and rational(protocol['conditional_padding']) == Q(1, 10 ** 12)
            and rational(protocol['tube_padding']) == Q(1, 10 ** 7),
            'unsupported frozen geometry')
    fields(protocol['dependencies'], {'basin_protocol', 'basin_checker', 'root_protocol',
                                      'root_record', 'root_checker'}, 'dependencies')


def model_binding(repo, protocol):
    refs = protocol['dependencies']
    data = {name: pinned(repo, ref) for name, ref in refs.items()}
    basin = runpy.run_path(str(repo / refs['basin_checker']['path']), run_name='fold_basin_dependency')
    require(basin['DEGREE'] == 96, 'Taylor degree mismatch')
    bp, rp = decode(data['basin_protocol']), decode(data['root_protocol'])
    basin['protocol_check'](bp)
    models = basin['independent_models'](repo, bp, rp)
    k = (basin['binary'](0.25) + basin['binary'](0.2)) / 2
    alpha = basin['binary'](0.35)
    G_expected = [[k, 0, alpha, 0, 0], [0, k, 0, alpha, 0],
                  [2, 0, k, alpha, 0], [0, 2, 2, k, alpha], [0, 0, 0, 2, k]]
    b0, G0, d0, qiso0 = models[IDS[0]]
    b1, G1, d1, qiso1 = models[IDS[1]]
    require(G0 == G1 == G_expected and d0 == d1 == basin['binary'](0.45)
            and b0 == [4, basin['binary'](0.12), 0, -2, 0]
            and b1 == [4, basin['binary'](0.16), 0, -2, 0]
            and qiso0 == qiso1 < 1 and 0 < d0 <= 1,
            'endpoint exact reduced model mismatch')
    raws, kernels, networks = [], [], []
    for record in bp['models']:
        raw = decode(pinned(repo, {'path': record['raw_path'],
                                   'sha256': record['raw_sha256'], 'bytes': record['raw_bytes']}))
        events = raw['execution']['packet']['document']['events']
        kernels.append(next(e for e in events if e['event'] == 'r02_engine_created')['payload']['config']['kernel'])
        networks.append(next(e for e in events if e['event'] == 'r02_network'
                             and e['payload'].get('kind') == 'decision')['payload'])
        raws.append(raw)
    require(kernels[0] == kernels[1], 'raw kernels differ')
    require([basin['binary'](kernels[0][key]) for key in
             ('temperature', 'damping', 'self_excitation', 'inhibition')]
            == [Q(1), d0, Q(1, 4), basin['binary'](0.2)], 'raw kernel primitive mismatch')
    require(networks[0]['program'] == networks[1]['program']
            and networks[0]['top_down'] is True and networks[1]['top_down'] is True,
            'endpoint graph/group biases differ')
    drives = [{key: basin['binary'](value) for key, value in n['drives'].items()} for n in networks]
    require(set(drives[0]) == set(drives[1]) and 'e:1' in drives[0]
            and [key for key in drives[0] if drives[0][key] != drives[1][key]] == ['e:1'],
            'endpoints are not a single-drive axis')
    h0, h1 = b0[1], b1[1]
    require(drives[0]['e:1'] == h0 and drives[1]['e:1'] == h1
            and h0 / 4 == basin['binary'](raws[0]['cell']['score'])
            and h1 / 4 == basin['binary'](raws[1]['cell']['score'])
            and h0 < h1, 'raw score endpoint mismatch')
    # Exact graph shape also proves the following structural PF hypotheses.
    require(all(value >= 0 for row in G0 for value in row)
            and all(G0[i][i] > 0 for i in range(5)), 'nonpositive PF graph')
    for start in range(5):
        reached = {start}
        for _ in range(5):
            reached |= {target for source in reached for target in range(5)
                        if target != source and G0[target][source] > 0}
        require(len(reached) == 5, 'PF graph is reducible')
    root = runpy.run_path(str(repo / refs['root_checker']['path']), run_name='fold_root_dependency')
    root_models = root['load_models'](repo, rp)
    require(all(root_models[name] == tuple(models[name][:3]) for name in IDS),
            'independent endpoint model mismatch')
    cert = decode(data['root_record'])['discovery']['certificates'][0]
    root_result, root_box = root['check_certificate'](cert, 0, root_models,
                                                     refs['root_protocol']['sha256'])
    require(root_result.get('accepted') is True and root_box is not None
            and cert['model_id'] == IDS[0], 'initial low root reverification failed')
    return basin, k, alpha, h0, h1, (root_box[0][3], root_box[1][3]), root_result


def reduction_check(k, alpha, tanh):
    q = max((k + alpha) * Q(19, 100), (2 + k) * Q(36, 100), k)
    require(0 < k < Q(1, 4) and 0 < alpha < Q(7, 20) + Q(1, 10 ** 10)
            and q < 1, 'conditional uniform contraction failed')
    require(tanh(point(4 - k - alpha))[0] > Q(9, 10)
            and tanh(point(Q(9, 5) - k - alpha))[0] > Q(4, 5),
            'all-root rectangle entry not established')
    require(tanh(point(4 + k * Q(9, 10) + alpha * Q(4, 5)))[0] > Q(9, 10)
            and tanh(point(Q(9, 5) + k * Q(4, 5) - alpha))[0] > Q(4, 5),
            'conditional rectangle invariance failed')
    return q


def residual_derivatives(y, h, states, k, alpha, tanh):
    a, u, v, g = states

    def EK(x):
        sigma = sub(point(1), square(x))
        denom = sub(point(1), scaled(k, sigma))
        require(denom[0] > 0, 'implicit scalar denominator not positive')
        e = div(sigma, denom)
        cube = mul(square(denom), denom)
        curvature = div(scaled(-2, mul(x, sigma)), cube)
        return e, curvature

    ea, ka = EK(a)
    eu, ku = EK(u)
    ev, kv = EK(v)
    eg, kg = EK(g)
    denom = sub(point(1), scaled(2 * alpha, mul(ea, eu)))
    require(denom[0] > 0, 'conditional two-state derivative denominator not positive')
    uy = div(scaled(alpha, eu), denom)
    ay = scaled(alpha, mul(ea, uy))
    uyy = div(add(scaled(2 * alpha ** 2, mul(mul(eu, ka), square(uy))),
                   mul(ku, square(add(scaled(2, ay), point(alpha))))), denom)
    vy, vh = scaled(alpha, ev), ev
    vyy, vyh = scaled(alpha ** 2, kv), scaled(alpha, kv)
    gy, gyy = scaled(2, eg), scaled(4, kg)
    L = total([point(-2), scaled(2, v), scaled(2, u), scaled(k, y), scaled(alpha, g)])
    r = tanh(L)  # MUTATION_TARGET_OFFROOT: r is tanh(L), never the free coordinate y.
    sigma = sub(point(1), square(r))
    Ly = total([scaled(2, vy), scaled(2, uy), point(k), scaled(alpha, gy)])
    Lh = scaled(2, vh)
    Lyy = total([scaled(2, vyy), scaled(2, uyy), scaled(alpha, gyy)])
    Lyh = scaled(2, vyh)
    return {'R': sub(y, r), 'Ry': sub(point(1), mul(sigma, Ly)),
            'Rh': neg(mul(sigma, Lh)),
            'Ryy': sub(scaled(2, mul(mul(r, sigma), square(Ly))), mul(sigma, Lyy)),
            'Ryh': sub(scaled(2, mul(mul(mul(r, sigma), Ly), Lh)), mul(sigma, Lyh))}


def check_query(query, k, alpha, tanh, h0, h1):
    fields(query, {'id', 'y', 'h', 'lower4', 'upper4'}, 'query')
    require(isinstance(query['id'], str) and re.fullmatch('[A-Za-z0-9_-]{1,80}', query['id']),
            'invalid query id')
    y, h = interval(query['y']), interval(query['h'])
    require(-1 < y[0] <= y[1] < 1 and h0 <= h[0] <= h[1] <= h1,
            'query outside continuous model domain')
    lower, upper = vector(query['lower4'], 4), vector(query['upper4'], 4)
    require(all(-1 < lo < hi < 1 for lo, hi in zip(lower, upper))
            and lower[0] >= Q(9, 10) and lower[1] >= Q(4, 5),
            'invalid conditional state rectangle')
    states = list(zip(lower, upper))
    a, u, v, g = states
    images = [tanh(total([point(4), scaled(k, a), scaled(alpha, u)])),
              tanh(total([scaled(2, a), scaled(k, u), scaled(alpha, y)])),
              tanh(total([h, scaled(k, v), scaled(alpha, y)])),
              tanh(total([scaled(2, y), scaled(k, g)]))]
    require(all(lo < image[0] and image[1] < hi
                for lo, hi, image in zip(lower, upper, images)),
            'conditional parameter-rectangle self-inclusion failed: ' + query['id'])
    values = residual_derivatives(y, h, states, k, alpha, tanh)
    return {'id': query['id'], 'y': y, 'h': h, 'states': states, **values}


def certifies_map(image, box, q):
    # MUTATION_TARGET_STRICTMAP: equality and q=1 never certify a contraction.
    return (bool(box) and len(image) == len(box) and 0 <= q < 1
            and all(b[0] < a[0] <= a[1] < b[1] for a, b in zip(image, box)))


def valid_chain_endpoints(intervals, start, finish):
    # MUTATION_TARGET_CHAIN: no gap, overlap, or reordered parameter intervals.
    return (bool(intervals) and intervals[0][0] == start and intervals[-1][1] == finish
            and all(lo < hi for lo, hi in intervals)
            and all(left[1] == right[0] for left, right in zip(intervals, intervals[1:])))


def verify(document, protocol, sha, repo):
    fields(document, {'schema', 'protocol_sha256', 'fold', 'critical', 'tubes',
                       'joins', 'queries', 'discovery'}, 'proposal')
    require(document['schema'] == 'HCCONFoldProposal.v1' and document['protocol_sha256'] == sha,
            'proposal protocol binding mismatch')
    require(isinstance(document['queries'], list) and 0 < len(document['queries']) <= MAX_QUERIES,
            'query budget exceeded')
    require(isinstance(document['discovery'], dict), 'invalid discovery diagnostics')
    basin, k, alpha, h0, h1, root_y, root_result = model_binding(repo, protocol)

    def tanh(value):
        return rounded(basin['tanh_enclosure'](value[0])[0],
                       basin['tanh_enclosure'](value[1])[1])

    q_conditional = reduction_check(k, alpha, tanh)
    queries = {}
    for query in document['queries']:
        require(isinstance(query, dict) and query.get('id') not in queries, 'duplicate query id')
        result = check_query(query, k, alpha, tanh, h0, h1)
        queries[result['id']] = result
    used = set()

    def get(query_id, y, h):
        require(isinstance(query_id, str) and query_id in queries, 'unknown query reference')
        query = queries[query_id]
        require(query['y'] == tuple(y) and query['h'] == tuple(h),
                'query/domain binding mismatch: ' + query_id)
        used.add(query_id)
        return query

    fold = document['fold']
    fields(fold, {'center2', 'box2', 'C2x2', 'center_query', 'box_query'}, 'fold')
    center = vector(fold['center2'], 2)
    require(isinstance(fold['box2'], list) and len(fold['box2']) == 2, 'fold box dimension')
    box = [interval(entry) for entry in fold['box2']]
    require(box == [(value - RADIUS, value + RADIUS) for value in center]
            and h0 < box[1][0] < box[1][1] < h1, 'fold frozen radius/interior mismatch')
    require(isinstance(fold['C2x2'], list) and len(fold['C2x2']) == 2, 'preconditioner dimension')
    C = [vector(row, 2) for row in fold['C2x2']]
    require(C[0][0] * C[1][1] - C[0][1] * C[1][0] != 0, 'singular rational preconditioner')
    cq = get(fold['center_query'], point(center[0]), point(center[1]))
    bq = get(fold['box_query'], box[0], box[1])
    fcenter = [cq['R'], cq['Ry']]
    J = [[bq['Ry'], bq['Rh']], [bq['Ryy'], bq['Ryh']]]
    Tc = [sub(point(center[i]), total([scaled(C[i][j], fcenter[j]) for j in range(2)]))
          for i in range(2)]
    M = [[sub(point(int(i == j)), total([scaled(C[i][l], J[l][j]) for l in range(2)]))
          for j in range(2)] for i in range(2)]
    delta = [sub(box[i], point(center[i])) for i in range(2)]
    image = [add(Tc[i], total([mul(M[i][j], delta[j]) for j in range(2)])) for i in range(2)]
    radii = [RADIUS, RADIUS]
    qmap = max(total([point(maxabs(M[i][j]) * radii[j] / radii[i])
                      for j in range(2)])[1] for i in range(2))
    require(certifies_map(image, box, qmap), 'fold augmented contraction/self-inclusion failed')

    critical = document['critical']
    fields(critical, {'y2', 'h_low', 'h_high', 'rect_query', 'low_left', 'low_center',
                       'low_right', 'high_center'}, 'critical')
    cy = interval(critical['y2'])
    hlo, hhi = rational(critical['h_low']), rational(critical['h_high'])
    require(cy == (center[0] - HALF, center[0] + HALF)
            and hlo == box[1][0] - GUARD and hhi == box[1][1] + GUARD
            and h0 < hlo < hhi < h1 and -1 < cy[0] < cy[1] < 1,
            'critical frozen geometry mismatch')
    rect = get(critical['rect_query'], cy, (hlo, hhi))
    require(rect['Rh'][1] < 0 and rect['Ryy'][1] < 0, 'critical nondegeneracy/concavity failed')
    left = get(critical['low_left'], point(cy[0]), point(hlo))
    middle = get(critical['low_center'], point(center[0]), point(hlo))
    right = get(critical['low_right'], point(cy[1]), point(hlo))
    upper = get(critical['high_center'], point(center[0]), point(hhi))
    require(left['R'][1] < 0 and middle['R'][0] > 0 and right['R'][1] < 0,
            'local two-root sign certificate failed')
    curvature = -rect['Ryy'][1]
    no_root_bound = upper['R'][1] + maxabs(upper['Ry']) ** 2 / (2 * curvature)
    require(no_root_bound < 0, 'local high-parameter no-root certificate failed')

    tubes = document['tubes']
    require(isinstance(tubes, list) and len(tubes) == TUBES, 'stable tube count mismatch')
    grid = [h0 + (hlo - h0) * (1 - (1 - Q(i, TUBES)) ** 2) for i in range(TUBES + 1)]
    tube_y, tube_h = [], []
    for i, tube in enumerate(tubes):
        fields(tube, {'h2', 'y2', 'rect_query', 'left_query', 'right_query'}, 'tube')
        h, y = interval(tube['h2']), interval(tube['y2'])
        require(h == (grid[i], grid[i + 1]) and y[0] < y[1], 'tube frozen grid mismatch')
        whole = get(tube['rect_query'], y, h)
        low = get(tube['left_query'], point(y[0]), point(h[0]))
        high = get(tube['right_query'], point(y[1]), point(h[1]))
        require(whole['Ry'][0] > 0 and whole['Rh'][1] < 0
                and low['R'][1] < 0 and high['R'][0] > 0,
                'stable tube IVT/uniqueness/stability failed: ' + str(i))
        tube_y.append(y)
        tube_h.append(h)
    require(valid_chain_endpoints(tube_h, h0, hlo), 'stable parameter chain has gap')
    require(tube_y[0][0] < root_y[0] <= root_y[1] < tube_y[0][1],
            'initial root0 full y projection not contained')
    require(cy[0] < tube_y[-1][0] < tube_y[-1][1] < box[0][0]
            and tube_h[-1][1] == hlo, 'low branch not joined to left local root')
    joins = document['joins']
    require(isinstance(joins, list) and len(joins) == TUBES - 1, 'join count mismatch')
    for i, join in enumerate(joins):
        fields(join, {'h', 'y2', 'left_query', 'right_query'}, 'join')
        h, y = rational(join['h']), interval(join['y2'])
        intersection = (max(tube_y[i][0], tube_y[i + 1][0]),
                        min(tube_y[i][1], tube_y[i + 1][1]))
        require(y == intersection and y[0] < y[1] and h == tube_h[i][1] == tube_h[i + 1][0],
                'join does not match exact adjacent intersection')
        low = get(join['left_query'], point(y[0]), point(h))
        high = get(join['right_query'], point(y[1]), point(h))
        require(low['R'][1] < 0 and high['R'][0] > 0, 'join common-root IVT failed')
    require(used == set(queries), 'unreferenced query present')
    return {'schema': 'HCCONFoldCheck.v1', 'protocol_sha256': sha, 'accepted': True,
            'family': {'parameter': 'exact real drive h; score s=h/4',
                       'h_endpoints': [str(h0), str(h1)],
                       'score_endpoints': [str(h0 / 4), str(h1 / 4)],
                       'only_e1_drive_differs': True, 'graph_primitive': True},
            'reduction': {'conditional_order': COND_ORDER, 'all_root_rectangle': True,
                          'conditional_q_upper': str(q_conditional),
                          'verified_query_count': len(queries),
                          'implicit_derivatives_off_root': True},
            'fold': {'y_interval': encode(box[0]), 'h_interval': encode(box[1]),
                     'score_interval': encode((box[1][0] / 4, box[1][1] / 4)),
                     'augmented_q_upper': str(qmap), 'image': [encode(i) for i in image],
                     'local_Rh': encode(rect['Rh']), 'local_Ryy': encode(rect['Ryy']),
                     'simple_multiplier_plus_one': True},
            'localpairs': {'h_low': str(hlo), 'h_high': str(hhi),
                           'lower_parameter_root_count_in_local_rectangle': 2,
                           'higher_parameter_root_count_in_local_rectangle': 0,
                           'higher_parameter_residual_upper': str(no_root_bound),
                           'left_root_stable_right_root_unstable': True},
            'connectedbranch': {'initial_root_index': 0, 'initial_y_projection': encode(root_y),
                                'initial_root_reverification': root_result,
                                'stable_tubes': TUBES, 'common_root_joins': TUBES - 1,
                                'parameter_gap_count': 0, 'low_branch_reaches_local_fold': True},
            'limits': ['Connected local low-branch saddle-node only; global unique critical point UNKNOWN.',
                       'No intermediate global root count or full basin-boundary claim.',
                       'Fixed-first-network real family; native binary64 recurrence/160tick/latergraph not certified.']}


def self_test():
    # A synthetic exact-state example distinguishes r=tanh(L) from free y.
    def exp_bounds(u):
        term = partial = Q(1)
        for divisor in range(1, 97):
            term = term * u / divisor
            partial += term
        return partial, partial + term * u / 97 / (1 - u / 98)

    def scalar_tanh(value):
        if value < 0:
            lo, hi = scalar_tanh(-value)
            return -hi, -lo
        lo, hi = exp_bounds(2 * value)
        return (lo - 1) / (lo + 1), (hi - 1) / (hi + 1)

    def tanh(value):
        return rounded(scalar_tanh(value[0])[0], scalar_tanh(value[1])[1])

    derivatives = residual_derivatives(point(0), point(0), [point(0)] * 4, Q(0), Q(0), tanh)
    require(Q(-1, 5) < derivatives['Rh'][0] <= derivatives['Rh'][1] < Q(-1, 10),
            'off-root derivative control failed')
    require(certifies_map([(Q(-1, 4), Q(1, 4))], [(Q(-1), Q(1))], Q(1, 2)),
            'valid synthetic map rejected')
    require(not certifies_map([(Q(-1), Q(1, 4))], [(Q(-1), Q(1))], Q(1, 2)),
            'strict map boundary accepted')
    require(not certifies_map([(Q(-1, 4), Q(1, 4))], [(Q(-1), Q(1))], Q(1)),
            'q=1 accepted')
    require(valid_chain_endpoints([(Q(0), Q(1)), (Q(1), Q(2))], Q(0), Q(2)),
            'valid chain rejected')
    require(not valid_chain_endpoints([(Q(0), Q(1)), (Q(3, 2), Q(2))], Q(0), Q(2)),
            'branch gap accepted')
    require(square((Q(-2), Q(1))) == (Q(0), Q(4)), 'interval square crossing zero')
    require(div(point(1), (Q(-2), Q(-1))) == (Q(-1), Q(-1, 2)), 'negative divisor enclosure')
    for value in ('-0', '1/1', '2/4', '+1', '01', '1.0', 'NaN'):
        try:
            rational(value)
        except ValueError:
            pass
        else:
            raise ValueError('invalid rational accepted: ' + value)
    print('PASS fold off-root, strict contraction, exact chain and rational boundary checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--protocol-sha256')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not all((args.protocol, args.protocol_sha256, args.input, args.output)):
        parser.error('--protocol, --protocol-sha256, --input and --output required')
    result = {'schema': 'HCCONFoldCheck.v1', 'protocol_sha256': args.protocol_sha256,
              'accepted': False, 'status': 'INCONCLUSIVE'}
    try:
        raw = args.protocol.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == args.protocol_sha256, 'protocol hash mismatch')
        protocol = decode(raw)
        protocol_check(protocol)
        result = verify(decode(args.input.read_bytes()), protocol, args.protocol_sha256, args.repo.resolve())
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, OSError) as error:
        result['reason'] = str(error)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'accepted': result['accepted'], 'reason': result.get('reason')}, ensure_ascii=False))
    if not result['accepted']:
        sys.exit(1)


if __name__ == '__main__':
    main()
