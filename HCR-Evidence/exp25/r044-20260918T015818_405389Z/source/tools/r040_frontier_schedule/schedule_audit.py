"""독립 scheduler 명세. 생산 scheduler.project/choose는 import하거나 호출하지 않는다."""
from copy import deepcopy
from .contracts import demand, digest


def expected_decision(core,policy):
    p=core['pending'];demand(p is not None and not p['ready'],'audit scheduler boundary')
    ids=[e['id'] for e in p['observation']['edges']]
    paths=[list(prefix['path']) for prefix in p['workspace']['frontier']]
    demand(policy in ('input_order','edge_id_min'),'audit scheduler name')
    demand(len(paths)<=32 and len(set(ids))==len(ids) and 1<=len(ids)<=8,'audit frontier/edge bound')
    demand(all(len(path)<=4 and all(type(i) is int and 0<=i<len(ids) for i in path) for path in paths),
           'audit scheduler slot/length')
    demand(len(set(map(tuple,paths)))==len(paths),'audit duplicate frontier')
    view=dict(schema='hcr-frontier-view-r040-v1',edge_ids=ids,frontier_paths=paths)
    if not paths: index=None;key=None;examined=reads=comparisons=0
    elif policy=='input_order':
        index=0;key=[ids[s] for s in paths[0]];examined=1;reads=len(paths[0]);comparisons=0
    else:
        # 생산 linear minimum과 달리 독립 정렬 명세로 선두를 결정한다.
        ordered=sorted((tuple(ids[s] for s in path),i) for i,path in enumerate(paths))
        key,index=ordered[0];key=list(key)
        examined=len(paths);reads=sum(len(path) for path in paths);comparisons=max(0,len(paths)-1)
    move=index is not None and index!=0
    result=dict(schema='hcr-frontier-choice-r040-v1',scheduler=policy,input_sha256=digest(view),
        selected_index=index,selected_path=None if index is None else paths[index],
        selected_edge_ids=key,priority_required=move,
        usage=dict(decision_calls=1,frontier_items_examined=examined,edge_id_reads=reads,
            key_comparisons=comparisons,priority_transitions=int(move),priority_match_scans=len(paths) if move else 0))
    return view,result


def check_transition(before,after,transition,decision):
    demand(decision['priority_required'] is True,'unsolicited priority transition')
    demand(transition['operation']=='prioritize_frontier' and
           transition['arguments']=={'path':decision['selected_path']},'priority operation/path')
    wanted=deepcopy(before);frontier=wanted['pending']['workspace']['frontier'];i=decision['selected_index']
    demand(type(i) is int and 0<i<len(frontier),'priority selected index')
    wanted['pending']['workspace']['frontier']=[frontier[i]]+frontier[:i]+frontier[i+1:]
    demand(after==wanted,'priority modified memory/observation/activation/cost or dropped a dependency')
