"""평가 전용 ID 기반 궤적. 모델 입력·state·parent reference를 수정하지 않는다."""
from copy import deepcopy
from r038_early_adoption.audit import candidate_view
from .contracts import demand, digest


def id_path(observation,path):
    edges=observation['edges']
    demand(isinstance(path,(list,tuple)) and all(type(i) is int and 0<=i<len(edges) for i in path),
           'slot 대응 실패; 추측/보정하지 않습니다.')
    return [edges[i]['id'] for i in path]


def aligned_state(view):
    obs=view['observation'];paths=view['completed_paths'];state=view['state']
    if not state:
        demand(not paths,'완성 경로가 있는데 state가 없음')
        return dict(edges=[],prefixes=[],goal=None)
    edge_states=sorted([[edge['id'],state[f'e:{i}']] for i,edge in enumerate(obs['edges'])])
    prefix_states=[]
    for i,path in enumerate(paths):
        ids=id_path(obs,path)
        for j in range(len(path)):
            # 동일 prefix가 서로 다른 route에 인스턴스화되어도 합치지 않는다.
            prefix_states.append(dict(route=ids,prefix=ids[:j+1],activation=state[f'p:{i}:{j}']))
    prefix_states.sort(key=lambda x:(x['route'],x['prefix']))
    return dict(edges=edge_states,prefixes=prefix_states,goal=state['goal'])


def completion_trace(base):
    doc=base['packet']['document'];obs=doc['engine']['pending']['observation']
    completed=[];expansion=0;known=set()
    for event in doc['events']:
        if event['event'] in ('r02_expansion','r02_dead_end'):
            expansion+=1
        if event['event']=='r02_expansion':
            for prefix in event['payload']['added']:
                if prefix['visited'][-1]!=obs['goal']:continue
                path=id_path(obs,prefix['path']);key=tuple(path)
                demand(key not in known,'중복 completed path event')
                known.add(key)
                completed.append(dict(rank=len(completed)+1,expansion=expansion,
                                      event_seq=event['seq'],path_edge_ids=path))
    return completed


def describe(run,report,case,*,view_of=candidate_view):
    base=run['base'];obs=case['observation'];readouts=[]
    demand(len(base['candidates'])==len(report['readouts']),'readout inventory')
    for candidate,row in zip(base['candidates'],report['readouts']):
        view=view_of(candidate)
        demand(digest(view['observation'])==digest(obs),'readout observation/array 변경')
        paths=[id_path(obs,p) for p in view['completed_paths']]
        first_native=row['native_assumptions']
        selected=row['selected_assumptions']
        readouts.append(dict(ordinal=row['ordinal'],ticks=row['kernel_ticks_at_readout'],
            raw_value=row['raw_value'],native_accepted=row['native_accepted'],
            policy_accepted=row['policy_accepted'],graph_complete=row['graph_complete'],
            frontier_count=row['frontier_count'],completed_paths_edge_ids=paths,
            native_assumptions_edge_ids=deepcopy(first_native),selected_assumptions_edge_ids=deepcopy(selected),
            native_D_DAG=row['native_D_DAG'],policy_D_DAG=row['D_DAG'],
            supported_completed_edge_ids=[paths[i] for i in row['supported_completed']],
            activation_eligible_supported_edge_ids=[paths[i] for i in row['activation_eligible_supported']],
            supported_positive_available=row['supported_positive_available'],
            supported_frontier_opportunity=row['supported_frontier_opportunity'],
            differential_opportunity=row['differential_opportunity'],id_aligned_state=aligned_state(view)))
    trace=completion_trace(base)
    # 완성 event의 순서와 마지막 실제 readout의 목록이 항상 같을 필요는 없다(예산 종료).
    terminal=base['packet']['document']['engine']['pending']
    route_ids=[id_path(obs,p['path']) for p in terminal['workspace']['routes']]
    demand([r['path_edge_ids'] for r in trace]==route_ids,'완성 event/terminal workspace 불일치')
    def first(predicate):
        item=next((r for r in readouts if predicate(r)),None)
        return None if item is None else dict(ordinal=item['ordinal'],ticks=item['ticks'],frontier_count=item['frontier_count'])
    support_rank=next((r['rank'] for r in trace if r['path_edge_ids']==['e0','e1']),None)
    return dict(branch_order=case['manipulation']['branch_order'],
        observation_sha256=digest(obs),edge_id_order=[e['id'] for e in obs['edges']],
        completion_trace=trace,support_route_completion_rank=support_rank,
        first_supported_completed_readout=first(lambda r:bool(r['supported_completed_edge_ids'])),
        first_supported_available_readout=first(lambda r:r['supported_positive_available']),
        first_differential_readout=first(lambda r:r['differential_opportunity']),
        readouts=readouts,terminal_completed_paths_edge_ids=route_ids,
        terminal_frontier_paths_edge_ids=[id_path(obs,p['path']) for p in terminal['workspace']['frontier']],
        mapping_boundary='independent_evaluator_only',production_state_modified=False)
