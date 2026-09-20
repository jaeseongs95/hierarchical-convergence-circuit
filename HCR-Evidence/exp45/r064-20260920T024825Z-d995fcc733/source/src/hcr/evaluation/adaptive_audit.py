"""R0.2 실행 기록의 독립 수치/경로/학습/집계 검산.

생산 runtime/dynamics/expansion/activation/learning을 호출하지 않는다.
JSON 계약, memory 구조 certificate loader, 외부 proof/reference는 공유한다.
외부 실행 인증이나 가설 입증 도구가 아니다.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
from math import isfinite
from pathlib import Path, PurePosixPath
import hashlib
from .. import codec
from ..model import AdaptiveCost, ContractError, fingerprint
from ..circuits import AdaptiveMemory
from ..trace import check_chain
from .reference import assess, validate_proof
from .audit import require, independent_step
from .adaptive_audit_support import (scan_patterns, pool_network, decision_network, plan_expansion,
                                     expected_learning, circuit_id)


def safe_relative(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and bool(name) and not p.is_absolute() and '..' not in p.parts
            and '\\' not in name and ':' not in name, 'unsafe artifact path')
    return p


def counted(rows):
    values = dict(attempts=0, correct=0, incorrect=0, unresolved=0, strict_correct=0, wrong_stable=0, circuit_reuse=0)
    for row in rows:
        values['attempts'] += 1
        a = row['assessment']
        values['unresolved' if a['correct'] is None else 'correct' if a['correct'] else 'incorrect'] += 1
        values['strict_correct'] += int(a['correct'] is True and a['proof_valid'] and a['assumption_correct'] is True)
        values['wrong_stable'] += int(a['wrong_stable'])
        values['circuit_reuse'] += int(bool(row['decision']['circuit_ids']))
    return values


def verify_run(root: Path, *, check_source: bool = True):
    try:
        return _verify(Path(root).resolve(), check_source)
    except ContractError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        raise ContractError('R0.2 audit malformed record: ' + str(error)) from error


def _verify(root, check_source):
    manifest = codec.loads((root / 'manifest.json').read_bytes())
    require(manifest['schema'] == 'hcr-run-manifest-r02' and manifest['state'] == 'complete', 'R0.2 incomplete manifest')
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'run symlink')
        if path.is_file() and path != root / 'manifest.json':
            actual.add(path.relative_to(root).as_posix())
    require(actual == set(manifest['files']), 'missing/extra run artifacts')
    for name, digest in manifest['files'].items():
        safe_relative(name)
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, 'artifact hash ' + name)
    plan = codec.loads((root / 'plan.json').read_bytes())
    require(plan['schema'] == 'hcr-plan-r02' and plan['protocol'] == 'r02-authored-path-motifs-v1', 'plan protocol')
    config = codec.adaptive_config_from(plan['config'])
    require(config.signature == plan['config_signature'] and plan['evaluation_labels_passed_to_engine'] is False,
            'plan config/boundary')
    project = Path(__file__).resolve().parents[3]
    require(bool(plan['source_hashes']), 'empty source provenance')
    for name, digest in plan['source_hashes'].items():
        safe_relative(name)
        require(name.startswith('src/hcr/') or name in ('hcr.py', 'configs/r01.toml', 'configs/r02.toml'), 'source scope')
        if check_source:
            require((project / name).is_file() and hashlib.sha256((project / name).read_bytes()).hexdigest() == digest,
                    'source differs ' + name)
    if check_source:
        expected_sources = {p.relative_to(project).as_posix() for p in (project / 'src/hcr').rglob('*.py')}
        expected_sources |= {'hcr.py', 'configs/r01.toml', 'configs/r02.toml'}
        require(set(plan['source_hashes']) == expected_sources, 'source inventory coverage')
    status = codec.loads((root / 'status.json').read_bytes())
    require(status['schema'] == 'hcr-status-r02' and status['state'] == 'complete', 'run status not complete')
    rows = [codec.loads(line) for line in (root / 'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
    events = [codec.loads(line) for line in (root / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
    check_chain(events, status['event_count'], status['event_head'])
    rowmap = {row['decision']['id']: row for row in rows}
    require(len(rowmap) == len(rows) == status['episode_records'], 'row accounting/duplicates')
    starts, decisions, networks, assessments, feedbacks, requests, delivered = {}, {}, {}, {}, {}, {}, {}
    known_memory = {AdaptiveMemory.empty(config).digest}
    memory = None
    engine = None
    attempts = {}
    pending_feedback = None
    steps = updates = scans_verified = graph_steps = 0
    checkpoints = []
    learning_costs = Counter()

    for event in events:
        name, p = event['event'], event['payload']
        did = p.get('decision_id')
        if name == 'r02_engine_created':
            require(pending_feedback is None, 'new engine before committed feedback')
            require(p['config'] == plan['config'] and p['config_signature'] == config.signature, 'engine config')
            require(all(type(p[k]) is bool for k in ('use_circuits', 'top_down', 'allow_reexpansion')), 'engine flag types')
            loaded = AdaptiveMemory.from_document(p['memory_document'], config)
            require(loaded.digest == p['memory_hash'] and loaded.digest in known_memory, 'unproven initial memory')
            memory = loaded.document()
            engine = deepcopy(p)
            attempts = {}
        elif name == 'r02_attempt_started':
            require(engine is not None and did not in starts and pending_feedback is None, 'attempt ordering')
            obs = codec.observation_from(p['observation'])
            require(len(obs.edges) <= config.kernel.max_edges, 'input edge budget')
            require(p['mode'] in ('train', 'frozen_eval', 'adapt'), 'mode contract')
            require(p['memory_hash'] == fingerprint(memory) and p['memory_version'] == memory['version'], 'memory changed during inference')
            previous = p['revision_of']
            if previous is not None:
                require(previous in requests and previous in delivered and p['mode'] == 'adapt', 'unauthorized revision')
                require(p['observation'] == delivered[previous], 'delivered observation was replaced')
                require(obs.episode_id == requests[previous]['episode_id'] and obs.revision == requests[previous]['revision'], 'revision identity')
            else:
                require(obs.episode_id not in attempts, 'episode repetition without revision')
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
            require(did not in decisions and did in rowmap, 'duplicate/unlisted decision')
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
            require(rowmap[did]['decision'] == p and rowmap[did]['observation'] == codec.plain(obs), 'first decision was overwritten')
            require(rowmap[did]['memory_before'] == rowmap[did]['memory_after_inference'] == s['payload']['memory_hash'], 'inference changed memory')
            decisions[did] = p
        elif name == 'r02_external_assessment':
            require(did in decisions and did not in assessments, 'assessment sequence')
            actual_assessment = codec.plain(assess(codec.adaptive_decision_from(decisions[did]), starts[did]['obs'], rowmap[did]['external_truth']))
            require(actual_assessment == p['assessment'] == rowmap[did]['assessment'], 'independent external/proof assessment')
            assessments[did] = actual_assessment
        elif name == 'r02_feedback':
            require(did in assessments and did not in feedbacks and decisions[did]['mode'] != 'frozen_eval', 'feedback permission')
            aa = assessments[did]
            require(p['correct'] is aa['correct'] and p['proof_valid'] is (aa['proof_valid'] and aa['assumption_correct'] is True)
                    and p['observation_digest'] == decisions[did]['observation_digest'], 'unauthorized feedback value')
            require(fingerprint(memory) == starts[did]['payload']['memory_hash'], 'stale feedback memory')
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
        elif name == 'r02_measurement_delivered':
            did = p['request']['decision_id']
            require(did in requests and did not in delivered and p['request'] == requests[did], 'unrequested measurement')
            old = codec.plain(starts[did]['obs'])
            expected = deepcopy(old)
            expected['revision'] += 1
            for edge in expected['edges']:
                if edge['id'] in requests[did]['edge_ids']:
                    edge['score'] = .98 if rowmap[did]['external_truth'][edge['id']] else -.98
            require(p['observation'] == expected, 'measurement changed topology or unauthorized facts')
            delivered[did] = expected
        elif name == 'r02_memory_checkpoint':
            safe_relative(p['path'])
            loaded = AdaptiveMemory.load(root / p['path'], config)
            require(loaded.digest == p['memory_hash'] == fingerprint(memory) and loaded.version == p['memory_version']
                    and (root / p['path']).stat().st_size == p['bytes_written'], 'memory persistence/reload')
            checkpoints.append(p)
        else:
            raise ContractError('audit: unknown R0.2 event ' + str(name))

    require(pending_feedback is None, 'unfinished learning transaction')
    require(set(starts) == set(decisions) == set(assessments) == set(rowmap), 'unaccounted attempt/assessment')
    require(all(n['settled'] for n in networks.values()), 'unfinished convergence network')
    require(set(feedbacks) == {d for d, p in decisions.items() if p['mode'] != 'frozen_eval'}, 'missing/extra feedback')
    require(set(requests) == set(delivered), 'requested measurement was not delivered')
    summary = codec.loads((root / 'summary.json').read_bytes())
    require(summary['schema'] == 'hcr-development-summary-r02' and summary['hypothesis_proved'] is False, 'summary scope')
    groups, total_cost = defaultdict(list), defaultdict(Counter)
    for row in rows:
        key = row['phase'] + '/' + row['arm']
        groups[key].append(row)
        total_cost[key].update(row['decision']['cost'])
        total_cost[key]['verification_checks'] += row['assessment']['verification_checks']
    require(summary['groups'] == {k: counted(v) for k, v in groups.items()}, 'summary group counts')
    require(summary['costs'] == {k: dict(v) for k, v in total_cost.items()}, 'summary cost totals')
    require(summary['learning_costs'] == dict(learning_costs), 'summary learning cost totals')
    require(summary['checkpoints'] == checkpoints, 'summary persistence evidence')
    require(summary['event_counts'] == dict(Counter(e['event'] for e in events)), 'summary event totals')
    require(summary['actual_llm_calls'] == summary['actual_network_calls'] == 0
            and status['actual_llm_calls'] == status['actual_network_calls'] == 0, 'offline execution declaration')
    adaptation = {}
    for key, group in groups.items():
        if key.startswith(('misconvergence/', 'tradeoff/')):
            adaptation[key] = dict(attempts=len(group), initial=group[0]['assessment'], final=group[-1]['assessment'],
                                  initial_decision=group[0]['decision']['id'], final_decision=group[-1]['decision']['id'])
    require(summary['adaptation'] == adaptation, 'initial failure/revision aggregation')
    expected_pairs = {}
    for case in ('same_structure', 'counterfactual', 'renamed_reordered'):
        cold = [r for r in groups['familiarity/cold'] if r['case'] == case]
        warm = [r for r in groups['familiarity/warm'] if r['case'] == case]
        require(len(cold) == len(warm) == 1, 'familiarity matched pair coverage')
        cold, warm = cold[0], warm[0]
        require(cold['observation'] == warm['observation'] and cold['external_truth'] == warm['external_truth'], 'familiarity input mismatch')
        expected_pairs[case] = dict(cold_decision=cold['decision']['id'], warm_decision=warm['decision']['id'],
            cold_correct=cold['assessment']['correct'], warm_correct=warm['assessment']['correct'],
            cold_primitive_D=cold['decision']['proof']['primitive_depth'], warm_primitive_D=warm['decision']['proof']['primitive_depth'],
            warm_minus_cold={k: warm['decision']['cost'][k] - cold['decision']['cost'][k]
                for k in ('graph_nodes_created', 'graph_edges_created', 'expansions', 'binding_operations',
                          'signal_events', 'convergence_ticks', 'wall_seconds')})
    require(summary['familiarity_pairs'] == expected_pairs, 'familiarity cost/proof-D comparison')
    require(plan['training_episodes'] == 6 and plan['tradeoff_training_counts'] == [3, 9], 'development protocol training counts')
    required_counts = {'training/full': 6, 'familiarity/cold': 3, 'familiarity/warm': 3,
        'novelty/graph_only': 2, 'novelty/full': 2, 'retention/reload': 1,
        'tradeoff_training/training_3': 3, 'tradeoff_training/training_9': 9}
    adaptive_groups = {'misconvergence/full', 'misconvergence/no_reexpansion', 'tradeoff/training_3', 'tradeoff/training_9'}
    require(set(groups) == set(required_counts) | adaptive_groups, 'development protocol phases')
    for key, count in required_counts.items():
        require(len(groups[key]) == count, 'development protocol count ' + key)
    for key in adaptive_groups:
        require(1 <= len(groups[key]) <= config.kernel.max_observation_requests + 1, 'adaptation attempt count')
        require([r['decision']['attempt'] for r in groups[key]] == list(range(1, len(groups[key]) + 1)), 'adaptation chronology')
    require(len(groups['misconvergence/no_reexpansion']) == 1, 're-expansion ablation changed')
    for case in ('longer_composition', 'branched_composition'):
        a = [r for r in groups['novelty/graph_only'] if r['case'] == case]
        b = [r for r in groups['novelty/full'] if r['case'] == case]
        require(len(a) == len(b) == 1 and a[0]['observation'] == b[0]['observation']
                and a[0]['memory_before'] == b[0]['memory_before'] and a[0]['external_truth'] == b[0]['external_truth'],
                'novelty ablation input/support mismatch')
        require(starts[a[0]['decision']['id']]['engine']['use_circuits'] is False
                and starts[b[0]['decision']['id']]['engine']['use_circuits'] is True, 'novelty ablation flags')
    return dict(schema='hcr-independent-audit-r02', state='complete', verified=True, differences=[],
        source_checked=check_source, file_hashes=len(manifest['files']), decisions_reassessed=len(rows), events=len(events),
        scalar_ticks_replayed=steps, binding_scans_checked=scans_verified, graph_steps_checked=graph_steps,
        memory_updates_checked=updates, checkpoints=len(checkpoints), hypothesis_proved=False,
        independent_of_runtime=['tick numerical calculation', 'bounded role binding scans', 'candidate ranking',
            'macro side-branch preservation', 'decision readout', 'learning transitions', 'operation counts', 'summary aggregation'],
        shared_components=['JSON/data contracts', 'memory structural certificate loader', 'external proof/reference validator'],
        limitations=['기록의 내부 일관성을 검산하며, 제삼자의 실행 인증은 아니다.',
                     'wall_seconds는 부호·유한성·집계만 확인하며 실측 시간을 재현하지 않는다.'])
