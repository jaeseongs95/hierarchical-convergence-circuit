"""선택 경계의 명시적 일대일 재표현. raw candidate를 덮어쓰거나 ID를 자동 보정하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from itertools import product
import re
from .contracts import digest, require, validate


def variants() -> list[dict]:
    return [dict(id='v'+''.join(map(str, bits)), node_alias=bool(bits[0]), edge_alias=bool(bits[1]),
                 edge_reverse=bool(bits[2]), path_reverse=bool(bits[3])) for bits in product((0, 1), repeat=4)]


def transform(view: dict, variant: dict) -> dict:
    validate(view)
    require(variant in variants(), '미등록 재표현 조건')
    obs = view['observation']; paths = view['completed_paths']; original_hash = digest(view)
    vertices = sorted({n for e in obs['edges'] for n in (e['source'], e['target'])})
    ids = sorted(e['id'] for e in obs['edges'])
    nm = {name: f'n_{len(vertices)-1-i:03d}' if variant['node_alias'] else name for i, name in enumerate(vertices)}
    em = {name: f'q_{len(ids)-1-i:03d}' if variant['edge_alias'] else name for i, name in enumerate(ids)}
    eo = list(range(len(obs['edges']))); po = list(range(len(paths)))
    if variant['edge_reverse']: eo.reverse()
    if variant['path_reverse']: po.reverse()
    es = {old: new for new, old in enumerate(eo)}; ps = {old: new for new, old in enumerate(po)}
    target = deepcopy(view)
    target['observation'] = dict(episode_id=obs['episode_id'], revision=obs['revision'],
        start=nm[obs['start']], goal=nm[obs['goal']], edges=[dict(id=em[obs['edges'][i]['id']],
            source=nm[obs['edges'][i]['source']], target=nm[obs['edges'][i]['target']],
            score=obs['edges'][i]['score']) for i in eo])
    target['completed_paths'] = [[es[s] for s in paths[i]] for i in po]
    state = {}
    for name, value in view['state'].items():
        if name.startswith('e:'): new_name = 'e:'+str(es[int(name[2:])])
        elif name.startswith('p:'):
            _, i, j = name.split(':'); new_name = f'p:{ps[int(i)]}:{j}'
        else: new_name = name
        require(new_name not in state, '재표현 state 충돌'); state[new_name] = value
    target['state'] = state
    p = target['original_proof']
    for n in p['nodes']:
        if n['edge_id'] is not None: n['edge_id'] = em[n['edge_id']]
        if n['path_index'] is not None: n['path_index'] = ps[n['path_index']]
    p['assumed_edges'] = sorted([[em[e], t] for e, t in p['assumed_edges']])
    if p['paths']: p['paths'] = [[em[e] for e in view['original_proof']['paths'][i]] for i in po]
    # proof의 node ID/parent ID는 opaque identity다. 문자열 안 숫자를 임의로 고치지 않는다.
    validate(target); require(original_hash == digest(view), '원 상태 수정')
    return dict(schema='hcr-frozen-transform-r035-v1', variant=deepcopy(variant), source_input_sha256=original_hash,
        maps=dict(node_names=nm, edge_names=em, edge_new_to_old=eo, path_new_to_old=po), input=target,
        boundary='post_readout_selector_only')
