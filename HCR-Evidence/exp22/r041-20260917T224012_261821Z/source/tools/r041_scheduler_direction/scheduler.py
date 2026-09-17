"""다음 frontier head 하나를 선택한다. 상태/ID/parent를 보정하거나 경로를 생성하지 않는다."""
from .contracts import SCHEDULERS, digest, require


def project(core):
    """기존 session의 공개 ID/등록된 경로만 노출한다. score·raw·world는 전달하지 않는다."""
    p=core['pending']
    require(p is not None and not p['ready'], 'running 경계에서만 scheduler를 호출합니다.')
    return dict(schema='hcr-frontier-view-r041-v1',
                edge_ids=[e['id'] for e in p['observation']['edges']],
                frontier_paths=[list(item['path']) for item in p['workspace']['frontier']])


def validate(view):
    require(type(view) is dict and set(view)=={'schema','edge_ids','frontier_paths'},
            'scheduler에 비등록 필드/score/world가 전달됐습니다.')
    require(view['schema']=='hcr-frontier-view-r041-v1','scheduler view schema')
    ids=view['edge_ids'];paths=view['frontier_paths']
    require(type(ids) is list and 1<=len(ids)<=8 and all(type(x) is str and 0<len(x)<=128 for x in ids)
            and len(set(ids))==len(ids),'scheduler edge ID inventory')
    require(type(paths) is list and len(paths)<=32,'scheduler frontier bound')
    require(all(type(p) is list and len(p)<=4 and all(type(i) is int and 0<=i<len(ids) for i in p) for p in paths),
            'scheduler path slot/length')
    require(len({tuple(p) for p in paths})==len(paths),'duplicate frontier path; no host correction')


def choose(view,policy):
    validate(view);require(policy in SCHEDULERS,'미등록 scheduler')
    ids=view['edge_ids'];paths=view['frontier_paths']
    selected=None;key=None;examined=reads=comparisons=0
    if paths and policy=='input_order':
        selected=0;key=tuple(ids[s] for s in paths[0]);examined=1;reads=len(paths[0])
    elif paths:
        for index,path in enumerate(paths):
            candidate=tuple(ids[s] for s in path)
            examined+=1;reads+=len(path)
            if selected is None: selected,key=index,candidate
            else:
                comparisons+=1
                if (candidate < key if policy=='edge_id_min' else candidate > key):
                    selected,key=index,candidate
    moved=selected is not None and selected!=0
    return dict(schema='hcr-frontier-choice-r041-v1',scheduler=policy,input_sha256=digest(view),
        selected_index=selected,selected_path=None if selected is None else list(paths[selected]),
        selected_edge_ids=None if key is None else list(key),priority_required=moved,
        usage=dict(decision_calls=1,frontier_items_examined=examined,edge_id_reads=reads,
                   key_comparisons=comparisons,priority_transitions=int(moved),
                   priority_match_scans=len(paths) if moved else 0))
