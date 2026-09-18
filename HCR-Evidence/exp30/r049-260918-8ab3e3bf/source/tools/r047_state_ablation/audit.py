"""Independent EXP28 auditor. No hcr/runtime imports; no calls into the producer.

Uses BFS for paths, a tanh form of the scalar equation, explicit term semantics for proof,
and independent edge/prefix matching. Every numerical tick and stopping rule is replayed.
"""
from __future__ import annotations
from collections import deque
from math import tanh, isclose, isfinite
from .storage import require, digest, canonical
from .spec import ARMS, FIXED_VALUE

TOL = 2e-12


def close(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float):
        return isfinite(a) and isfinite(b) and isclose(a, b, rel_tol=TOL, abs_tol=TOL)
    return type(a) is type(b) and a == b


class PathBudget(Exception):
    def __init__(self, count): self.count = count


def bfs(obs, cfg):
    work = deque([(obs['start'], (obs['start'],), [])]); paths = []; scans = 0
    while work:
        node, visited, path = work.popleft()
        if node == obs['goal']:
            paths.append(path)
            if len(paths) > cfg['max_paths']: raise PathBudget(scans)
            continue
        for slot, edge in enumerate(obs['edges']):
            scans += 1
            if scans > cfg['max_search']: raise PathBudget(scans)
            if edge['source'] == node and edge['target'] not in visited:
                if len(path) >= cfg['max_path_length']: raise PathBudget(scans)
                work.append((edge['target'], visited+(edge['target'],), path+[slot]))
    return paths, scans


def world_answer(obs, world):
    require(set(world) == {e['id'] for e in obs['edges']} and
            all(type(v) is bool for v in world.values()), 'world schema')
    reached = {obs['start']}
    while True:
        nxt = reached | {e['target'] for e in obs['edges'] if e['source'] in reached and world[e['id']]}
        if nxt == reached: return obs['goal'] in reached
        reached = nxt


def program_check(r):
    obs = r['observation']; cfg = r['config']; p = r['program']
    paths, scans = bfs(obs, cfg)
    require(p is not None and len(paths) == len(p['paths']) and
            {tuple(x) for x in paths} == {tuple(x) for x in p['paths']}, 'structural paths')
    groups = [dict(id=f'e:{i}', level=0, bias=0.0) for i in range(len(obs['edges']))]
    links = []
    for pi, path in enumerate(p['paths']):
        for j, slot in enumerate(path):
            name = f'p:{pi}:{j}'
            parents = [f'e:{slot}'] + ([] if j == 0 else [f'p:{pi}:{j-1}'])
            groups.append(dict(id=name, level=1, bias=-cfg['relation_gain']*(len(parents)-1)))
            for par in parents:
                links.extend([dict(source=par, target=name, weight=cfg['relation_gain'], kind='support'),
                              dict(source=name, target=par, weight=cfg['top_down_gain'], kind='top_down')])
    groups.append(dict(id='goal', level=1, bias=cfg['relation_gain']*(len(paths)-1)))
    for pi, path in enumerate(p['paths']):
        tail = f'p:{pi}:{len(path)-1}'
        links.extend([dict(source=tail, target='goal', weight=cfg['relation_gain'], kind='support'),
                      dict(source='goal', target=tail, weight=cfg['top_down_gain'], kind='top_down')])
    expected = dict(groups=groups, links=links, paths=p['paths'], edge_count=len(obs['edges']))
    require(close(p, expected), 'native program structure/bias/links changed')
    drive = {f'e:{i}': cfg['evidence_gain']*(e['score'] or 0.0) for i, e in enumerate(obs['edges'])}
    drive['goal'] = 0.0
    require(r['raw_drives'] == drive, 'raw drive mismatch')
    require(r['effective_drives'] == {g['id']: drive.get(g['id'], 0.0) for g in groups}, 'effective drive mismatch')
    n = r['native_cost']
    require(n['search_edge_checks'] == scans and n['dynamic_groups_created'] == len(groups)
            and n['dynamic_links_created'] == len(links), 'native construction cost')


def expected_packet(source):
    a = source['observation']; p = source['proof_graph']; by_id = {e['id']: e for e in a['edges']}
    out = dict(schema='hcr-exp28-state-packet-v1', origin_record_sha256=digest(source),
        episode_id=a['episode_id'], revision=a['revision'], config_sha256=digest(source['config']),
        start=a['start'], end=a['goal'], value=True,
        dependencies=[by_id[eid] for eid, v in p['assumed_edges'] if v],
        proof_ref=p['final'], node_refs=[n['id'] for n in p['nodes']],
        source_paths=p['paths'], state=source['final_state'])
    return dict(out, sha256=digest(out))


def guard_check(r, source):
    require(r['source_sha256'] == (None if source is None else digest(source)), 'source record provenance')
    c = r['bridge_cost']; p = r['carry_packet']; trace = []
    reason = 'not_requested'; valid = False
    packet_counts = dict(export_bytes=0, import_bytes=0, packet_hash_checks=0,
                         dependency_checks=0, endpoint_checks=0, proof_ref_checks=0)
    if r['arm'] == 'cold':
        require(p is None, 'cold imported packet')
    else:
        require(source is not None, 'missing A record')
        if not source['accepted'] or source['raw_value'] is not True:
            require(p is None, 'nonadopted source exported')
            reason = 'no_adopted_positive_source'
        else:
            expected = expected_packet(source)
            require(p == expected, 'packet content/state/proof/dependencies changed')
            packet_counts.update(export_bytes=len(canonical(expected)), import_bytes=len(canonical(expected)),
                packet_hash_checks=2, endpoint_checks=3, proof_ref_checks=1+len(expected['node_refs']))
            a = source['observation']; b = r['observation']
            if source['config'] != r['config']: reason = 'config_changed'
            elif a['episode_id'] != b['episode_id']: reason = 'episode_mismatch'
            elif a['start'] != b['start']: reason = 'subject_mismatch'
            elif b['revision'] < a['revision']: reason = 'revision_rollback'
            else:
                reason = 'bound_and_dependencies_current'
                by_id = {e['id']: e for e in b['edges']}
                for dep in expected['dependencies']:
                    eq = by_id.get(dep['id']) == dep
                    trace.append(dict(edge_id=dep['id'], matches=eq))
                    if not eq:
                        reason = 'support_dependency_changed'; break
                packet_counts['dependency_checks'] = len(trace)
            valid = reason == 'bound_and_dependencies_current'
    require(r['gate_valid'] is valid and r['gate_reason'] == reason, 'guard decision')
    require(r['dependency_check_trace'] == trace, 'dependency scan order')
    require(all(c[k] == v for k, v in packet_counts.items()), 'guard operation counts')
    return valid


def initial_check(r, source, valid):
    require(r['initial_stable_steps'] == 0 and r['old_goal_imported'] is False, 'history/goal transfer')
    wanted = {g['id']: 0.5 for g in r['program']['groups']}; mapped = []
    counts = dict(source_descriptors_created=0, target_descriptor_lookups=0,
                  matched_groups=0, selected_groups=0, source_state_values_read=0, initial_groups_written=0)
    if r['arm'] != 'cold' and valid:
        mode, mask = r['arm'].split('_')
        a = source['observation']; b = r['observation']; old = a['edges']; new = b['edges']
        counts['source_descriptors_created'] = len(old)+sum(len(p) for p in source['program']['paths'])
        # Match by current edge identity + endpoints, not the group slot string.
        pairs = []
        for i, e in enumerate(new):
            counts['target_descriptor_lookups'] += 1
            for j, f in enumerate(old):
                if (e['id'], e['source'], e['target']) == (f['id'], f['source'], f['target']):
                    pairs.append(('edge', f'e:{j}', f'e:{i}')); break
        for pi, path in enumerate(r['program']['paths']):
            for j in range(len(path)):
                counts['target_descriptor_lookups'] += 1
                ids = [new[k]['id'] for k in path[:j+1]]
                for ai, ap in enumerate(source['program']['paths']):
                    if a['start'] == b['start'] and j < len(ap) and ids == [old[k]['id'] for k in ap[:j+1]]:
                        pairs.append(('prefix', f'p:{ai}:{j}', f'p:{pi}:{j}')); break
        counts['matched_groups'] = len(pairs)
        for kind, oldkey, newkey in pairs:
            if mask != 'both' and mask != kind: continue
            value = source['final_state'][oldkey] if mode == 'carry' else FIXED_VALUE
            mapped.append(dict(group_kind=kind, source_group=oldkey, target_group=newkey,
                value=value, value_origin='A_state' if mode == 'carry' else 'fixed_0.99'))
            wanted[newkey] = value
        counts['selected_groups'] = counts['initial_groups_written'] = len(mapped)
        counts['source_state_values_read'] = len(mapped) if mode == 'carry' else 0
    require(r['initial_state'] == wanted and r['transfer_map'] == mapped, 'mask/value/binding intervention mismatch')
    require(wanted['goal'] == 0.5, 'new goal initialized from an old answer')
    require(all(r['bridge_cost'][k] == v for k, v in counts.items()), 'initialization cost')


def scalar_check(r):
    cfg = r['config']; p = r['program']; state = dict(r['initial_state'])
    require(set(state) == {g['id'] for g in p['groups']} and
        all(type(v) in (int, float) and isfinite(v) and 0 <= v <= 1 for v in state.values()), 'initial range/identity')
    stable = 0; history = []; terminal = None; residual = 1.0; margin = 0.0; max_error = 0.0
    require(bool(r['ticks']), 'missing numeric trajectory')
    for number, row in enumerate(r['ticks'], 1):
        require(terminal is None and row['tick'] == number, 'tick order or continuation after stopping')
        nxt = {}
        for g in p['groups']:
            k = g['id']
            incoming = [e['weight']*(2*state[e['source']]-1) for e in p['links'] if e['target'] == k]
            drive = g['bias'] + r['raw_drives'].get(k, 0.0)
            for v in incoming: drive += v
            half_logit = (drive + 0.5*(cfg['self_excitation']+cfg['inhibition'])*(2*state[k]-1))/cfg['temperature']
            target = 0.5 + 0.5*tanh(half_logit)
            nxt[k] = (1-cfg['damping'])*state[k] + cfg['damping']*target
        residual = max(abs(nxt[k]-state[k]) for k in state)
        stable = stable+1 if residual <= cfg['residual_tolerance'] else 0
        require(close(row['state'], nxt) and close(row['residual'], residual) and row['stable_steps'] == stable,
                'independent scalar replay mismatch at tick '+str(number))
        max_error = max(max_error, max(abs(row['state'][k]-nxt[k]) for k in state))
        margin = abs(2*nxt['goal']-1)
        if stable >= cfg['patience']:
            terminal = 'stable_decision' if margin >= cfg['margin_threshold'] else 'stable_ambiguous'
        elif history and residual > cfg['residual_tolerance']*10 and max(abs(nxt[k]-history[-1][k]) for k in nxt) < cfg['residual_tolerance']:
            terminal = 'oscillating'
        elif number == cfg['max_ticks']:
            terminal = 'budget_exhausted'
        history.append(state); history = history[-3:]; state = nxt
    require(terminal is not None and close(r['final_state'], state), 'missing final state or terminal')
    require(close(r['convergence'], dict(status=terminal, ticks=len(r['ticks']), residual=residual,
        margin=margin, stable_steps=stable)), 'convergence annotation')
    value = state['goal'] >= 0.5 if terminal == 'stable_decision' else None
    require(r['raw_value'] is value and r['censored'] is (terminal == 'budget_exhausted'), 'readout/budget classification')
    n = r['native_cost']; nt = len(r['ticks'])
    for k, v in dict(kernel_ticks=nt, group_updates=nt*len(state), normalization_ops=nt*len(state),
                     signal_transmissions=nt*len(p['links'])).items():
        require(n[k] == v, 'native numeric counter: ' + k)
    return max_error


def proof_check(r):
    proof = r['proof_graph']; ob = r['observation']; state = r['final_state']; value = r['raw_value']
    require(proof is not None and not proof.get('external_node_refs'), 'EXP28 cannot reuse foreign proof nodes')
    edges = {e['id']: (i, e) for i, e in enumerate(ob['edges'])}
    nodes = proof['nodes']; table = {n['id']: n for n in nodes}
    require(len(nodes) == len(table), 'duplicate proof identity')
    terms = {}; depths = {}; assumed = {}; visited = set()
    def visit(key):
        require(key in table and key not in visited, 'missing parent/cycle')
        if key in terms: return terms[key]
        visited.add(key); n = table[key]; rule = n['rule']
        parents = [visit(x) for x in n['parents']]
        depth = 0 if not parents else 1+max(depths[x] for x in n['parents'])
        if rule in ('assumed_open', 'assumed_closed'):
            require(not parents and n['edge_id'] in edges, 'fact proof contract')
            slot, edge = edges[n['edge_id']]; truth = rule == 'assumed_open'
            require((state[f'e:{slot}'] >= 0.5) is truth, 'proof fact not in native state')
            assumed[edge['id']] = truth
            term = ('edge', edge['source'], edge['target'], truth, edge['id'])
        elif rule == 'start_edge':
            require(len(parents) == 1 and parents[0][0] == 'edge' and parents[0][3] is True,
                    'start-edge inference')
            e = parents[0]; require(e[1] == ob['start'], 'wrong start referent')
            term = ('reachable', e[1], e[2])
        elif rule == 'extend_path':
            require(len(parents) == 2 and parents[0][0] == 'reachable' and parents[1][0] == 'edge'
                    and parents[1][3] is True and parents[0][2] == parents[1][1], 'relation composition binding')
            term = ('reachable', parents[0][1], parents[1][2])
        elif rule == 'path_blocked':
            pi = n['path_index']
            require(type(pi) is int and 0 <= pi < len(r['program']['paths']) and len(parents) == 1,
                    'blocked-path reference')
            e = parents[0]; require(e[0] == 'edge' and e[3] is False, 'negative path support')
            require(e[4] in [ob['edges'][s]['id'] for s in r['program']['paths'][pi]], 'cut outside path')
            term = ('blocked', pi)
        elif rule == 'all_paths_blocked':
            require(len(parents) == len(r['program']['paths']) and
                set(parents) == {('blocked', i) for i in range(len(r['program']['paths']))}, 'incomplete negative proof')
            term = ('unreachable', ob['start'], ob['goal'])
        else:
            raise ValueError('unknown proof rule: ' + rule)
        visited.remove(key); terms[key] = term; depths[key] = depth
        return term
    final = proof['final']
    if final is None:
        # Unsupported or unsettled is a legitimate measured outcome, not an audit pass for an invalid proof.
        require(not proof['under_assumptions_valid'] and proof['primitive_depth'] is None, 'invalid empty proof annotation')
        for n in nodes: visit(n['id'])
        dd = None
    else:
        term = visit(final)
        expected = ('reachable' if value is True else 'unreachable', ob['start'], ob['goal'])
        require(value is not None and term == expected and proof['under_assumptions_valid'], 'final proof semantics')
        require(len(terms) == len(nodes), 'unreferenced proof nodes')
        dd = depths[final]; require(proof['primitive_depth'] == dd, 'D_DAG mismatch')
    require(proof['assumed_edges'] == sorted([[k, v] for k, v in assumed.items()]), 'assumption registry')
    if value is not None:
        require(proof['paths'] == [[ob['edges'][s]['id'] for s in path] for path in r['program']['paths']], 'proof path registry')
    accepted = final is not None and value is not None and proof['under_assumptions_valid']
    checks = 0
    if accepted:
        for eid, truth in proof['assumed_edges']:
            checks += 1; score = edges[eid][1]['score']
            if score is None or score == 0 or (score > 0) is not truth:
                accepted = False; break
    require(r['accepted'] is bool(accepted), 'terminal adoption changed')
    require(r['bridge_cost']['support_checks'] == checks, 'support-check cost')
    require(r['native_cost']['proof_nodes_reconstructed'] == len(nodes) == r['bridge_cost']['proof_nodes_created'],
            'proof construction count')
    require(r['bridge_cost']['proof_nodes_reused'] == 0, 'unexpected proof reuse')
    termination = 'kernel_budget' if r['censored'] else ('adopted_supported' if accepted else 'unsupported_or_unsettled')
    require(r['termination'] == termination, 'terminal reason')
    return dd


def events_check(r):
    ev = r['events']
    require([e['ordinal'] for e in ev] == list(range(len(ev))), 'event ordinal')
    expected_names = ['begin', 'carry_gate', 'network'] + ['tick']*len(r['ticks']) + ['settled', 'proof_built', 'adoption']
    require([e['event'] for e in ev] == expected_names, 'event ordering/extra inference')
    require(ev[0]['payload'] == dict(observation_sha256=digest(r['observation']), config_sha256=digest(r['config']),
            arm=r['arm'], source_sha256=r['source_sha256']), 'begin event')
    require(ev[1]['payload'] == dict(valid=r['gate_valid'], reason=r['gate_reason'],
            dependency_trace=r['dependency_check_trace'], fallback_to_cold=r['arm'] != 'cold' and not r['gate_valid'],
            packet=r['carry_packet']), 'gate event')
    require(ev[2]['payload'] == dict(program=r['program'], raw_drives=r['raw_drives'],
            effective_drives=r['effective_drives'], initial=r['initial_state'], transfer_map=r['transfer_map'],
            initial_stable_steps=0, top_down=True), 'network event')
    require([e['payload'] for e in ev[3:3+len(r['ticks'])]] == r['ticks'], 'tick stream differs from record')
    require(ev[-3]['payload'] == dict(state=r['final_state'], convergence=r['convergence'], raw_value=r['raw_value']), 'settled event')
    require(ev[-2]['payload'] == dict(proof=r['proof_graph'], native_nodes_reconstructed=r['native_cost']['proof_nodes_reconstructed']), 'proof event')
    require(ev[-1]['payload'] == dict(accepted=r['accepted'], value=r['raw_value'], reason=r['termination']), 'adoption event')


def audit_record(r, source=None, world=None):
    fields = {'schema','observation','config','arm','source_sha256','carry_packet','gate_valid','gate_reason',
        'dependency_check_trace','initial_stable_steps','old_goal_imported','native_adaptive_expansions',
        'energy_joules','peak_memory_bytes','censored','termination','program','raw_drives','effective_drives',
        'initial_state','transfer_map','ticks','convergence','final_state','raw_value','proof_graph','accepted',
        'native_cost','bridge_cost','events','wall_seconds'}
    require(set(r) == fields and r['schema'] == 'hcr-exp28-query-v1' and r['arm'] in ARMS, 'record schema/arm')
    native_fields = {'search_edge_checks','dynamic_groups_created','dynamic_links_created','binding_checks',
        'recall_checks','circuit_groups_instantiated','kernel_ticks','group_updates','signal_transmissions',
        'normalization_ops','proof_nodes_reconstructed','compilation_items','memory_write_items',
        'observation_requests','verification_checks','wall_seconds'}
    bridge_fields = {'export_bytes','import_bytes','packet_hash_checks','dependency_checks','endpoint_checks',
        'proof_ref_checks','source_descriptors_created','target_descriptor_lookups','matched_groups',
        'selected_groups','source_state_values_read','initial_groups_written','support_checks',
        'proof_nodes_created','proof_nodes_reused'}
    require(set(r['native_cost']) == native_fields and set(r['bridge_cost']) == bridge_fields, 'cost schema')
    require(all(type(v) is int and v >= 0 for k,v in r['native_cost'].items() if k != 'wall_seconds') and
            all(type(v) is int and v >= 0 for v in r['bridge_cost'].values()), 'cost type/range')
    require(type(r['accepted']) is bool and type(r['censored']) is bool and type(r['gate_valid']) is bool,
            'decision flags must be Boolean')
    require(type(r['initial_stable_steps']) is int and r['initial_stable_steps'] == 0 and r['old_goal_imported'] is False,
            'initial history/old goal contract')
    require(r['energy_joules'] is None and r['peak_memory_bytes'] is None and r['native_adaptive_expansions'] is None,
            'unmeasured quantity reported as a measurement')
    require(r['native_cost']['wall_seconds'] is None, 'native default time is not a measured time')
    require(type(r['wall_seconds']) in (int, float) and isfinite(r['wall_seconds']) and r['wall_seconds'] >= 0, 'wall time')
    valid = guard_check(r, source)
    if r['program'] is None:
        # Budget termination is preserved and audited, never repaired into an outcome.
        exhausted = False; scans = None
        try:
            paths, scans = bfs(r['observation'], r['config'])
            groups = len(r['observation']['edges'])+sum(map(len, paths))+1
            exhausted = groups > r['config']['max_groups']
        except PathBudget as e:
            exhausted = True; scans = e.count
        require(exhausted and r['termination'] == 'graph_budget' and r['censored'] and not r['accepted']
                and r['raw_value'] is None and not r['ticks'] and r['proof_graph'] is None, 'unjustified graph termination')
        require(r['native_cost']['search_edge_checks'] == scans and r['native_cost']['kernel_ticks'] == 0, 'budget counters')
        require([e['event'] for e in r['events']] == ['begin', 'carry_gate', 'budget_termination'], 'budget event chain')
        return dict(verified=True, D_DAG=None, classification='budget_termination', scalar_ticks=0, max_scalar_error=0.0)
    program_check(r); initial_check(r, source, valid)
    error = scalar_check(r); dd = proof_check(r); events_check(r)
    n = r['native_cost']
    for k in ('binding_checks', 'recall_checks', 'circuit_groups_instantiated', 'compilation_items',
              'memory_write_items', 'observation_requests', 'verification_checks'):
        require(n[k] == 0, 'unexpected native mechanism: ' + k)
    truth = None if world is None else world_answer(r['observation'], world)
    classification = ('budget_termination' if r['censored'] else
        'unsettled' if r['raw_value'] is None else
        'unsupported' if not r['accepted'] else
        'not_evaluated' if world is None else
        'correct' if r['raw_value'] is truth else 'logical_failure')
    return dict(verified=True, D_DAG=dd, classification=classification,
        oracle_value=truth, scalar_ticks=len(r['ticks']), max_scalar_error=error)
