"""R0.2 감사용 별도 재구성. 생산 expansion/activation/runtime/learning을 호출하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from ..model import ContractError, fingerprint, AdaptiveCost
from .. import codec
from .audit import require


def chain_program(edge_count, paths, k):
    groups = [dict(id='e:' + str(i), level=0, bias=0.0) for i in range(edge_count)]
    links, terminals = [], []
    for number, path in enumerate(paths):
        parent = None
        for depth, slot in enumerate(path):
            key = f'p:{number}:{depth}'
            inputs = ['e:' + str(slot)] + ([] if parent is None else [parent])
            groups.append(dict(id=key, level=1, bias=-k.relation_gain * (len(inputs) - 1)))
            for source in inputs:
                links.append(dict(source=source, target=key, weight=k.relation_gain, kind='support'))
                links.append(dict(source=key, target=source, weight=k.top_down_gain, kind='top_down'))
            parent = key
        terminals.append(parent)
    groups.append(dict(id='goal', level=1, bias=k.relation_gain * (len(terminals) - 1)))
    for terminal in terminals:
        links.extend([dict(source=terminal, target='goal', weight=k.relation_gain, kind='support'),
                      dict(source='goal', target=terminal, weight=k.top_down_gain, kind='top_down')])
    return dict(groups=groups, links=links, paths=[list(p) for p in paths], edge_count=edge_count)


def role_binding(obs, pattern_id, slots):
    vertices = [obs.edges[slots[0]].source] + [obs.edges[i].target for i in slots]
    context = fingerprint((obs.digest, pattern_id, tuple(slots)))[:24]
    return dict(observation_digest=obs.digest, revision=obs.revision, pattern_id=pattern_id,
                roles=[['R' + str(i), dict(node_id=f'binding:{context}:{i}', semantic_id=v,
                                         revision=obs.revision)] for i, v in enumerate(vertices)],
                edge_order=list(slots))


def circuit_id(raw):
    return 'pattern-' + fingerprint(raw['pattern'])[:24]


def scan_patterns(obs, prefix, memory, config, remaining):
    """관측 점수를 보지 않는 별도 DFS로 scan/match 순서와 예산 중단을 복원한다."""
    inspected, scans, matches = [], [], []
    reason = None
    for circuit in sorted(memory['circuits'], key=lambda c: (len(c['pattern']['relations']), circuit_id(c))):
        cid = circuit_id(circuit)
        inspected.append(cid)
        length = len(circuit['pattern']['relations'])
        if not circuit['active'] or len(prefix['path']) + length > config.kernel.max_path_length:
            continue
        def visit(vertex, visited, slots):
            nonlocal reason
            if reason is not None:
                return
            if len(slots) == length:
                matches.append(dict(circuit_id=cid, binding=role_binding(obs, cid, slots)))
                if len(matches) > config.max_pool_candidates:
                    reason = 'pool_capacity'
                return
            if vertex == obs.goal:
                return
            children = []
            for slot, edge in enumerate(obs.edges):
                if len(scans) >= remaining:
                    reason = 'binding_budget'
                    return
                scans.append([cid, list(slots), slot])
                if edge.source == vertex and edge.target not in visited:
                    children.append((edge.target, visited + [edge.target], slots + [slot]))
            for args in children:
                visit(*args)
                if reason is not None:
                    break
        visit(prefix['visited'][-1], list(prefix['visited']), [])
        if reason is not None:
            break
    return dict(inspected=inspected, scans=scans, matched=matches, complete=reason is None, fallback_reason=reason)


def pool_network(obs, records, memory, config):
    k = config.kernel
    lookup = {circuit_id(c): c for c in memory['circuits']}
    groups = [dict(id='e:' + str(i), level=0, bias=0.0) for i in range(len(obs.edges))]
    links = []
    drives = {'e:' + str(i): k.evidence_gain * (edge.score or 0.0) for i, edge in enumerate(obs.edges)}
    metadata, paths = [], []
    instantiated = 0
    for number, record in enumerate(records):
        cid, binding = record['circuit_id'], record['binding']
        c = lookup[cid]
        slots = binding['edge_order']
        require(binding == role_binding(obs, cid, slots), 'pool role/node/revision binding')
        n = len(c['evidence_episodes'])
        prior = k.prior_gain * c['strength'] * (n / (n + 1)) * max(1 - abs(obs.edges[s].score or 0.0) for s in slots)
        mismatch = max(max(0.0, -(obs.edges[s].score or 0.0)) for s in slots)
        translation = {'goal': 'c:' + str(number)}
        for i, slot in enumerate(slots):
            translation['e:' + str(i)] = 'e:' + str(slot)
            translation['p:0:' + str(i)] = 'p:' + str(number) + ':' + str(i)
        for g in c['pattern']['program']['groups']:
            if g['level'] == 1:
                groups.append(dict(id=translation[g['id']], level=1, bias=g['bias']))
                drives[translation[g['id']]] = prior
                instantiated += 1
        for link in c['pattern']['program']['links']:
            links.append(dict(link, source=translation[link['source']], target=translation[link['target']]))
        metadata.append(dict(circuit_id=cid, circuit_version=c['version'], binding=binding, prior=prior, mismatch=mismatch))
        paths.append(list(slots))
    groups.append(dict(id='goal', level=1, bias=k.relation_gain * (len(records) - 1)))
    for i in range(len(records)):
        key = 'c:' + str(i)
        links += [dict(source=key, target='goal', weight=k.relation_gain, kind='support'),
                  dict(source='goal', target=key, weight=k.top_down_gain, kind='top_down')]
        links += [dict(source=key, target='c:' + str(j), weight=-config.circuit_inhibition, kind='support')
                  for j in range(len(records)) if j != i]
    return dict(groups=groups, links=links, paths=paths, edge_count=len(obs.edges)), drives, metadata, instantiated


def decision_network(obs, routes, config, *, judgment_prior="legacy"):
    require(judgment_prior in ("legacy", "route_only"), "unknown judgment policy")
    program = chain_program(len(obs.edges), [r['path'] for r in routes], config.kernel)
    drives = {'e:' + str(i): config.kernel.evidence_gain * (e.score or 0.0) for i, e in enumerate(obs.edges)}
    priors = []
    for pi, route in enumerate(routes):
        for use in route['uses']:
            slots = use['binding']['edge_order']
            require(route['path'][use['offset']:use['offset'] + len(slots)] == slots, 'circuit route span')
            for j in range(use['offset'], use['offset'] + len(slots)):
                key = f'p:{pi}:{j}'
                drives[key] = drives.get(key, 0.0) + (use['prior'] if judgment_prior == 'legacy' else 0.0)
            priors.append(use['prior'] if judgment_prior == 'legacy' else 0.0)
    drives['goal'] = max(priors, default=0.0)
    return program, drives


def plan_expansion(obs, frontier, routes, known, candidate, next_node, config):
    prefix = frontier[0]
    path = prefix['path'] + candidate['edges']
    visited = list(prefix['visited'])
    vertex = visited[-1]
    for slot in candidate['edges']:
        require(type(slot) is int and 0 <= slot < len(obs.edges), 'expansion edge bounds')
        edge = obs.edges[slot]
        require(vertex != obs.goal and edge.source == vertex and edge.target not in visited, 'expansion adjacency/cycle')
        vertex = edge.target
        visited.append(vertex)
    if len(path) > config.kernel.max_path_length:
        return None, 0, 'primitive path length budget; dependency was not silently dropped'
    uses = deepcopy(prefix['uses'])
    if candidate['source'] == 'circuit':
        uses.append(dict(circuit_id=candidate['circuit_id'], circuit_version=candidate['circuit_version'],
                         offset=len(prefix['path']), binding=candidate['binding'], prior=candidate['prior']))
    else:
        require(candidate['source'] == 'primitive' and len(candidate['edges']) == 1, 'primitive expansion arity')
    planned = [(path, visited, uses)]
    checks = len(candidate['edges']) * len(obs.edges)
    for i, selected in enumerate(candidate['edges']):
        vertices = prefix['visited'] + [obs.edges[s].target for s in candidate['edges'][:i]]
        for slot, edge in enumerate(obs.edges):
            if slot != selected and edge.source == vertices[-1] and edge.target not in vertices:
                planned.append((prefix['path'] + candidate['edges'][:i] + [slot], vertices + [edge.target], prefix['uses']))
    staged = set(known)
    unique = []
    for p, vertices, inherited in planned:
        if tuple(p) not in staged:
            staged.add(tuple(p))
            unique.append((p, vertices, inherited))
    if (len(frontier) - 1 + sum(v[-1] != obs.goal for _, v, _ in unique) > config.max_frontier
            or len(routes) + sum(v[-1] == obs.goal for _, v, _ in unique) > config.kernel.max_paths):
        return None, checks, 'frontier/route budget; no partial negative answer allowed'
    additions = [dict(node=dict(node_id='node:' + obs.digest[:20] + ':' + str(next_node + i),
                               semantic_id=v[-1], revision=obs.revision), path=p, visited=v, uses=deepcopy(u))
                 for i, (p, v, u) in enumerate(unique)]
    return (additions, staged), checks, None


def expected_learning(old, obs, decision, feedback, config):
    """현재 R0.2의 상태 전이식을 별도 dict 처리로 재계산한다."""
    new = deepcopy(old)
    changes = []
    compilation_items = 0
    if feedback['correct'] is False:
        for c in new['circuits']:
            cid = circuit_id(c)
            if cid in decision['circuit_ids']:
                before = c['strength']
                c['strength'] *= config.kernel.weakening
                c['failures'] += 1
                c['version'] += 1
                c['feedback_ids'].append(feedback['id'])
                if c['failures'] >= 3 and c['strength'] < .05:
                    c['active'] = False
                changes.append(dict(kind='weaken', circuit=cid, before_strength=before,
                                    after_strength=c['strength'], active=c['active']))
    elif feedback['correct'] is True and feedback['proof_valid'] and decision['value'] is True:
        # Positive primitive path의 depth는 직접 path primitive 개수다. reference가 별도로 검증한다.
        length = decision['proof']['primitive_depth']
        for size in config.pattern_lengths:
            if size > length:
                continue
            pattern = dict(roles=[dict(id='R' + str(i), kind='vertex') for i in range(size + 1)],
                relations=[dict(source_role='R' + str(i), target_role='R' + str(i + 1), kind='open_edge') for i in range(size)],
                entry_conditions=['injective_roles', 'contiguous_directed_path', 'current_revision', 'current_measurements'],
                output_role='R' + str(size), program=chain_program(size, [list(range(size))], config.kernel),
                kernel_signature=config.kernel.signature)
            cid = 'pattern-' + fingerprint(pattern)[:24]
            compilation_items += len(pattern['program']['groups']) + len(pattern['program']['links'])
            existing = next((c for c in new['circuits'] if circuit_id(c) == cid), None)
            if existing is not None:
                if obs.episode_id not in existing['evidence_episodes']:
                    existing['evidence_episodes'].append(obs.episode_id)
                    existing['feedback_ids'].append(feedback['id'])
                    existing['proof_digests'].append(fingerprint(decision['proof']))
                    before = existing['strength']
                    if decision['attempt'] == 1:
                        existing['strength'] += config.kernel.learning_rate * (1 - existing['strength'])
                        existing['active'] = True
                    existing['version'] += 1
                    changes.append(dict(kind='validated_after_reopen' if decision['attempt'] > 1 else 'reinforce',
                        circuit=cid, before_strength=before, after_strength=existing['strength']))
                continue
            pending = next((c for c in new['pending'] if circuit_id(c) == cid), None)
            if pending is None:
                if len(new['pending']) >= config.kernel.max_circuits:
                    changes.append(dict(kind='pending_capacity_reached', circuit=cid))
                    continue
                pending = dict(pattern=pattern, evidence_episodes=[], feedback_ids=[], proof_digests=[])
                new['pending'].append(pending)
            if obs.episode_id not in pending['evidence_episodes']:
                pending['evidence_episodes'].append(obs.episode_id)
                pending['feedback_ids'].append(feedback['id'])
                pending['proof_digests'].append(fingerprint(decision['proof']))
            changes.append(dict(kind='validated_subgraph', circuit=cid, distinct_episodes=len(pending['evidence_episodes'])))
            if len(pending['evidence_episodes']) >= config.kernel.min_valid_episodes:
                new['circuits'].append(dict(pending, strength=.55, version=1, failures=0, active=True))
                new['pending'].remove(pending)
                changes.append(dict(kind='compile_subgraph', circuit=cid, primitive_length=size))
    previous = new['version']
    new['version'] += 1
    new['consumed_feedback'].append(feedback['id'])
    patch = dict(previous_version=previous, version=new['version'], before_hash=fingerprint(old),
                 feedback_id=feedback['id'], decision_id=decision['id'], changes=changes)
    new['patches'].append(patch)
    cost = AdaptiveCost(compilation_items=compilation_items, learning_updates=1,
                        memory_write_items=len(changes) + 1, storage_bytes=len(codec.dumps(new).encode('utf-8')))
    return new, patch, cost
