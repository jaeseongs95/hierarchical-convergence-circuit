"""Native HCR execution with an explicit initial-state intervention.

No evaluator, world, scenario, result-based tuning, retry, or native monkey patch.
The preallocated-substrate/plasticity hypotheses are intentionally not implemented here.
"""
from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from .spec import treatment, FIXED_VALUE
from .storage import require, digest, canonical


def bridge_cost() -> dict:
    return dict(export_bytes=0, import_bytes=0, packet_hash_checks=0,
        dependency_checks=0, endpoint_checks=0, proof_ref_checks=0,
        source_descriptors_created=0, target_descriptor_lookups=0,
        matched_groups=0, selected_groups=0, source_state_values_read=0,
        initial_groups_written=0, support_checks=0,
        proof_nodes_created=0, proof_nodes_reused=0)


def export_state(source: dict, cost: dict) -> dict | None:
    if not source['accepted'] or source['raw_value'] is not True:
        return None
    a = source['observation']; proof = source['proof_graph']
    require(proof['final'] is not None and proof['under_assumptions_valid'], 'source has no valid proof')
    require(len(proof['paths']) == 1 and not proof.get('external_node_refs'),
            'EXP28 supports one positive non-nested source path')
    by_id = {e['id']: e for e in a['edges']}
    # Preserve the R046 ID-sorted proof assumption order; do not hide its cost effect.
    deps = [deepcopy(by_id[eid]) for eid, truth in proof['assumed_edges'] if truth]
    packet = dict(schema='hcr-exp28-state-packet-v1', origin_record_sha256=digest(source),
        episode_id=a['episode_id'], revision=a['revision'], config_sha256=digest(source['config']),
        start=a['start'], end=a['goal'], value=True, dependencies=deps,
        proof_ref=proof['final'], node_refs=[n['id'] for n in proof['nodes']],
        source_paths=deepcopy(proof['paths']), state=deepcopy(source['final_state']))
    packet['sha256'] = digest(packet)
    cost['export_bytes'] = len(canonical(packet))
    return packet


def import_guard(packet: dict | None, source: dict, obs: dict, cfg: dict, cost: dict):
    trace = []
    if packet is None:
        return False, 'no_adopted_positive_source', trace
    cost['import_bytes'] = len(canonical(packet)); cost['packet_hash_checks'] += 2
    require(packet['sha256'] == digest({k: v for k, v in packet.items() if k != 'sha256'}), 'packet checksum')
    require(packet['origin_record_sha256'] == digest(source), 'source provenance mismatch')
    require(set(packet) == {'schema', 'origin_record_sha256', 'episode_id', 'revision',
        'config_sha256', 'start', 'end', 'value', 'dependencies', 'proof_ref', 'node_refs',
        'source_paths', 'state', 'sha256'}, 'packet fields')
    require(packet['schema'] == 'hcr-exp28-state-packet-v1' and packet['value'] is True, 'packet schema/value')
    proof = source['proof_graph']
    require(packet['proof_ref'] == proof['final'] and packet['node_refs'] == [n['id'] for n in proof['nodes']],
            'source proof identity')
    cost['proof_ref_checks'] += 1 + len(packet['node_refs'])
    cost['endpoint_checks'] += 3
    if packet['config_sha256'] != digest(cfg): return False, 'config_changed', trace
    if packet['episode_id'] != obs['episode_id']: return False, 'episode_mismatch', trace
    if packet['start'] != obs['start']: return False, 'subject_mismatch', trace
    if obs['revision'] < packet['revision']: return False, 'revision_rollback', trace
    current = {e['id']: e for e in obs['edges']}
    for dep in packet['dependencies']:
        cost['dependency_checks'] += 1
        match = current.get(dep['id']) == dep
        trace.append(dict(edge_id=dep['id'], matches=match))
        if not match: return False, 'support_dependency_changed', trace
    return True, 'bound_and_dependencies_current', trace


def initialize(program, obs: dict, source: dict, packet: dict, arm: str, cost: dict):
    mode, mask = treatment(arm)
    require(mode in ('carry', 'fixed'), 'initializer requires a carry treatment')
    initial = {g.id: 0.5 for g in program.groups}
    old_obs = source['observation']; old_edges = old_obs['edges']; new_edges = obs['edges']
    descriptors = {}
    for i, e in enumerate(old_edges):
        descriptors[('edge', e['id'], e['source'], e['target'])] = f'e:{i}'
    for pi, path in enumerate(source['program']['paths']):
        for j in range(len(path)):
            descriptors[('prefix', old_obs['start'], tuple(old_edges[k]['id'] for k in path[:j+1]))] = f'p:{pi}:{j}'
    cost['source_descriptors_created'] += len(descriptors)
    choices = []
    for i, e in enumerate(new_edges):
        choices.append(('edge', ('edge', e['id'], e['source'], e['target']), f'e:{i}'))
    for pi, path in enumerate(program.paths):
        for j in range(len(path)):
            choices.append(('prefix', ('prefix', obs['start'], tuple(new_edges[k]['id'] for k in path[:j+1])), f'p:{pi}:{j}'))
    mapping = []
    for group_kind, descriptor, target in choices:
        cost['target_descriptor_lookups'] += 1
        old = descriptors.get(descriptor)
        if old is None: continue
        cost['matched_groups'] += 1
        if mask not in ('both', group_kind): continue
        cost['selected_groups'] += 1
        if mode == 'carry':
            value = packet['state'][old]
            cost['source_state_values_read'] += 1
        else:
            value = FIXED_VALUE
        require(type(value) in (int, float) and 0 <= value <= 1, 'initial value range')
        initial[target] = value; cost['initial_groups_written'] += 1
        mapping.append(dict(group_kind=group_kind, source_group=old, target_group=target,
                            value=value, value_origin='A_state' if mode == 'carry' else 'fixed_0.99'))
    require(initial['goal'] == 0.5, 'old goal cannot initialize the new goal')
    return initial, mapping


def namespaced(proof: dict, namespace: str) -> dict:
    out = deepcopy(proof)
    out['nodes'] = [dict(n, id=namespace+n['id'], parents=[namespace+p for p in n['parents']])
                    for n in proof['nodes']]
    out['final'] = None if proof['final'] is None else namespace+proof['final']
    out['external_node_refs'] = []
    return out


def supported(proof: dict, observation: dict, value, cost: dict) -> bool:
    if value is None or not proof['under_assumptions_valid'] or proof['final'] is None:
        return False
    edges = {e['id']: e for e in observation['edges']}
    for eid, truth in proof['assumed_edges']:
        cost['support_checks'] += 1
        require(eid in edges, 'proof names missing evidence')
        score = edges[eid]['score']
        if score is None or score == 0 or (score > 0) is not truth:
            return False
    return True


def run_query(observation: dict, config: dict, arm: str = 'cold', source: dict | None = None,
              event_sink=None) -> dict:
    from hcr.model import Config, Cost, Status, ExpansionLimit
    from hcr.codec import observation_from, plain
    from hcr.binding import Binding, Topology
    from hcr.workspace import discover_paths, make_program
    from hcr.dynamics import settle
    from hcr.proof import reconstruct

    treatment(arm)
    require(arm == 'cold' or source is not None, 'carry requires an A record')
    ob = deepcopy(observation); cf = deepcopy(config)
    obs = observation_from(ob); cfg = Config(**cf)
    cost = Cost(); bridge = bridge_cost(); events = []; started = perf_counter()
    def emit(name, data):
        event = dict(ordinal=len(events), event=name, payload=deepcopy(data))
        events.append(event)
        if event_sink is not None: event_sink(event)
    source_sha = None if source is None else digest(source)
    emit('begin', dict(observation_sha256=obs.digest, config_sha256=digest(cf), arm=arm,
                       source_sha256=source_sha))
    packet = None; valid = False; reason = 'not_requested'; check_trace = []
    if arm != 'cold':
        packet = export_state(source, bridge)
        valid, reason, check_trace = import_guard(packet, source, ob, cf, bridge)
    emit('carry_gate', dict(valid=valid, reason=reason, dependency_trace=check_trace,
        fallback_to_cold=arm != 'cold' and not valid, packet=packet))
    base = dict(schema='hcr-exp28-query-v1', observation=ob, config=cf, arm=arm,
        source_sha256=source_sha, carry_packet=packet, gate_valid=valid, gate_reason=reason,
        dependency_check_trace=check_trace, initial_stable_steps=0, old_goal_imported=False,
        native_adaptive_expansions=None, energy_joules=None, peak_memory_bytes=None)
    try:
        paths = discover_paths(Topology.from_observation(obs), cfg, cost)
        require(bool(paths), 'EXP28 scope requires a structural path; no path is not fabricated')
        program = make_program(len(obs.edges), paths, cfg, cost)
    except ExpansionLimit as exc:
        emit('budget_termination', dict(stage='graph_construction', message=str(exc)))
        n = cost.snapshot(); n['wall_seconds'] = None
        return dict(base, censored=True, termination='graph_budget', program=None,
            raw_drives=None, effective_drives=None, initial_state=None, transfer_map=[], ticks=[],
            convergence=None, final_state=None, raw_value=None, proof_graph=None, accepted=False,
            native_cost=n, bridge_cost=bridge, events=events, wall_seconds=perf_counter()-started)
    drives = {f'e:{i}': cfg.evidence_gain * (e.score or 0.0) for i, e in enumerate(obs.edges)}
    drives['goal'] = 0.0
    effective = {g.id: drives.get(g.id, 0.0) for g in program.groups}
    initial = {g.id: 0.5 for g in program.groups}; mapping = []
    if arm != 'cold' and valid:
        initial, mapping = initialize(program, ob, source, packet, arm, bridge)
    emit('network', dict(program=plain(program), raw_drives=drives, effective_drives=effective,
        initial=initial, transfer_map=mapping, initial_stable_steps=0, top_down=True))
    ticks = []
    def observe(i, state, residual, stable):
        row = dict(tick=i, state=deepcopy(state), residual=residual, stable_steps=stable)
        ticks.append(row); emit('tick', row)
    state, convergence = settle(program, drives, cfg, cost, initial=initial, observe=observe, top_down=True)
    value = state['goal'] >= 0.5 if convergence.status == Status.STABLE_DECISION else None
    emit('settled', dict(state=state, convergence=plain(convergence), raw_value=value))
    proof = namespaced(plain(reconstruct(obs, program,
        Binding(obs.digest, obs.revision, tuple(range(len(obs.edges)))), state, value, cost)),
        'q:'+obs.digest[:24]+':')
    bridge['proof_nodes_created'] = len(proof['nodes'])
    emit('proof_built', dict(proof=proof, native_nodes_reconstructed=cost.proof_nodes_reconstructed))
    accepted = supported(proof, ob, value, bridge)
    censored = convergence.status == Status.BUDGET_EXHAUSTED
    termination = 'kernel_budget' if censored else ('adopted_supported' if accepted else 'unsupported_or_unsettled')
    emit('adoption', dict(accepted=accepted, value=value, reason=termination))
    n = cost.snapshot(); n['wall_seconds'] = None  # Native Cost's default 0 is not a timing measurement.
    return dict(base, censored=censored, termination=termination, program=plain(program),
        raw_drives=drives, effective_drives=effective, initial_state=initial, transfer_map=mapping,
        ticks=ticks, convergence=plain(convergence), final_state=state, raw_value=value,
        proof_graph=proof, accepted=accepted, native_cost=n, bridge_cost=bridge,
        events=events, wall_seconds=perf_counter()-started)
