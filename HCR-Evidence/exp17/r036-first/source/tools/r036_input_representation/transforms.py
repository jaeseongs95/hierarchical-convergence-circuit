"""공개 입력만 일대일 변환한다. 실행 결과의 ID/경로/activation을 고치지 않는다."""
from __future__ import annotations
from copy import deepcopy
from math import isfinite
from r035_frozen_selection.contracts import digest, require
from .spec import variants


def validate_observation(obs: dict) -> None:
    require(isinstance(obs,dict) and set(obs)=={'episode_id','revision','start','goal','edges'},'공개 observation 필드')
    def ident(v):
        return isinstance(v,str) and 0<len(v)<=128 and all(ord(c)>=32 for c in v)
    require(all(ident(obs[k]) for k in ('episode_id','start','goal')) and obs['start']!=obs['goal'],'입력 identity')
    require(type(obs['revision']) is int and obs['revision']>=0,'입력 revision')
    edges=obs['edges']; require(isinstance(edges,list) and 1<=len(edges)<=8,'R036 edge 범위')
    for e in edges:
        require(isinstance(e,dict) and set(e)=={'id','source','target','score'},'edge 필드')
        require(all(ident(e[k]) for k in ('id','source','target')) and e['source']!=e['target'],'edge identity')
        x=e['score']
        require(x is None or type(x) in (int,float) and isfinite(x) and -1<=x<=1,'관측 score')
    require(len({e['id'] for e in edges})==len(edges) and len({(e['source'],e['target']) for e in edges})==len(edges),'edge 중복')
    nodes={n for e in edges for n in (e['source'],e['target'])}
    require({obs['start'],obs['goal']}<=nodes and len(nodes)<=len(edges)+1,'입력 node 범위')


def transform_input(obs: dict, variant: dict) -> dict:
    validate_observation(obs)
    require(variant in variants() and all(type(variant[k]) is bool for k in ('node_alias','edge_alias','edge_reverse')),
            '등록되지 않은 입력 재표현')
    before=digest(obs)
    names=sorted({n for e in obs['edges'] for n in (e['source'],e['target'])})
    ids=sorted(e['id'] for e in obs['edges'])
    nm={n:f'n_{len(names)-1-i:03d}' if variant['node_alias'] else n for i,n in enumerate(names)}
    em={n:f'q_{len(ids)-1-i:03d}' if variant['edge_alias'] else n for i,n in enumerate(ids)}
    order=list(range(len(obs['edges'])))
    if variant['edge_reverse']:order.reverse()
    changed=dict(episode_id=obs['episode_id'],revision=obs['revision'],start=nm[obs['start']],goal=nm[obs['goal']],
        edges=[dict(id=em[obs['edges'][j]['id']],source=nm[obs['edges'][j]['source']],
                    target=nm[obs['edges'][j]['target']],score=obs['edges'][j]['score']) for j in order])
    validate_observation(changed); require(digest(obs)==before,'원 입력 변경')
    return dict(schema='hcr-input-transform-r036-v1',boundary='before_native_begin',variant=deepcopy(variant),
        source_observation_sha256=before,observation=changed,
        maps=dict(node_names=nm,edge_names=em,edge_new_to_old=order))
