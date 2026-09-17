"""R0.2.1 snapshot의 독립 상태·generation·수치 검산.

기존 R0.2 audit의 event 해석을 재사용한 별도 session 계약이다.
runtime/state/sessions/expansion/dynamics/learning의 실행 함수를 호출하지 않는다.
원래 seed memory의 사실성과 feedback의 외부 정답성은 이 검산의 주장이 아니다.
"""
from __future__ import annotations
from copy import deepcopy
from collections import Counter
from math import isfinite
from .. import codec
from ..model import AdaptiveCost, ContractError, Feedback, fingerprint
from ..circuits import AdaptiveMemory
from ..trace import check_chain
from .reference import validate_proof
from .audit import require, independent_step
from .adaptive_audit_support import scan_patterns, pool_network, decision_network, plan_expansion, expected_learning


def _pending(s, networks, config, seconds):
    n = networks.get(s['last_network'])
    cv = dict(status='no_candidate', ticks=0, residual=0.0, margin=0.0, stable_steps=0)
    state, program, value = {}, None, None
    if n is not None:
        require(n['settled'], 'checkpoint inside an unfinished kernel')
        program, state, cv = n['payload']['program'], n['state'], dict(n['convergence'])
        if cv['status'] == 'stable_decision':
            value = state['goal'] >= .5
            if value is False and s['frontier']:
                value = None
        unsupported = (not any(u['prior'] != 0 for r in s['routes'] for u in r['uses'])
                       and all(e.score is None or e.score == 0 for e in s['obs'].edges))
        if unsupported:
            value = None
            if cv['status'] == 'stable_decision':
                cv['status'] = 'unsupported'
    if s['failed']:
        value, cv['status'] = None, 'budget_exhausted'
    p, flags = s['payload'], s['engine']
    return dict(observation=codec.plain(s['obs']), mode=p['mode'], revision_of=p['revision_of'],
        attempt=p['attempt'], decision_id=p['decision_id'], memory_hash=p['memory_hash'],
        memory_version=p['memory_version'], config_signature=config.signature,
        switches=[flags[k] for k in ('use_circuits', 'top_down', 'allow_reexpansion')],
        cost=s['cost'].snapshot(), workspace=dict(frontier=s['frontier'], routes=s['routes'],
            known=[list(p) for p in sorted(s['known'])], next_node=s['next_node']),
        mismatch=s['mismatch'], program=program, state=state, convergence=cv, value=value,
        network_id=s['last_network'], settled_paths=program['paths'] if program else [],
        failure_reason=s['failed'], ready=bool(s['failed'] or not s['frontier'] or value is not None),
        active_seconds=seconds)


def verify_document(document):
    try:
        return _verify_document(document)
    except ContractError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        raise ContractError('malformed R0.2.1 checkpoint: ' + str(exc)) from exc


def _verify_document(document):
    require(set(document) == {'session_id', 'source_hashes', 'engine', 'events', 'transitions'}, 'session document fields')
    require(isinstance(document['session_id'], str) and 0 < len(document['session_id']) <= 128, 'session identity')
    core, events, journal = document['engine'], document['events'], document['transitions']
    require(isinstance(events, list) and 0 < len(events) <= 100000 and isinstance(journal, list)
            and 0 < len(journal) <= 10000, 'session event/generation budget')
    check_chain(events, len(events), events[-1]['sha256'])
    require(set(core) == {'config','memory','switches','attempts','held','feedback','requests','pending'}, 'engine state fields')
    config = codec.adaptive_config_from(core['config'])
    starts, decisions, networks, feedbacks, requests, attempts = {}, {}, {}, {}, {}, {}
    known_memory = set()
    memory = engine = pending_feedback = active_did = None
    steps = updates = scans_verified = graph_steps = 0
    learning_costs = Counter()
    offset = 0
    previous_transition = '0' * 64
    previous_core = None
    current_core = None
    for generation, transition in enumerate(journal):
        require(set(transition) == {'generation','session_id','operation','arguments','event_start','event_end',
            'previous','before_state','after_state','active_seconds','sha256'}, 'transition fields')
        tb = {k:v for k,v in transition.items() if k != 'sha256'}
        require(type(transition['generation']) is int and transition['generation'] == generation
                and transition['session_id'] == document['session_id']
                and transition['previous'] == previous_transition and fingerprint(tb) == transition['sha256'],
                'generation lineage mismatch')
        end = transition['event_end']
        require(type(end) is int and type(transition['event_start']) is int
                and transition['event_start'] == offset and offset <= end <= len(events), 'event boundary')
        require(transition['before_state'] == previous_core, 'broken state lineage')
        op, args = transition['operation'], transition['arguments']
        segment = events[offset:end]
        names = [e['event'] for e in segment]
        if op == 'init':
            require(generation == 0 and names == ['r02_engine_created'] and args == {}, 'initial generation')
        else:
            require(generation > 0, 'missing initial generation')
            pending = current_core['pending']
            if op == 'begin':
                require(pending is None and names == ['r02_attempt_started','r02_workspace_created'], 'begin boundary')
                p = segment[0]['payload']
                require(args == dict(observation_digest=fingerprint(p['observation']), mode=p['mode'], revision_of=p['revision_of']),
                        'begin arguments')
            elif op == 'advance':
                require(pending is not None and pending['ready'] is False and args == {}, 'advance phase')
                require(sum(n in ('r02_expansion','r02_dead_end') for n in names) <= 1
                        and names.count('r02_expansion_exhausted') <= 1
                        and any(n in ('r02_expansion','r02_dead_end','r02_expansion_exhausted') for n in names)
                        and not set(names) & {'r02_engine_created','r02_attempt_started','r02_decision','r02_feedback','r02_memory_updated','r02_observation_requested'},
                        'one dependency step per generation')
            elif op == 'finish':
                require(pending is not None and pending['ready'] is True and names == ['r02_decision'] and args == {}, 'finish phase')
            elif op == 'feedback':
                require(pending is None and names == ['r02_feedback','r02_memory_updated']
                        and args == dict(feedback_digest=fingerprint(segment[0]['payload'])), 'feedback phase')
            elif op == 'request_revision':
                require(pending is None and set(args) == {'decision_id'} and names in ([], ['r02_observation_requested']), 'request phase')
                target = args['decision_id']
                require(target in feedbacks and feedbacks[target]['correct'] is False, 'request without error')
                d, obs = decisions[target], starts[target]['obs']
                eligible = (d['mode'] == 'adapt' and engine['allow_reexpansion']
                            and d['attempt'] <= config.kernel.max_observation_requests
                            and any(e.score is None or abs(e.score) < .9 for e in obs.edges))
                require(bool(names) == bool(eligible), 'request availability')
                if names:
                    require(segment[0]['payload']['decision_id'] == target, 'request target')
            else:
                raise ContractError('unknown generation operation ' + str(op))
        for event in segment:
            name, p = event['event'], event['payload']
            did = p.get('decision_id')
            if name == 'r02_engine_created':
                require(engine is None and pending_feedback is None, 'duplicate engine initialization')
                require(p['config'] == codec.plain(config) and p['config_signature'] == config.signature, 'engine config')
                require(all(type(p[k]) is bool for k in ('use_circuits', 'top_down', 'allow_reexpansion')), 'engine flag types')
                loaded = AdaptiveMemory.from_document(p['memory_document'], config)
                require(loaded.digest == p['memory_hash'], 'unproven initial memory')
                memory = loaded.document()
                engine = deepcopy(p)
                attempts = {}
            elif name == 'r02_attempt_started':
                require(engine is not None and active_did is None and did not in starts and pending_feedback is None, 'attempt ordering')
                obs = codec.observation_from(p['observation'])
                require(len(obs.edges) <= config.kernel.max_edges, 'input edge budget')
                require(p['mode'] in ('train', 'frozen_eval', 'adapt'), 'mode contract')
                require(p['memory_hash'] == fingerprint(memory) and p['memory_version'] == memory['version'], 'memory changed during inference')
                previous = p['revision_of']
                if previous is not None:
                    require(previous in requests and p['mode'] == 'adapt', 'unauthorized revision')
                    request, prior = requests[previous], starts[previous]['obs']
                    require(obs.episode_id == request['episode_id'] and obs.revision == request['revision']
                            and obs.revision > prior.revision and (obs.start, obs.goal) == (prior.start, prior.goal)
                            and [(e.id, e.source, e.target) for e in obs.edges] == [(e.id, e.source, e.target) for e in prior.edges],
                            'revision identity/topology')
                    require(all(a.score == b.score or a.id in request['edge_ids'] for a, b in zip(prior.edges, obs.edges)),
                            'unrequested observation change')
                    del requests[previous]
                else:
                    require(obs.episode_id not in attempts, 'episode repetition without revision')
                require(did == 'r02-d-' + str(event['seq']) + '-' + obs.digest[:16], 'decision ID continuity')
                active_did = did
                number = attempts.get(obs.episode_id, 0) + 1
                attempts[obs.episode_id] = number
                require(p['attempt'] == number, 'attempt count')
                starts[did] = dict(payload=p, obs=obs, memory=deepcopy(memory), engine=deepcopy(engine),
                    cost=AdaptiveCost(observation_requests=int(previous is not None)), frontier=None, routes=[], known=set(),
                    next_node=1, scan=None, pool_activations=[], proposals=None, last_network=None, failed=None,
                    mismatch=dict(kind='feedback_reopen' if previous is not None else 'new_input', magnitude=float(previous is not None), detail=''))
            elif name == 'r02_workspace_created':
                s = starts[did]
                obs = s['obs']
                initial = dict(node=dict(node_id='node:' + obs.digest[:20] + ':0', semantic_id=obs.start, revision=obs.revision),
                               path=[], visited=[obs.start], uses=[])
                require(s['frontier'] is None and p['initial'] == initial, 'initial node/semantic identity')
                s['frontier'], s['known'] = [initial], {()}
                s['cost'].graph_nodes_created += 1
            elif name == 'r02_binding_scan':
                s = starts[did]
                require(s['engine']['use_circuits'] and s['payload']['revision_of'] is None, 'disabled circuit scan')
                require(p['prefix'] == s['frontier'][0], 'scan frontier binding')
                expected = scan_patterns(s['obs'], p['prefix'], s['memory'], config,
                                        max(0, config.max_binding_checks - s['cost'].binding_operations))
                require({k: p[k] for k in expected} == expected, 'independent pattern enumeration/budget')
                s['scan'] = expected
                s['pool_activations'] = []
                s['cost'].recall_checks += len(expected['inspected'])
                s['cost'].binding_operations += len(expected['scans'])
                s['cost'].binding_checks += len(expected['scans'])
                s['cost'].candidate_circuits += len(expected['matched'])
                scans_verified += len(expected['scans'])
            elif name == 'r02_pool_unavailable':
                s = starts[did]
                require(s['scan'] and s['scan']['complete'] and s['scan']['matched'], 'pool unavailable without candidates')
                program, _, _, _ = pool_network(s['obs'], s['scan']['matched'], s['memory'], config)
                require(len(program['groups']) > config.kernel.max_groups and p['reason'] == 'common_kernel_group_budget', 'false pool exhaustion')
            elif name == 'r02_network':
                s, obs = starts[did], starts[did]['obs']
                nid = p['network_id']
                require(nid not in networks and nid == 'network-' + str(event['seq']), 'network identity')
                require(p['top_down'] is s['engine']['top_down'], 'top-down ablation')
                if p['kind'] == 'pool':
                    require(s['scan'] and s['scan']['complete'] and s['scan']['matched'], 'partial pool masquerades as complete')
                    expected, drives, meta, instantiated = pool_network(obs, s['scan']['matched'], s['memory'], config)
                    require(p['metadata'] == dict(prefix=s['frontier'][0], candidates=meta), 'pool prior/version/binding')
                    s['cost'].dynamic_groups_created += len(obs.edges) + 1
                    n = len(meta)
                    s['cost'].dynamic_links_created += 2 * n + n * (n - 1)
                    s['cost'].circuit_groups_instantiated += instantiated
                    s['cost'].pool_calls += 1
                elif p['kind'] == 'decision':
                    require(bool(s['routes']), 'goal network before a goal route')
                    expected, drives = decision_network(obs, s['routes'], config)
                    require(p['metadata'] == dict(routes=s['routes'], graph_complete=not s['frontier']), 'decision network routes')
                    s['cost'].dynamic_groups_created += len(expected['groups'])
                    s['cost'].dynamic_links_created += len(expected['links'])
                    s['last_network'] = nid
                else:
                    raise ContractError('audit: unknown R0.2 network kind')
                require(len(expected['groups']) <= config.kernel.max_groups and len(expected['paths']) <= config.kernel.max_paths,
                        'common kernel size limit')
                require(p['program'] == expected and p['program_digest'] == fingerprint(expected), 'independent signal grammar')
                require(p['drives'] == drives, 'signal drive from unauthorized data')
                networks[nid] = dict(payload=p, state={g['id']: .5 for g in expected['groups']}, ticks=0,
                                      stable=0, residual=1.0, history=[], oscillating=False, settled=False, terminal=False)
            elif name == 'r02_tick':
                n = networks[p['network_id']]
                s = starts[did]
                require(n['payload']['decision_id'] == did and not n['settled'] and not n['terminal'], 'tick sequencing')
                actual_state = independent_step(n['payload']['program'], n['state'], n['payload']['drives'], config.kernel, n['payload']['top_down'])
                require(set(actual_state) == set(p['state']) and all(isfinite(v) and abs(v - actual_state[k]) < 2e-12 for k, v in p['state'].items()),
                        'independent recurrence mismatch')
                residual = max(abs(actual_state[k] - n['state'][k]) for k in actual_state)
                stable = n['stable'] + 1 if residual <= config.kernel.residual_tolerance else 0
                require(p['tick'] == n['ticks'] + 1 and p['tick'] <= config.kernel.max_ticks,
                        'tick count/budget')
                require(abs(p['residual'] - residual) < 2e-12 and p['stable_steps'] == stable, 'residual/stable persistence')
                n['oscillating'] = bool(n['history'] and residual > config.kernel.residual_tolerance * 10
                    and max(abs(actual_state[k] - n['history'][-1][k]) for k in actual_state) < config.kernel.residual_tolerance)
                n['history'] = (n['history'] + [n['state']])[-3:]
                # 입력된 실제 trace 값을 다음 독립 step의 상태로 쓴다. 오차 허용을 누적 왜곡에 쓰지 않는다.
                n['state'], n['ticks'], n['stable'], n['residual'] = dict(p['state']), p['tick'], stable, p['residual']
                n['terminal'] = stable >= config.kernel.patience or n['oscillating'] or n['ticks'] == config.kernel.max_ticks
                s['cost'].kernel_ticks += 1
                s['cost'].group_updates += len(actual_state)
                s['cost'].normalization_ops += len(actual_state)
                s['cost'].signal_transmissions += sum(n['payload']['top_down'] or e['kind'] != 'top_down' for e in n['payload']['program']['links'])
                steps += 1
            elif name == 'r02_settled':
                n = networks[p['network_id']]
                require(n['payload']['decision_id'] == did and n['terminal'] and not n['settled'], 'premature/duplicate settle')
                require(p['state'] == n['state'], 'settled state overwritten')
                margin = abs(2 * n['state']['goal'] - 1)
                if n['stable'] >= config.kernel.patience:
                    state = 'stable_decision' if margin >= config.kernel.margin_threshold else 'stable_ambiguous'
                elif n['oscillating']:
                    state = 'oscillating'
                else:
                    state = 'budget_exhausted'
                expected = dict(status=state, ticks=n['ticks'], residual=n['residual'], margin=margin, stable_steps=n['stable'])
                require(p['convergence'] == expected, 'convergence classification')
                n['settled'], n['convergence'] = True, expected
            elif name == 'r02_pool_result':
                s, n = starts[did], networks[p['network_id']]
                require(n['settled'] and n['payload']['kind'] == 'pool', 'pool readout before settle')
                stable = n['convergence']['status'] in ('stable_decision', 'stable_ambiguous')
                result = []
                for i, candidate in enumerate(n['payload']['metadata']['candidates']):
                    value = n['state']['c:' + str(i)]
                    result.append(dict(circuit_id=candidate['circuit_id'], binding=candidate['binding'], activation=value,
                        mismatch=candidate['mismatch'], prior=candidate['prior'], circuit_version=candidate['circuit_version'],
                        eligible=stable and value >= config.activation_threshold and candidate['mismatch'] <= config.mismatch_threshold))
                require(p['activations'] == result, 'circuit selection was not a common-kernel readout')
                s['pool_activations'] = result
            elif name == 'r02_proposals':
                s, obs = starts[did], starts[did]['obs']
                require(s['cost'].expansions < config.max_expansions, 'proposal after expansion budget')
                require(p['prefix'] == s['frontier'][0] and p['mismatch'] == s['mismatch'], 'proposal current workspace/mismatch')
                enabled = s['engine']['use_circuits'] and s['payload']['revision_of'] is None
                require(p['circuits_enabled'] is enabled, 'forced reopen reused circuits')
                primitive = [i for i, edge in enumerate(obs.edges) if edge.source == p['prefix']['visited'][-1] and edge.target not in p['prefix']['visited']]
                require(p['primitive_slots'] == primitive, 'primitive proposal omitted a dependency')
                activations = s['pool_activations'] if enabled and primitive else []
                cs = [dict(edges=a['binding']['edge_order'], source='circuit', activation=a['activation'], mismatch=a['mismatch'],
                           circuit_id=a['circuit_id'], binding=a['binding'], prior=a['prior'], circuit_version=a['circuit_version'])
                      for a in activations if a['eligible']]
                cs.sort(key=lambda x: (-x['activation'], -len(x['edges']), tuple(x['edges']), x['circuit_id']))
                expected = cs + [dict(edges=[i], source='primitive', activation=0.0, mismatch=0.0, circuit_id=None,
                                       binding=None, prior=0.0, circuit_version=0) for i in primitive]
                require(p['candidates'] == expected, 'candidate ranking/primitive fallback')
                reason = 'circuit_candidate' if cs else 'circuit_mismatch' if activations else 'no_applicable_circuit'
                require(p['reason'] == reason, 'novelty/mismatch reason')
                s['proposals'] = expected
                s['cost'].topology_edge_checks += len(obs.edges)
                s['cost'].primitive_candidates += len(primitive)
            elif name == 'r02_expansion':
                s, obs = starts[did], starts[did]['obs']
                require(s['proposals'] and p['candidate'] == s['proposals'][0] and p['prefix'] == s['frontier'][0], 'unproposed graph edit')
                planned, checks, error = plan_expansion(obs, s['frontier'], s['routes'], s['known'],
                                                        p['candidate'], s['next_node'], config)
                require(error is None, 'graph edit exceeded a budget')
                additions, known = planned
                require(p['added'] == additions, 'lost side branch or mutated node identity')
                s['next_node'] += len(additions)
                s['known'] = known
                s['frontier'] = [r for r in additions if r['visited'][-1] != obs.goal] + s['frontier'][1:]
                s['routes'] += [r for r in additions if r['visited'][-1] == obs.goal]
                require(p['complete'] is (not s['frontier']), 'false dependency coverage')
                s['cost'].topology_edge_checks += checks
                s['cost'].expansions += 1
                s['cost'].graph_nodes_created += len(additions)
                s['cost'].graph_edges_created += len(additions)
                s['cost'].circuit_reuses += int(p['candidate']['source'] == 'circuit')
                s['proposals'], s['pool_activations'], s['scan'] = None, [], None
                graph_steps += 1
            elif name == 'r02_dead_end':
                s = starts[did]
                require(s['proposals'] == [] and p['prefix'] == s['frontier'][0], 'false dead end')
                s['frontier'].pop(0)
                s['cost'].expansions += 1
                s['cost'].frontier_retirements += 1
                s['proposals'], s['pool_activations'], s['scan'] = None, [], None
                graph_steps += 1
            elif name == 'r02_progress':
                s = starts[did]
                require(p['network_id'] == s['last_network'] and p['graph_complete'] is (not s['frontier'])
                        and p['completed_paths'] == [r['path'] for r in s['routes']], 'progress state')
                n = networks.get(s['last_network'])
                unsupported = not any(u['prior'] != 0 for r in s['routes'] for u in r['uses']) and all(e.score is None or e.score == 0 for e in s['obs'].edges)
                negative = n is not None and n['convergence']['status'] == 'stable_decision' and n['state']['goal'] < .5 and not unsupported
                expected = dict(kind='negative_requires_dependency_coverage' if negative else 'unresolved_or_no_goal_candidate', magnitude=1.0, detail='')
                require(p['mismatch'] == expected, 'mismatch did not follow the observed state')
                s['mismatch'] = expected
            elif name == 'r02_expansion_exhausted':
                s = starts[did]
                if s['cost'].expansions >= config.max_expansions:
                    expected_reason = 'D expansion budget exhausted'
                elif s['proposals']:
                    _, checks, expected_reason = plan_expansion(s['obs'], s['frontier'], s['routes'], s['known'],
                                                               s['proposals'][0], s['next_node'], config)
                    require(expected_reason is not None, 'false budget failure')
                    s['cost'].topology_edge_checks += checks
                else:
                    needed = len(s['obs'].edges) + sum(len(r['path']) for r in s['routes']) + 1
                    require(needed > config.kernel.max_groups, 'unjustified expansion exhaustion')
                    expected_reason = 'signal group budget'
                require(p['reason'] == expected_reason, 'budget reason')
                s['failed'] = expected_reason
            elif name == 'r02_decision':
                did = p['id']
                s, obs = starts[did], starts[did]['obs']
                require(did not in decisions and active_did == did, 'duplicate/unlisted decision')
                d = codec.adaptive_decision_from(p)
                require(d.observation_digest == obs.digest and d.observation_revision == obs.revision and d.episode_id == obs.episode_id,
                        'decision observation identity')
                require(d.mode.value == s['payload']['mode'] and d.attempt == s['payload']['attempt']
                        and d.memory_version == s['payload']['memory_version'] and d.adaptive_config_signature == config.signature, 'decision mode/version')
                require(d.graph_complete is (not s['frontier']) and p['expanded_paths'] == [r['path'] for r in s['routes']], 'decision dependency coverage')
                used = sorted({u['circuit_id'] for r in s['routes'] for u in r['uses']})
                require(p['circuit_ids'] == used and p['circuit_id'] == (used[0] if len(used) == 1 else None), 'decision circuit provenance')
                require(d.method == ('adaptive_graph_circuit' if used else 'adaptive_graph'), 'decision method')
                n = networks.get(s['last_network'])
                value, cv, state = None, dict(status='no_candidate', ticks=0, residual=0.0, margin=0.0, stable_steps=0), {}
                if n is not None:
                    require(n['settled'], 'decision before convergence finished')
                    cv, state = dict(n['convergence']), n['state']
                    if cv['status'] == 'stable_decision':
                        value = state['goal'] >= .5
                        if value is False and s['frontier']:
                            value = None
                    unsupported = not any(u['prior'] != 0 for r in s['routes'] for u in r['uses']) and all(e.score is None or e.score == 0 for e in obs.edges)
                    if unsupported:
                        value = None
                        if cv['status'] == 'stable_decision':
                            cv['status'] = 'unsupported'
                if s['failed']:
                    value, cv['status'] = None, 'budget_exhausted'
                require(d.value is value and p['convergence'] == cv and dict(d.state) == state
                        and d.failure_reason == s['failed'], 'decision readout/status repair')
                require(d.program_digest == (n['payload']['program_digest'] if n else None), 'decision network digest')
                if d.value is not None:
                    for eid, fact in d.proof.assumed_edges:
                        slot = next(i for i, e in enumerate(obs.edges) if e.id == eid)
                        require(fact is (state['e:' + str(slot)] >= .5), 'proof assumption differs from signal state')
                    require(p['proof']['paths'] == [[obs.edges[i].id for i in path] for path in p['expanded_paths']], 'proof path substitution')
                    valid, _, _, _ = validate_proof(d.proof, obs, d.value)
                    require(valid is d.proof.under_assumptions_valid, 'proof validity self-report')
                else:
                    require(not d.proof.nodes and d.proof.final is None, 'abstention has a fabricated proof')
                s['cost'].proof_nodes_reconstructed = len(d.proof.nodes)
                require(type(d.cost['wall_seconds']) in (int, float) and isfinite(d.cost['wall_seconds']) and d.cost['wall_seconds'] >= 0, 'timing contract')
                s['cost'].wall_seconds = d.cost['wall_seconds']
                require(d.cost == s['cost'].snapshot(), 'independent operation accounting')
                require(fingerprint(memory) == s['payload']['memory_hash'], 'inference changed memory')
                decisions[did] = p
                active_did = None
            elif name == 'r02_feedback':
                require(active_did is None and did in decisions and did not in feedbacks
                        and decisions[did]['mode'] != 'frozen_eval', 'feedback permission')
                Feedback(**p)
                require(p['observation_digest'] == decisions[did]['observation_digest'], 'feedback observation')
                require(fingerprint(memory) == starts[did]['payload']['memory_hash']
                        and memory['version'] == decisions[did]['memory_version'], 'stale feedback memory')
                require(p['id'] not in memory['consumed_feedback'], 'duplicate feedback identity')
                feedbacks[did], pending_feedback = p, did
            elif name == 'r02_memory_updated':
                did = p['patch']['decision_id']
                require(did == pending_feedback, 'memory mutation outside feedback boundary')
                new, patch, expected_cost = expected_learning(memory, starts[did]['obs'], decisions[did], feedbacks[did], config)
                require(p['memory_document'] == new and p['patch'] == patch and p['memory_after'] == fingerprint(new), 'independent learning transition')
                AdaptiveMemory.from_document(new, config)
                require(type(p['cost']['wall_seconds']) in (int, float) and isfinite(p['cost']['wall_seconds']) and p['cost']['wall_seconds'] >= 0, 'learning time')
                expected_cost.wall_seconds = p['cost']['wall_seconds']
                require(p['cost'] == expected_cost.snapshot(), 'learning operation accounting')
                learning_costs.update(p['cost'])
                memory = new
                known_memory.add(fingerprint(new))
                pending_feedback = None
                updates += 1
            elif name == 'r02_observation_requested':
                require(did in feedbacks and feedbacks[did]['correct'] is False and decisions[did]['mode'] == 'adapt'
                        and starts[did]['engine']['allow_reexpansion'] and did not in requests, 'measurement request permission')
                obs = starts[did]['obs']
                require(decisions[did]['attempt'] <= config.kernel.max_observation_requests, 'measurement budget')
                ids = [e.id for e in sorted(obs.edges, key=lambda e: (abs(e.score or 0), e.id)) if e.score is None or abs(e.score) < .9]
                require(p['edge_ids'] == ids and ids and p['revision'] == obs.revision + 1
                        and p['episode_id'] == obs.episode_id and p['reason'] == 'uncertain_features_after_error', 'measurement scope')
                requests[did] = p
            else:
                raise ContractError('R0.2.1 engine event not allowed: ' + str(name))
        require(pending_feedback is None and all(n['settled'] for n in networks.values()), 'unfinished transaction/kernel boundary')
        seconds = transition['active_seconds']
        if active_did is not None:
            require(type(seconds) in (int,float) and isfinite(seconds) and seconds >= 0, 'active timing contract')
            if op == 'advance':
                require(seconds >= current_core['pending']['active_seconds'], 'active elapsed time moved backwards')
            active = _pending(starts[active_did], networks, config, seconds)
        else:
            require(seconds is None, 'idle state has active timing')
            active = None
        current_core = dict(config=codec.plain(config), memory=memory,
            switches={k:engine[k] for k in ('use_circuits','top_down','allow_reexpansion')}, attempts=attempts,
            held={did:dict(observation=codec.plain(starts[did]['obs']), decision=d, recorded_hash=fingerprint(d),
                          memory_hash=starts[did]['payload']['memory_hash']) for did,d in decisions.items()},
            feedback=feedbacks, requests=requests, pending=active)
        require(fingerprint(current_core) == transition['after_state'], 'snapshot state/counter differs from independent event replay')
        previous_core, previous_transition = transition['after_state'], transition['sha256']
        offset = end
    require(offset == len(events) and core == current_core, 'snapshot payload does not match generation tip')
    return dict(schema='hcr-session-audit-r021-v1', verified=True, generation=len(journal)-1,
        events=len(events), decisions_checked=len(decisions), scalar_ticks_replayed=steps,
        graph_steps_checked=graph_steps, binding_scans_checked=scans_verified,
        memory_updates_checked=updates, checkpoint_state_replayed=True,
        new_inferences=0, external_truth_evaluated=False,
        scope='independent event/state/counter replay; declared seed memory and feedback are inputs; timing is range-checked only')
