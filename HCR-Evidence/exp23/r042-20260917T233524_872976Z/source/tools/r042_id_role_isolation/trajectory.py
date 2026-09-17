"""평가 전용 inverse-ID 투영. native raw/state/proof/reference는 수정하지 않는다."""
from copy import deepcopy
from .storage import digest, require
from .input_audit import declared_map


def canonical_path(path, inverse):
    require(type(path) is list and all(type(e) is str and e in inverse for e in path), '미등록 path ID; 자동 보정 금지')
    return [inverse[e] for e in path]


def canonical_assumptions(items, inverse):
    if items is None: return None
    require(type(items) is list, 'assumption list')
    result = []
    for pair in items:
        require(isinstance(pair,(list,tuple)) and len(pair) == 2 and type(pair[1]) is bool, 'assumption pair')
        require(pair[0] in inverse, '미등록 assumption edge ID')
        result.append([inverse[pair[0]],pair[1]])
    return sorted(result)


def canonical_state(state, inverse):
    require(set(state) == {'edges','prefixes','goal'}, 'aligned state schema')
    edges = []
    for eid,value in state['edges']:
        require(eid in inverse, '미등록 activation edge ID')
        edges.append([inverse[eid],value])
    prefixes = [dict(route=canonical_path(p['route'],inverse), prefix=canonical_path(p['prefix'],inverse),
                     activation=p['activation']) for p in state['prefixes']]
    prefixes.sort(key=lambda p:(p['route'],p['prefix']))
    return dict(edges=sorted(edges), prefixes=prefixes, goal=state['goal'])


def describe(run: dict, record: dict, case: dict) -> dict:
    from r041_scheduler_direction.trial_audit import candidate_view
    from r039_order_isolation.trajectory import completion_trace, aligned_state, id_path
    base = run['base']; obs = case['observation']
    inverse = {v:k for k,v in declared_map(case['id_variant']).items()}
    require(len(base['candidates']) == len(record['readouts']), 'readout inventory')
    timeline, native_rows = [], []
    for candidate,row in zip(base['candidates'],record['readouts']):
        view = candidate_view(candidate)
        require(digest(view['observation']) == digest(obs), 'candidate observation 변경')
        native_paths = [id_path(obs,p) for p in view['completed_paths']]
        paths = [canonical_path(p,inverse) for p in native_paths]
        timeline.append(dict(ordinal=row['ordinal'], ticks=row['kernel_ticks_at_readout'],
            raw_value=row['raw_value'], native_accepted=row['native_accepted'],
            policy_accepted=row['policy_accepted'], frontier_count=row['frontier_count'],
            completed_paths=paths,
            supported_paths=[paths[i] for i in row['supported_completed']],
            activation_eligible_supported_paths=[paths[i] for i in row['activation_eligible_supported']],
            supported_positive_available=row['supported_positive_available'],
            differential_opportunity=row['differential_opportunity'],
            native_assumptions=canonical_assumptions(row['native_assumptions'],inverse),
            selected_assumptions=canonical_assumptions(row['selected_assumptions'],inverse),
            native_D_DAG=row['native_D_DAG'], policy_D_DAG=row['D_DAG'],
            state=canonical_state(aligned_state(view),inverse)))
        native_rows.append(dict(ordinal=row['ordinal'],native_paths=native_paths,
            canonical_paths=paths,native_assumptions=deepcopy(row['native_assumptions']),
            selected_assumptions=deepcopy(row['selected_assumptions'])))
    native_trace = completion_trace(base)
    canonical_trace = [dict(rank=item['rank'], expansion=item['expansion'],
        path=canonical_path(item['path_edge_ids'],inverse)) for item in native_trace]
    pending = base['packet']['document']['engine']['pending']
    terminal_paths = [id_path(obs,p['path']) for p in pending['workspace']['routes']]
    require([item['path_edge_ids'] for item in native_trace] == terminal_paths, '완성 event/terminal 경로 불일치')
    terminal_canonical = [canonical_path(p,inverse) for p in terminal_paths]
    support = next((row for row in timeline if row['supported_paths']),None)
    usable = next((row for row in timeline if row['supported_positive_available']),None)
    support_rank = next((i['rank'] for i in canonical_trace if i['path'] == ['e0','e1']),None)
    final = record['final']; projection = None
    if final['accepted']:
        index = final['readout_ordinal']; proof = base['selections'][index]['proof']
        projection = dict(D_DAG=record['readouts'][index]['D_DAG'],
            assumed_edges=canonical_assumptions(proof['assumed_edges'],inverse),
            paths=[canonical_path(p,inverse) for p in proof['paths']])
    requests = [event for event in base['events'] if event['event'] == 'schedule_requested']
    decisions = [event['decision'] for event in base['events'] if event['event'] == 'schedule_decided']
    require(len(requests) == len(decisions), 'scheduler request/decision 불일치')
    scheduler_rows = []
    for index,(request,decision) in enumerate(zip(requests,decisions)):
        ids = request['view']['edge_ids']
        slots = request['view']['frontier_paths']
        frontier = [[ids[s] for s in p] for p in slots]
        selected = decision['selected_edge_ids']
        scheduler_rows.append(dict(ordinal=index, native_frontier=frontier,
            canonical_frontier=[canonical_path(p,inverse) for p in frontier],
            native_selected=selected,
            canonical_selected=None if selected is None else canonical_path(selected,inverse),
            priority_required=decision['priority_required'], usage=deepcopy(decision['usage'])))
    competing = next((r for r in requests if len(r['view']['frontier_paths']) >= 2),None)
    probe = None
    if competing is not None:
        generation = competing['reference']['generation']; view = competing['view']
        preceding = [timeline[i] for i,candidate in enumerate(base['candidates'])
                     if candidate['reference']['generation'] <= generation]
        frontier = [[view['edge_ids'][s] for s in p] for p in view['frontier_paths']]
        probe = dict(readouts_before_first_competitive_schedule=preceding,
                     canonical_frontier_set=sorted(canonical_path(p,inverse) for p in frontier))
    return dict(inverse_mapping=inverse, canonical_trace=canonical_trace, native_trace=native_trace,
        native_readout_paths=native_rows, canonical_readouts=timeline,
        canonical_trajectory_sha256=digest(timeline),
        canonical_completion_sha256=digest([item['path'] for item in canonical_trace]),
        terminal_canonical_paths=terminal_canonical,
        final_proof_projection=projection, support_route_completion_rank=support_rank,
        first_supported_readout=None if support is None else dict(ordinal=support['ordinal'],ticks=support['ticks'],
                                                                 frontier_count=support['frontier_count']),
        first_usable_supported_readout=None if usable is None else dict(ordinal=usable['ordinal'],ticks=usable['ticks'],
                                                                       frontier_count=usable['frontier_count']),
        pre_competitive_probe=probe, scheduler_rows=scheduler_rows,
        mapping_boundary='independent_evaluator_only', native_artifacts_modified=False,
        probe_scope='readouts_and_frontier_set_only; not_full_state_equivalence')
