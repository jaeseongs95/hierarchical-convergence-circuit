"""EXP-16 독립 검산. selection/native_bridge/transforms의 실행 함수를 호출하지 않는다.

선택 순서·가정·DAG 의미·깊이·예산·재표현 일대일 대응을 원자료에서 재계산한다.
원 native trajectory 검산은 별도 source_audit 경로에서 기존 EXP-15 auditor를 재사용한다.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from math import isfinite


class AuditError(ValueError):
    """독립 evaluator 불일치. 논리 실패나 보류로 바꾸지 않는다."""


def demand(ok, message):
    if not ok: raise AuditError(message)


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def view_check(v):
    demand(isinstance(v, dict) and set(v) == {'schema', 'observation', 'raw_value', 'state',
        'completed_paths', 'graph_complete', 'original_proof', 'min_abs_score'}, 'audit/public fields')
    demand(v['schema'] == 'hcr-frozen-proof-view-r035-v1', 'audit/public schema')
    demand(type(v['raw_value']) in (bool, type(None)) and type(v['graph_complete']) is bool, 'audit/typed value')
    o = v['observation']; e = o['edges']; p = v['completed_paths']; state = v['state']
    demand(set(o) == {'episode_id', 'revision', 'start', 'goal', 'edges'} and o['start'] != o['goal'], 'audit/observation')
    demand(type(o['revision']) is int and o['revision'] >= 0, 'audit/revision')
    demand(all(isinstance(o[k], str) and o[k] for k in ('episode_id', 'start', 'goal')), 'audit/ids')
    demand(isinstance(e, list) and 0 < len(e) <= 8 and all(isinstance(x, dict) for x in e), 'audit/edge range')
    for x in e:
        demand(set(x) == {'id', 'source', 'target', 'score'} and x['source'] != x['target'], 'audit/edge fields')
        demand(all(isinstance(x[k], str) and x[k] for k in ('id', 'source', 'target')), 'audit/edge ids')
        s = x['score']
        demand(s is None or type(s) in (float, int) and isfinite(s) and -1 <= s <= 1, 'audit/score')
    demand(len({x['id'] for x in e}) == len(e) and len({(x['source'], x['target']) for x in e}) == len(e), 'audit/duplicate edges')
    demand(isinstance(p, list) and len(p) <= 4 and all(isinstance(x, list) for x in p), 'audit/paths')
    demand(all(all(type(s) is int and 0 <= s < len(e) for s in path) for path in p), 'audit/slot type')
    demand(len({tuple(x) for x in p}) == len(p), 'audit/duplicate paths')
    expected = {'goal'} | {f'e:{i}' for i in range(len(e))}
    for pi, path in enumerate(p):
        demand(0 < len(path) <= 4, 'audit/path length')
        links = [e[i] for i in path]
        vertices = [o['start']] + [x['target'] for x in links]
        demand(links[0]['source'] == o['start'] and links[-1]['target'] == o['goal'], 'audit/path endpoints')
        demand(all(a['target'] == b['source'] for a, b in zip(links, links[1:])), 'audit/path continuity')
        demand(len(vertices) == len(set(vertices)), 'audit/path cycle')
        expected |= {f'p:{pi}:{j}' for j in range(len(path))}
    demand(isinstance(state, dict) and (set(state) == expected or not p and not state), 'audit/state identity')
    demand(all(type(s) in (int, float) and isfinite(s) and 0 <= s <= 1 for s in state.values()), 'audit/state value')
    threshold = v['min_abs_score']
    demand(type(threshold) in (int, float) and isfinite(threshold) and 0 <= threshold < 1, 'audit/threshold')
    demand(isinstance(v['original_proof'], dict), 'audit/original proof')


def check_transform(source, wrapped):
    view_check(source)
    demand(set(wrapped) == {'schema', 'variant', 'source_input_sha256', 'maps', 'input', 'boundary'}, 'audit/transform fields')
    demand(wrapped['schema'] == 'hcr-frozen-transform-r035-v1' and wrapped['boundary'] == 'post_readout_selector_only', 'audit/transform scope')
    demand(wrapped['source_input_sha256'] == sha(source), 'audit/transform source hash')
    variant = wrapped['variant']; m = wrapped['maps']; dest = wrapped['input']; view_check(dest)
    bits = ('node_alias', 'edge_alias', 'edge_reverse', 'path_reverse')
    demand(set(variant) == set(bits) | {'id'} and all(type(variant[k]) is bool for k in bits), 'audit/variant fields')
    demand(variant['id'] == 'v'+''.join(str(int(variant[k])) for k in bits), 'audit/variant id')
    demand(set(m) == {'node_names', 'edge_names', 'edge_new_to_old', 'path_new_to_old'}, 'audit/map fields')
    o = source['observation']; edges = o['edges']; paths = source['completed_paths']
    vertices = sorted(set([x['source'] for x in edges] + [x['target'] for x in edges])); ids = sorted(x['id'] for x in edges)
    nm = {n: ('n_%03d' % (len(vertices)-i-1) if variant['node_alias'] else n) for i, n in enumerate(vertices)}
    em = {n: ('q_%03d' % (len(ids)-i-1) if variant['edge_alias'] else n) for i, n in enumerate(ids)}
    eo = sorted(range(len(edges)), reverse=variant['edge_reverse']); po = sorted(range(len(paths)), reverse=variant['path_reverse'])
    demand(m == dict(node_names=nm, edge_names=em, edge_new_to_old=eo, path_new_to_old=po), 'audit/unregistered or non-bijective map')
    demand(dest['observation']['episode_id'] == o['episode_id'] and dest['observation']['revision'] == o['revision'], 'audit/revision changed')
    demand(dest['observation']['start'] == nm[o['start']] and dest['observation']['goal'] == nm[o['goal']], 'audit/transformed endpoints')
    for i, old in enumerate(eo):
        a = edges[old]; b = dest['observation']['edges'][i]
        demand(b == dict(id=em[a['id']], source=nm[a['source']], target=nm[a['target']], score=a['score']), 'audit/edge transport')
    expected_state = {}
    for old_name, value in source['state'].items():
        parts = old_name.split(':')
        new_name = ('e:'+str(eo.index(int(parts[1]))) if parts[0] == 'e' else
                    'p:'+str(po.index(int(parts[1])))+':'+parts[2] if parts[0] == 'p' else old_name)
        expected_state[new_name] = value
    demand(dest['state'] == expected_state, 'audit/activation transport')
    wanted_paths = [[eo.index(s) for s in paths[old]] for old in po]
    demand(dest['completed_paths'] == wanted_paths, 'audit/route transport')
    demand(all(dest[k] == source[k] for k in ('raw_value', 'graph_complete', 'min_abs_score')), 'audit/semantic scalar changed')
    proof = deepcopy(source['original_proof'])
    for node in proof['nodes']:
        if node['edge_id'] is not None: node['edge_id'] = em[node['edge_id']]
        if node['path_index'] is not None: node['path_index'] = po.index(node['path_index'])
    proof['assumed_edges'] = sorted([em[eid], value] for eid, value in proof['assumed_edges'])
    if proof['paths']: proof['paths'] = [[em[eid] for eid in source['original_proof']['paths'][old]] for old in po]
    demand(dest['original_proof'] == proof, 'audit/original proof transport')
    return dest


def check_proof(v, proof):
    """노드 ID를 의미로 추측하지 않고 dependency를 따라 proof DAG를 해석한다."""
    if proof is None:
        return dict(valid=False, selected_path=None, depth=None, assumptions={}, feature_slots={})
    demand(set(proof) == {'nodes', 'final', 'primitive_depth', 'assumed_edges', 'under_assumptions_valid', 'paths'}, 'audit/proof fields')
    demand(type(proof['under_assumptions_valid']) is bool and isinstance(proof['nodes'], list) and len(proof['nodes']) <= 128, 'audit/proof type')
    edges = v['observation']['edges']; paths = v['completed_paths']; edge_slots = {e['id']: i for i, e in enumerate(edges)}
    expected_paths = [[edges[s]['id'] for s in p] for p in paths] if v['raw_value'] is not None else []
    demand(proof['paths'] == expected_paths, 'audit/proof paths')
    meanings = {}; depths = {}; features = {}; feature_slots = {}
    for n in proof['nodes']:
        demand(isinstance(n, dict) and set(n) == {'id', 'rule', 'edge_id', 'parents', 'path_index'}, 'audit/node fields')
        ident = n['id']; parents = n['parents']; rule = n['rule']; pi = n['path_index']
        demand(isinstance(ident, str) and ident and ident not in meanings, 'audit/duplicate node')
        demand(isinstance(parents, list) and len(set(parents)) == len(parents) and all(p in meanings for p in parents), 'audit/missing parent/cycle/order')
        if pi is not None: demand(type(pi) is int and 0 <= pi < len(paths), 'audit/path index')
        ps = [meanings[p] for p in parents]
        if rule in ('assumed_open', 'assumed_closed'):
            eid = n['edge_id']; truth = rule == 'assumed_open'
            demand(not parents and pi is None and eid in edge_slots and eid not in features, 'audit/feature binding')
            slot = edge_slots[eid]
            demand((v['state'][f'e:{slot}'] >= .5) is truth, 'audit/feature activation disagrees')
            features[eid] = truth; feature_slots[eid] = slot
            meanings[ident] = ('edge', slot, truth); depths[ident] = 0
        elif rule == 'start_edge':
            demand(n['edge_id'] is None and pi is not None and len(ps) == 1 and ps[0] == ('edge', paths[pi][0], True), 'audit/start rule')
            meanings[ident] = ('path', pi, (paths[pi][0],)); depths[ident] = 1 + depths[parents[0]]
        elif rule == 'extend_path':
            demand(n['edge_id'] is None and pi is not None and len(ps) == 2 and ps[0][0:2] == ('path', pi), 'audit/extend binding')
            prefix = ps[0][2]
            demand(len(prefix) < len(paths[pi]) and ps[1] == ('edge', paths[pi][len(prefix)], True), 'audit/extend edge')
            meanings[ident] = ('path', pi, prefix + (ps[1][1],)); depths[ident] = 1 + max(depths[p] for p in parents)
        elif rule == 'path_blocked':
            demand(n['edge_id'] is None and pi is not None and len(ps) == 1 and ps[0][0] == 'edge'
                   and ps[0][2] is False and ps[0][1] in paths[pi], 'audit/cut rule')
            meanings[ident] = ('cut', pi, ps[0][1]); depths[ident] = 1 + depths[parents[0]]
        elif rule == 'all_paths_blocked':
            demand(n['edge_id'] is None and pi is None and ps and all(p[0] == 'cut' for p in ps)
                   and sorted(p[1] for p in ps) == list(range(len(paths))), 'audit/negative coverage')
            meanings[ident] = ('negative',); depths[ident] = 1 + max(depths[p] for p in parents)
        else: raise AuditError('audit/unknown rule: '+str(rule))
    assumptions = proof['assumed_edges']
    demand(isinstance(assumptions, list) and all(isinstance(x, list) and len(x) == 2 and type(x[1]) is bool for x in assumptions), 'audit/assumption type')
    demand(assumptions == sorted([[k, t] for k, t in features.items()]), 'audit/assumption inventory')
    final = proof['final']; selected = None
    demand(proof['primitive_depth'] is None or type(proof['primitive_depth']) is int and proof['primitive_depth'] >= 0, 'audit/depth type')
    demand(final is None or final in meanings, 'audit/missing final')
    valid = final is not None
    demand(proof['under_assumptions_valid'] is valid, 'audit/reported validity')
    demand(proof['primitive_depth'] == (depths[final] if final is not None else None), 'audit/D_DAG')
    if final is not None:
        m = meanings[final]
        if v['raw_value'] is True:
            demand(m[0] == 'path' and m[2] == tuple(paths[m[1]]), 'audit/final positive goal'); selected = m[1]
        else:
            demand(v['raw_value'] is False and m == ('negative',), 'audit/final negative value')
        # 유효한 증명의 모든 노드는 최종 노드의 조상이어야 한다.
        by_id = {n['id']: n for n in proof['nodes']}; seen = set(); stack = [final]
        while stack:
            x = stack.pop()
            if x not in seen: seen.add(x); stack.extend(by_id[x]['parents'])
        demand(seen == set(by_id), 'audit/unused proof nodes')
    return dict(valid=valid, selected_path=selected, depth=depths.get(final), assumptions=features, feature_slots=feature_slots)


def audit_result(v, out):
    view_check(v)
    fields = {'schema', 'policy', 'input_sha256', 'limits', 'applicable', 'proof', 'selected_path_index',
        'accepted', 'value', 'reason', 'selection_trace', 'usage', 'gate_reason', 'boundaries', 'wall_seconds'}
    demand(set(out) == fields and out['schema'] == 'hcr-frozen-proof-result-r035-v1', 'audit/result fields')
    demand(out['input_sha256'] == sha(v), 'audit/result source hash')
    policy = out['policy']; demand(policy in ('native_saved', 'native_rebuild', 'support_first'), 'audit/policy')
    demand(type(out['accepted']) is bool and type(out['value']) in (bool, type(None)) and type(out['applicable']) is bool, 'audit/result types')
    demand(out['selected_path_index'] is None or type(out['selected_path_index']) is int, 'audit/selected path type')
    demand(isinstance(out['usage'], dict) and all(v is None or type(v) is int and v >= 0 for v in out['usage'].values()), 'audit/usage types')
    cap = out['limits']; default = dict(max_ranked_paths=64, max_path_checks=64, max_edge_checks=256, max_proof_nodes=128)
    demand(set(cap) == set(default) and all(type(x) is int and 0 <= x <= 100000 for x in cap.values()), 'audit/budgets')
    demand(policy == 'support_first' or cap == default, 'audit/non-support ablation')
    demand(type(out['wall_seconds']) in (int, float) and isfinite(out['wall_seconds']) and out['wall_seconds'] >= 0, 'audit/time')
    demand(out['boundaries'] == dict(new_kernel_ticks=0, measurements=0, memory_updates=0,
        input_modified=False, raw_value_changed=False, new_routes_generated=False), 'audit/boundaries')
    actual = check_proof(v, out['proof']); expected_pi = None
    usage = dict(ranked_paths=0, path_checks=0, edge_checks=0, proof_nodes_created=0,
                 proof_nodes_reused=0, gate_assumptions_checked=len(actual['assumptions']))
    trace = []; raw = v['raw_value']; paths = v['completed_paths']; state = v['state']; edges = v['observation']['edges']
    applicable = raw is not None
    if policy == 'native_saved' or policy == 'support_first' and raw is not True:
        demand(out['proof'] == v['original_proof'], 'audit/native proof not preserved')
        usage['proof_nodes_reused'] = len(out['proof']['nodes'])
        reason = 'retained_native_proof' if policy == 'native_saved' else 'nonpositive_native_passthrough'
        if policy == 'support_first': applicable = False
        expected_pi = actual['selected_path']
    elif policy == 'native_rebuild':
        demand(out['proof'] is not None, 'audit/rebuild proof missing')
        usage.update(ranked_paths=None, path_checks=None, edge_checks=None,
                     proof_nodes_created=len(out['proof']['nodes']))
        reason = 'native_reconstructed'
        if raw is True:
            choices = [i for i in range(len(paths)) if all(state[f'e:{s}'] >= .5 for s in paths[i])]
            expected_pi = min(choices, key=lambda i: (-state[f'p:{i}:{len(paths[i])-1}'], i)) if choices else None
            demand(actual['selected_path'] == expected_pi and actual['valid'] is (expected_pi is not None), 'audit/native ranking')
            demand(len(out['proof']['nodes']) == (2 * len(paths[expected_pi]) if expected_pi is not None else 0), 'audit/native node count')
        elif raw is False:
            cuts = []
            for i, path in enumerate(paths):
                eligible = [s for s in path if state[f'e:{s}'] < .5]
                if not eligible: break
                chosen = min(eligible, key=lambda s: (state[f'e:{s}'], s)); cuts.append((i, chosen))
            found = [(n['path_index'], actual['feature_slots'][next(x['edge_id'] for x in out['proof']['nodes'] if x['id'] == n['parents'][0])])
                     for n in out['proof']['nodes'] if n['rule'] == 'path_blocked']
            demand(found == cuts and actual['valid'] is (len(cuts) == len(paths) and bool(paths)), 'audit/native negative ranking')
        else:
            demand(not out['proof']['nodes'] and not actual['valid'], 'audit/None proof')
    else:
        ordered = sorted(range(len(paths)), key=lambda i: (-state[f'p:{i}:{len(paths[i])-1}'], i))
        reason = 'no_supported_existing_path'
        if len(ordered) > cap['max_ranked_paths']: reason = 'ranking_budget'
        else:
            usage['ranked_paths'] = len(ordered)
            for pi in ordered:
                p = paths[pi]
                if usage['path_checks'] == cap['max_path_checks'] or usage['edge_checks'] + len(p) > cap['max_edge_checks']:
                    reason = 'scan_budget'; break
                usage['path_checks'] += 1; usage['edge_checks'] += len(p)
                a = not any(state[f'e:{s}'] < .5 for s in p)
                b = not any(edges[s]['score'] is None or edges[s]['score'] <= v['min_abs_score'] for s in p)
                trace.append(dict(path_index=pi, activation_eligible=a, observation_supported=b))
                if a and b:
                    if 2 * len(p) > cap['max_proof_nodes']: reason = 'proof_budget'
                    else:
                        expected_pi = pi; reason = 'supported_existing_positive_path'; usage['proof_nodes_created'] = 2 * len(p)
                    break
        demand(actual['selected_path'] == expected_pi, 'audit/support-first ranking')
        demand((out['proof'] is not None) is (expected_pi is not None), 'audit/support proof absent/present')
        if expected_pi is not None: demand(actual['valid'], 'audit/selected invalid proof')
    supported = []
    lookup = {e['id']: e for e in edges}
    for eid, t in actual['assumptions'].items():
        s = lookup[eid]['score']
        supported.append(s is not None and abs(s) > v['min_abs_score'] and (s > 0) is t)
    accepted = bool(raw is not None and actual['valid'] and supported and all(supported)
                    and (raw is not False or v['graph_complete']))
    demand(out['applicable'] is applicable and out['accepted'] is accepted and out['value'] is (raw if accepted else None), 'audit/gate/value')
    demand(out['selected_path_index'] == expected_pi and out['reason'] == reason, 'audit/selected path/reason')
    demand(out['selection_trace'] == trace and out['usage'] == usage, 'audit/inventory counters')
    demand(out['gate_reason'] == ('supported_under_sign_contract' if accepted else
        'original_abstention' if raw is None else 'dependency_support_abstention'), 'audit/gate reason')
    return dict(verified=True, value=out['value'], accepted=accepted, applicable=applicable,
        D_DAG=actual['depth'], selected_path=expected_pi, supported_assumptions=len(supported),
        proof_valid=actual['valid'], external_correctness_not_required=True)


def reachable(observation, truth):
    edges = observation['edges']
    demand(set(truth) == {e['id'] for e in edges} and all(type(t) is bool for t in truth.values()), 'audit/world contract')
    seen = {observation['start']}; frontier = [observation['start']]
    while frontier:
        vertex = frontier.pop()
        for e in edges:
            if e['source'] == vertex and truth[e['id']] and e['target'] not in seen:
                seen.add(e['target']); frontier.append(e['target'])
    return observation['goal'] in seen
