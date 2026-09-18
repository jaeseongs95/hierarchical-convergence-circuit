"""독립 evaluator 전용 측정. 전체 입력의 판별 가능성을 native/controller에 전달하지 않는다."""
from __future__ import annotations
from r035_frozen_selection.audit import demand


def reachable(obs: dict, truth: dict) -> bool:
    demand(set(truth)=={e['id'] for e in obs['edges']} and all(type(v) is bool for v in truth.values()),'world 형식')
    found={obs['start']}; stack=[obs['start']]
    while stack:
        n=stack.pop()
        for e in obs['edges']:
            if e['source']==n and truth[e['id']] and e['target'] not in found:
                found.add(e['target']);stack.append(e['target'])
    return obs['goal'] in found


def identifiability(obs: dict, threshold: float=0.) -> dict:
    lower={e['id']:e['score'] is not None and e['score']>threshold for e in obs['edges']}
    upper={e['id']:e['score'] is None or e['score']>=-threshold for e in obs['edges']}
    lo=reachable(obs,lower);hi=reachable(obs,upper)
    return dict(identifiable=lo==hi,value=lo if lo==hi else None,
                positive_support_path_exists=lo,possible_positive_path_exists=hi)


def complete_route(obs: dict, slots: list[int]) -> bool:
    if not slots or any(type(i) is not int or not 0<=i<len(obs['edges']) for i in slots):return False
    edges=[obs['edges'][i] for i in slots]
    vertices=[edges[0]['source']]+[e['target'] for e in edges]
    return (edges[0]['source']==obs['start'] and edges[-1]['target']==obs['goal']
        and all(a['target']==b['source'] for a,b in zip(edges,edges[1:]))
        and len(vertices)==len(set(vertices)))


def proposed_routes(candidate: dict, obs: dict) -> list[list[int]]:
    """후보 pool의 경로 제안과 workspace에 완성된 경로를 같은 것으로 세지 않는다."""
    routes=set(); did=candidate['decision']['id']
    for event in candidate['packet']['document']['events']:
        p=event['payload']
        if event['event']!='r02_proposals' or p['decision_id']!=did:continue
        for c in p['candidates']:
            route=list(p['prefix']['path'])+list(c['edges'])
            if complete_route(obs,route):routes.add(tuple(route))
    return [list(p) for p in sorted(routes)]


def diagnose_state(view: dict, candidate: dict, results: dict) -> dict:
    """원인 확정 대신 관찰된 gap 위치를 다중 플래그와 운영상 분류로 기록한다."""
    obs=view['observation'];edges=obs['edges'];threshold=view['min_abs_score'];state=view['state']
    info=identifiability(obs,threshold)
    def support(path):return all(edges[s]['score'] is not None and edges[s]['score']>threshold for s in path)
    paths=view['completed_paths']
    supported=[i for i,p in enumerate(paths) if support(p)]
    active=[i for i in supported if all(state[f'e:{s}']>=.5 for s in paths[i])]
    proposals=proposed_routes(candidate,obs);supported_proposals=[p for p in proposals if support(p)]
    raw=view['raw_value'];native=results['native_saved'];chosen=results['support_first']
    conflict=info['identifiable'] and raw is not None and raw is not info['value']
    if native['accepted']:label='native_supported'
    elif not info['identifiable']:label='information_underdetermined'
    elif info['value'] is False:label='known_negative_not_accepted'
    elif not supported:label='supported_route_proposed_not_completed' if supported_proposals else 'supported_route_not_completed'
    elif not active:label='completed_support_activation_gap'
    elif raw is not True:label='supported_route_raw_nonpositive'
    elif chosen['accepted']:label='proof_selection_gap_recovered'
    else:label='selection_unresolved'
    return dict(label=label,label_is_causal_attribution=False,information=info,
        raw_conflicts_with_identified_value=bool(conflict),
        completed_route_count=len(paths),completed_supported_indices=supported,
        completed_activation_eligible_supported_indices=active,
        proposed_complete_routes=proposals,proposed_supported_complete_routes=supported_proposals,
        native_accepted=native['accepted'],support_first_accepted=chosen['accepted'],
        same_value_selection_applicable=raw is True,
        recovered_same_value_output=not native['accepted'] and chosen['accepted'],
        support_first_reason=chosen['reason'])


def canonical_state(view: dict, results: dict, edge_map: dict) -> dict:
    """분석용 역매핑만 수행한다. 원 native 기록이나 selector 입력에는 반영하지 않는다."""
    reverse={v:k for k,v in edge_map.items()};edges=view['observation']['edges'];paths=view['completed_paths']
    routes=[[reverse[edges[s]['id']] for s in p] for p in paths]
    edge_activation={reverse[e['id']]:view['state'].get(f'e:{i}') for i,e in enumerate(edges)}
    terminals=[dict(route=route,activation=view['state'][f'p:{i}:{len(paths[i])-1}']) for i,route in enumerate(routes)]
    selected={}
    for policy,out in results.items():
        pi=out['selected_path_index'];p=out['proof']
        selected[policy]=dict(value=out['value'],accepted=out['accepted'],
            route=None if pi is None else routes[pi],D_DAG=None if p is None else p['primitive_depth'],
            assumptions=[] if p is None else sorted([[reverse[e],truth] for e,truth in p['assumed_edges']]))
    return dict(raw_value=view['raw_value'],graph_complete=view['graph_complete'],
        completed_route_order=routes,completed_route_set=sorted(routes),edge_activation=edge_activation,
        path_terminal_activation=sorted(terminals,key=lambda x:x['route']),outputs=selected)
