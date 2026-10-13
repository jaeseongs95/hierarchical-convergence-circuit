"""Pinned exact verification of the fixed first-ON real critical strip.

The producer is never imported. Earlier exact helpers and raw-model binding
are reused; strip coverage, signs and augmented fold obligations are new.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time


REGIONS = [('low', Q(-999, 1000), Q(-1, 4), 96),
           ('middle', Q(-1, 4), Q(9, 10), 128),
           ('high', Q(9, 10), Q(999, 1000), 32)]
EDGE_Y = [Q(-999, 1000), Q(-1, 4), Q(9, 10), Q(999, 1000)]
BUDGET = {'conditional_iterations': 200, 'h_cells': 4, 'max_queries': 1100,
          'wall_time_seconds': 1800, 'auto_retry': False}
ARITHMETIC = {'interval_decimal_places': 70, 'taylor_degree': 96}
FOLD_CHECKER_SHA = '90b5038691c774b1705b868f03cfaa524d2216d115dbf23aab7a67cc96827264'
FOLD_PROTOCOL_SHA = '9e9f4cfc432e68e57c5b20dd0bb2c62d11b7b86376aff7228862467b99043ef5'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_partition(cells):
    """Require every fixed cell once, in the frozen region/h/y order."""
    expected = [(name, hi, yi) for name, _, _, n in REGIONS
                for hi in range(4) for yi in range(n)]
    require(isinstance(cells, list) and len(cells) == len(expected), 'cell coverage count')
    ids = []
    for cell, (name, hi, yi) in zip(cells, expected):
        require(isinstance(cell, dict)
                and set(cell) == {'region', 'h_index', 'y_index', 'query'}, 'cell fields')
        require(type(cell['h_index']) is int and type(cell['y_index']) is int
                and (cell['region'], cell['h_index'], cell['y_index']) == (name, hi, yi),
                'cell exact coverage/order mismatch')
        require(isinstance(cell['query'], str), 'cell query reference')
        ids.append(cell['query'])
    require(len(ids) == len(set(ids)), 'reused cell query')
    return expected


def region_sign(region, values):
    if region == 'low':
        return values['Ryy'][1] < 0 and values['Rh'][1] < 0
    if region == 'middle':
        return values['R'][1] < 0
    if region == 'high':
        return values['Ry'][0] > 0
    raise ValueError('unknown region')


def face_binding(query, y, h):
    return query['y'] == (y, y) and query['h'] == tuple(h)


def fold_binding(record, sha):
    return (isinstance(record, dict) and record.get('schema') == 'HCCONFoldCertificates.v1'
            and isinstance(record.get('protocol'), dict)
            and record['protocol'].get('sha256') == sha
            and isinstance(record.get('proposal'), dict)
            and record['proposal'].get('schema') == 'HCCONFoldProposal.v1'
            and record['proposal'].get('protocol_sha256') == sha)


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


def read_pin(repo, ref):
    require(isinstance(ref, dict) and set(ref) == {'path', 'sha256', 'bytes'}, 'dependency fields')
    require(isinstance(ref['path'], str) and isinstance(ref['sha256'], str)
            and len(ref['sha256']) == 64 and all(c in '0123456789abcdef' for c in ref['sha256'])
            and type(ref['bytes']) is int and ref['bytes'] > 0, 'invalid dependency pin')
    path = (repo / ref['path']).resolve()
    require(path.is_relative_to(repo), 'dependency outside repo')
    raw = path.read_bytes()
    require(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'],
            'dependency hash/byte mismatch: ' + ref['path'])
    return path, raw


def verify(document, protocol, sha, repo):
    started = time.monotonic()

    def deadline():
        require(time.monotonic() - started <= BUDGET['wall_time_seconds'], 'wall-time budget exhausted')

    require(protocol.get('schema') == 'HCCONCriticalStripProtocol.v1', 'protocol schema')
    require(protocol.get('budget') == BUDGET and protocol.get('arithmetic') == ARITHMETIC,
            'frozen budget/arithmetic mismatch')
    require(protocol.get('conditional_padding') == '1/1000000000000'
            and protocol.get('regions') == [{'id': n, 'y': [str(a), str(b)], 'cells': c}
                                            for n, a, b, c in REGIONS]
            and protocol.get('edge_y') == list(map(str, EDGE_Y)), 'frozen strip geometry mismatch')
    refs = protocol['dependencies']
    require(isinstance(refs, dict) and set(refs) == {'fold_protocol', 'fold_checker', 'fold_record',
                                                  'workspace', 'dynamics', 'runtime'}, 'dependencies')
    require(refs['fold_checker']['sha256'] == FOLD_CHECKER_SHA
            and refs['fold_protocol']['sha256'] == FOLD_PROTOCOL_SHA, 'unsupported exact helper version')
    pinned = {name: read_pin(repo, ref) for name, ref in refs.items()}
    old = runpy.run_path(str(pinned['fold_checker'][0]), run_name='critical_strip_exact_dependency')
    old_protocol = old['decode'](pinned['fold_protocol'][1])
    old['protocol_check'](old_protocol)
    basin, k, alpha, h0, h1, root_y, root_result = old['model_binding'](repo, old_protocol)
    deadline()
    add, sub, mul, scaled, total = [old[n] for n in ('add', 'sub', 'mul', 'scaled', 'total')]
    point, interval, vector = [old[n] for n in ('point', 'interval', 'vector')]

    def tanh(value):
        return old['rounded'](basin['tanh_enclosure'](value[0])[0],
                              basin['tanh_enclosure'](value[1])[1])

    q_conditional = old['reduction_check'](k, alpha, tanh)
    lmin, lmax = -Q(12, 5) - k - alpha, 2 + k + alpha
    tanh_bounds = tanh((lmin, lmax))
    require(EDGE_Y[0] < tanh_bounds[0] <= tanh_bounds[1] < EDGE_Y[-1],
            'all-root y collar not strictly excluded')
    old['fields'](document, {'schema', 'protocol_sha256', 'cells', 'edges', 'queries', 'discovery'}, 'proposal')
    require(document['schema'] == 'HCCONCriticalStripProposal.v1'
            and document['protocol_sha256'] == sha, 'proposal protocol binding mismatch')
    require(isinstance(document['discovery'], dict), 'discovery diagnostics')
    exact_partition(document['cells'])
    require(isinstance(document['edges'], list) and len(document['edges']) == 4
            and all(isinstance(qid, str) for qid in document['edges'])
            and len(set(document['edges'])) == 4, 'edge query references')
    require(isinstance(document['queries'], list) and len(document['queries']) == 1028
            and len(document['queries']) + 2 <= BUDGET['max_queries'], 'query budget/count')
    queries = {}
    for raw_query in document['queries']:
        deadline()
        require(isinstance(raw_query, dict) and raw_query.get('id') not in queries, 'duplicate query id')
        query = old['check_query'](raw_query, k, alpha, tanh, h0, h1)
        queries[query['id']] = query
    used = set()

    def get(qid, y, h):
        require(isinstance(qid, str) and qid in queries, 'unknown query reference')
        query = queries[qid]
        require(query['y'] == tuple(y) and query['h'] == tuple(h), 'query/domain mismatch: ' + qid)
        require(qid not in used, 'query reference reused')
        used.add(qid)
        return query

    geometry = {n: (a, b, c) for n, a, b, c in REGIONS}
    for cell in document['cells']:
        name, hi, yi = cell['region'], cell['h_index'], cell['y_index']
        a, b, n = geometry[name]
        y = (a + (b - a) * Q(yi, n), a + (b - a) * Q(yi + 1, n))
        h = (h0 + (h1 - h0) * Q(hi, 4), h0 + (h1 - h0) * Q(hi + 1, 4))
        query = get(cell['query'], y, h)
        require(region_sign(name, query), 'strict region sign failed: ' + query['id'])
    faces = []
    for y, qid in zip(EDGE_Y, document['edges']):
        query = get(qid, point(y), (h0, h1))
        require(face_binding(query, y, (h0, h1)), 'whole-h face binding')
        faces.append(query)
    require(all(faces[i]['R'][1] < 0 for i in range(3)) and faces[3]['R'][0] > 0,
            'strict face residual signs')
    require(faces[0]['Ry'][0] > 0 and faces[1]['Ry'][1] < 0, 'strict low face derivative signs')
    require(used == set(queries), 'unreferenced query present')
    record = old['decode'](pinned['fold_record'][1])
    require(fold_binding(record, FOLD_PROTOCOL_SHA), 'fold record/protocol binding mismatch')
    require(record['protocol'] == refs['fold_protocol'], 'fold record exact protocol pin mismatch')
    proposal = record['proposal']
    fold = proposal['fold']
    old['fields'](fold, {'center2', 'box2', 'C2x2', 'center_query', 'box_query'}, 'fold')
    center = vector(fold['center2'], 2)
    require(isinstance(fold['box2'], list) and len(fold['box2']) == 2, 'fold box dimension')
    box = [interval(value) for value in fold['box2']]
    radius = Q(1, 10**8)
    require(box == [(c - radius, c + radius) for c in center]
            and REGIONS[0][1] < box[0][0] < box[0][1] < REGIONS[0][2]
            and h0 < box[1][0] < box[1][1] < h1, 'fold radius/interior mismatch')
    require(isinstance(fold['C2x2'], list) and len(fold['C2x2']) == 2, 'fold C dimension')
    C = [vector(row, 2) for row in fold['C2x2']]
    require(C[0][0] * C[1][1] - C[0][1] * C[1][0] != 0, 'singular fold C')
    required_ids = [fold['center_query'], fold['box_query']]
    require(all(isinstance(qid, str) for qid in required_ids) and len(set(required_ids)) == 2,
            'fold query references')
    selected = {}
    require(isinstance(proposal['queries'], list), 'fold queries')
    for raw_query in proposal['queries']:
        if isinstance(raw_query, dict) and raw_query.get('id') in required_ids:
            require(raw_query['id'] not in selected, 'duplicate selected fold query')
            deadline()
            selected[raw_query['id']] = old['check_query'](raw_query, k, alpha, tanh, h0, h1)
    require(set(selected) == set(required_ids), 'missing selected fold query')
    cq, bq = [selected[qid] for qid in required_ids]
    require(cq['y'] == point(center[0]) and cq['h'] == point(center[1])
            and bq['y'] == box[0] and bq['h'] == box[1], 'fold query/domain mismatch')
    fcenter = [cq['R'], cq['Ry']]
    J = [[bq['Ry'], bq['Rh']], [bq['Ryy'], bq['Ryh']]]
    Tc = [sub(point(center[i]), total([scaled(C[i][j], fcenter[j]) for j in range(2)]))
          for i in range(2)]
    M = [[sub(point(int(i == j)), total([scaled(C[i][l], J[l][j]) for l in range(2)]))
          for j in range(2)] for i in range(2)]
    delta = [sub(box[i], point(center[i])) for i in range(2)]
    image = [add(Tc[i], total([mul(M[i][j], delta[j]) for j in range(2)])) for i in range(2)]
    qmap = max(total([point(old['maxabs'](M[i][j])) for j in range(2)])[1] for i in range(2))
    require(old['certifies_map'](image, box, qmap), 'fold strict contraction/self-inclusion failed')
    require(bq['Rh'][1] < 0 and bq['Ryy'][1] < 0, 'fold nondegeneracy signs')
    deadline()
    return {'schema': 'HCCONCriticalStripCheck.v1', 'protocol_sha256': sha,
            'accepted': True, 'status': 'CERTIFIED',
            'family': {'h_endpoints': [str(h0), str(h1)],
                       'score_endpoints': [str(h0 / 4), str(h1 / 4)],
                       'fixed_first_network_real_family': True},
            'coverage': {'cells': 1024, 'whole_h_faces': 4, 'new_queries': 1028,
                         'reverified_fold_queries': 2, 'uncovered_cells': 0},
            'reduction': {'all_root_rectangle': True, 'conditional_q_upper': str(q_conditional),
                          'root_y_domain': list(map(str, (EDGE_Y[0], EDGE_Y[-1]))),
                          'tanh_L_bounds': old['encode'](tanh_bounds)},
            'fold': {'y_interval': old['encode'](box[0]), 'h_interval': old['encode'](box[1]),
                     'score_interval': old['encode']((box[1][0] / 4, box[1][1] / 4)),
                     'augmented_q_upper': str(qmap), 'image': [old['encode'](i) for i in image]},
            'counts': {'h_below_actual_fold': 3, 'h_at_actual_fold_distinct': 2,
                       'h_above_actual_fold': 1, 'endpoint_h0': 3, 'endpoint_h1': 1},
            'claims': {'unique_equilibrium_degenerate_point': True,
                       'endpoint_anchor_historical_status_used': False},
            'proof': ['Strict low concavity and interior maximum with Rh<0 give a unique zero of m(h).',
                      'Low negative boundary signs imply 2/1/0 roots below/at/above the actual fold.',
                      'Middle has no roots; high strict monotonicity and boundary signs give one root.',
                      'Uniform y collar and exact cell coverage exclude omitted equilibria.'],
            'limits': ['Fixed-first-network exact real family only; no native rounding/stop threshold claim.',
                       'No all-bifurcations, oscillation, stability census or global-basin claim.']}


def self_test():
    cells = [{'region': n, 'h_index': hi, 'y_index': yi, 'query': f'{n}_{hi}_{yi}'}
             for n, _, _, count in REGIONS for hi in range(4) for yi in range(count)]
    exact_partition(cells)
    for changed in (cells[:-1], cells[:1] + cells[:1] + cells[2:]):
        try:
            exact_partition(changed)
        except ValueError:
            pass
        else:
            raise ValueError('coverage gap/reuse accepted')
    require(region_sign('low', {'Ryy': (-2, -1), 'Rh': (-2, -1)}), 'valid strict sign rejected')
    require(not region_sign('low', {'Ryy': (-1, 0), 'Rh': (-2, -1)}), 'weak strict sign accepted')
    require(face_binding({'y': (Q(0), Q(0)), 'h': (Q(1), Q(2))}, Q(0), (Q(1), Q(2))),
            'valid whole-h face rejected')
    require(not face_binding({'y': (Q(0), Q(0)), 'h': (Q(1), Q(1))}, Q(0), (Q(1), Q(2))),
            'point-h face accepted')
    record = {'schema': 'HCCONFoldCertificates.v1', 'protocol': {'sha256': 'p'},
              'proposal': {'schema': 'HCCONFoldProposal.v1', 'protocol_sha256': 'p'}}
    require(fold_binding(record, 'p'), 'valid fold binding rejected')
    record['proposal']['protocol_sha256'] = 'forged'
    require(not fold_binding(record, 'p'), 'forged fold binding accepted')
    print('PASS exact partition, strict signs, whole-h faces and fold binding controls')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--protocol-sha256')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not all((args.repo, args.protocol, args.protocol_sha256, args.input, args.output)):
        parser.error('--repo, --protocol, --protocol-sha256, --input and --output required')
    result = {'schema': 'HCCONCriticalStripCheck.v1', 'protocol_sha256': args.protocol_sha256,
              'accepted': False, 'status': 'INCONCLUSIVE'}
    try:
        raw = args.protocol.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == args.protocol_sha256, 'protocol hash mismatch')
        result = verify(decode(args.input.read_bytes()), decode(raw), args.protocol_sha256, args.repo.resolve())
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
