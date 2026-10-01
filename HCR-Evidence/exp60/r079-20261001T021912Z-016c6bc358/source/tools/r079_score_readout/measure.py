"""Read-only measurement from independently replayed journals and boundaries."""
from tools.r050_review_boundary.common import require
from tools.r078_binding_order.audit import public_path


def readout_state(status, goal, graph_complete, unsupported=False):
    candidate = goal >= .5 if status == 'stable_decision' and not unsupported else None
    ready = candidate is True or graph_complete
    value = candidate if candidate is True or (candidate is False and graph_complete) else None
    reason = (None if candidate is True or (candidate is False and graph_complete) else
              'negative_requires_dependency_coverage' if candidate is False else 'unresolved_or_no_goal_candidate')
    category = ('stable_true' if candidate is True else 'stable_false' if candidate is False else
                'unsupported' if unsupported else 'stable_ambiguous' if status == 'stable_ambiguous' else status)
    return dict(candidate_value=candidate, ready=ready, pending_value=value,
                progress_mismatch_kind=reason, category=category)


def decision_networks(execution, states, observation):
    doc = execution['packet']['document']; events = doc['events']; result = []
    unsupported = all(e['score'] in (0, None) for e in observation['edges'])
    for index, event in enumerate(events):
        if event['event'] != 'r02_network' or event['payload']['kind'] != 'decision':
            continue
        n = event['payload']; nid = n['network_id']
        owners = [t for t in doc['transitions'] if t['event_start'] <= index < t['event_end']]
        require(len(owners) == 1 and owners[0]['operation'] == 'advance', 'Unique creation advance')
        t = owners[0]; g = t['generation']; p = states[g]['pending']
        within = events[t['event_start']:t['event_end']]
        settled = [x for x in within if x['event'] == 'r02_settled' and x['payload']['network_id'] == nid]
        require(len(settled) == 1 and p['network_id'] == nid, 'Settled network to boundary binding')
        s = settled[0]['payload']; conv = s['convergence']; goal = s['state']['goal']
        complete = not p['workspace']['frontier']
        expected = readout_state(conv['status'], goal, complete, unsupported)
        progress = [x for x in within if x['event'] == 'r02_progress' and x['payload']['network_id'] == nid]
        require(len(progress) == int(expected['progress_mismatch_kind'] is not None), 'Progress presence at creation advance')
        actual_reason = progress[0]['payload']['mismatch']['kind'] if progress else None
        require(actual_reason == expected['progress_mismatch_kind'], 'Network-local progress reason')
        require(p['ready'] is expected['ready'] and p['value'] is expected['pending_value'], 'Independent readout boundary')
        require(p['state'] == s['state'] and abs(conv['margin']-abs(2*goal-1)) <= 2e-12, 'State/margin boundary')
        ticks = [x for x in within if x['event'] == 'r02_tick' and x['payload']['network_id'] == nid]
        require(len(ticks) == conv['ticks'], 'Per-network tick count')
        frontier = p['workspace']['frontier']
        result.append(dict(network_id=nid, event_index=index, event_seq=event['seq'], generation=g,
            advance_index=sum(x['operation'] == 'advance' for x in doc['transitions'][:g+1]),
            transition_event_start=t['event_start'], transition_event_end=t['event_end'],
            settled_event_seq=settled[0]['seq'], progress_event_seq=progress[0]['seq'] if progress else None,
            convergence=conv, goal_activation=goal, final_state=s['state'], **expected,
            graph_complete=complete, frontier=frontier,
            frontier_public_paths=[public_path(observation,f['path']) for f in frontier],
            route_slot_paths=[r['path'] for r in n['metadata']['routes']],
            route_public_paths=[public_path(observation,r['path']) for r in n['metadata']['routes']],
            unsupported_gate=unsupported, boundary_cost=p['cost'],
            subsequent_expansion_count=sum(x['event'] == 'r02_expansion' for x in events[t['event_end']:]),
            measurement_status='measured'))
    return result


def proof_support(decision):
    proof = decision['proof']; nodes = {n['id']:n for n in proof['nodes']}
    require(len(nodes) == len(proof['nodes']), 'Unique proof node identity')
    if proof['final'] is None:
        return dict(measurement_status='no_final_proof', path_inventory=proof['paths'],
                    final=None, final_path_index=None, selected_edge_id_path=None,
                    final_support_node_ids=[], recomputed_D_DAG=None)
    reached = set(); active = set(); depths = {}
    def visit(identity):
        require(identity in nodes and identity not in active, 'Existing acyclic final dependency')
        if identity in reached:
            return depths[identity]
        active.add(identity); n = nodes[identity]
        depth = 0 if not n['parents'] else 1+max(visit(i) for i in n['parents'])
        active.remove(identity); reached.add(identity); depths[identity] = depth
        return depth
    depth = visit(proof['final'])
    require(depth == proof['primitive_depth'], 'Final dependency depth')
    index = nodes[proof['final']]['path_index']; selected = None
    if decision['value'] is True:
        require(type(index) is int and 0 <= index < len(proof['paths']), 'Positive final path index')
        selected = proof['paths'][index]
        require({nodes[i]['edge_id'] for i in reached if nodes[i]['edge_id'] is not None} == set(selected), 'Final support edge identity')
        require(all(nodes[i]['path_index'] in (None,index) for i in reached), 'Positive ancestry path')
        require({e for e,v in proof['assumed_edges'] if v} == set(selected), 'Positive assumptions')
        state = dict(decision['state'])
        slots = {e:i for i,e in enumerate(decision['_slot_to_edge_id'])}
        eligible = [i for i,path in enumerate(proof['paths']) if all(state['e:'+str(slots[e])] >= .5 for e in path)]
        ranking = sorted(eligible, key=lambda i:(-state[f'p:{i}:{len(proof["paths"][i])-1}'],i))
        require(ranking and index == ranking[0], 'Independent eligible terminal path ranking')
    return dict(measurement_status='measured', path_inventory=proof['paths'], final=proof['final'],
                final_path_index=index, selected_edge_id_path=selected,
                final_support_node_ids=sorted(reached), final_support_nodes=[nodes[i] for i in sorted(reached)],
                recomputed_D_DAG=depth)


def measurement_selftest():
    cases = [('stable_decision',.02,False,False,False,False,'negative_requires_dependency_coverage'),
             ('stable_decision',.02,True,False,False,True,None),
             ('stable_ambiguous',.5,False,False,None,False,'unresolved_or_no_goal_candidate'),
             ('stable_ambiguous',.5,True,False,None,True,'unresolved_or_no_goal_candidate'),
             ('stable_decision',.99,False,False,True,True,None),
             ('stable_decision',.99,False,True,None,False,'unresolved_or_no_goal_candidate')]
    for status,goal,complete,unsupported,value,ready,reason in cases:
        r = readout_state(status,goal,complete,unsupported)
        require((r['candidate_value'],r['ready'],r['progress_mismatch_kind']) == (value,ready,reason), 'Synthetic readout classes')
    require(abs(2*.36-1) < .3 and abs(2*.64-1) < .3, 'Synthetic interior ambiguity margin')
    require(abs(2*.34-1) >= .3 and abs(2*.66-1) >= .3, 'Synthetic exterior decision margin')
    return dict(readout_cases=len(cases), margin_cases=4, synthetic_native_executions=0, research_sample=False)
