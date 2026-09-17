"""선택기에 전달할 공개 입력만 허용한다. 별도 정답·case 분류·원자료 위치는 제외한다."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
from math import isfinite
import re


class ContractError(ValueError):
    """계약 실패를 논리적 보류와 구별한다."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ContractError(message)


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Limits:
    max_ranked_paths: int = 64
    max_path_checks: int = 64
    max_edge_checks: int = 256
    max_proof_nodes: int = 128

    def __post_init__(self) -> None:
        require(all(type(v) is int and 0 <= v <= 100000 for v in asdict(self).values()),
                '선택 예산은 유한 범위의 비음수 정수여야 합니다.')


PUBLIC_FIELDS = {'schema', 'observation', 'raw_value', 'state', 'completed_paths',
                 'graph_complete', 'original_proof', 'min_abs_score'}
PROOF_FIELDS = {'nodes', 'final', 'primitive_depth', 'assumed_edges',
                'under_assumptions_valid', 'paths'}


def valid_id(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 128 and all(ord(c) >= 32 for c in value)


def validate(view: dict) -> None:
    require(isinstance(view, dict) and set(view) == PUBLIC_FIELDS, '공개 입력 필드 불일치/비공개 필드 혼입')
    require(view['schema'] == 'hcr-frozen-proof-view-r035-v1', '공개 입력 schema')
    require(type(view['raw_value']) in (bool, type(None)), 'raw_value 형식')
    require(type(view['graph_complete']) is bool, 'graph_complete 형식')
    obs = view['observation']
    require(isinstance(obs, dict) and set(obs) == {'episode_id', 'revision', 'start', 'goal', 'edges'}, '관측 필드')
    require(all(valid_id(obs[k]) for k in ('episode_id', 'start', 'goal')) and obs['start'] != obs['goal'], '관측 identity')
    require(type(obs['revision']) is int and obs['revision'] >= 0, '관측 revision')
    edges = obs['edges']
    require(isinstance(edges, list) and 1 <= len(edges) <= 8, 'EXP-15 edge 범위')
    for e in edges:
        require(isinstance(e, dict) and set(e) == {'id', 'source', 'target', 'score'}, 'edge 필드')
        require(all(valid_id(e[k]) for k in ('id', 'source', 'target')) and e['source'] != e['target'], 'edge identity')
        s = e['score']
        require(s is None or type(s) in (int, float) and isfinite(s) and -1 <= s <= 1, '관측 score')
    require(len({e['id'] for e in edges}) == len(edges), '중복 edge ID')
    require(len({(e['source'], e['target']) for e in edges}) == len(edges), '중복 edge 관계')
    vertices = {v for e in edges for v in (e['source'], e['target'])}
    require(obs['start'] in vertices and obs['goal'] in vertices, '관측 endpoint')
    paths = view['completed_paths']; state = view['state']
    require(isinstance(paths, list) and len(paths) <= 4 and all(isinstance(p, list) for p in paths), '경로 범위')
    require(all(all(type(s) is int and 0 <= s < len(edges) for s in p) for p in paths), '경로 slot 형식')
    require(len({tuple(p) for p in paths}) == len(paths), '중복 경로')
    require(isinstance(state, dict), 'state 형식')
    expected = {'e:' + str(i) for i in range(len(edges))} | {'goal'}
    for pi, path in enumerate(paths):
        require(1 <= len(path) <= 4, '경로 길이')
        cursor = obs['start']; seen = {cursor}
        for j, slot in enumerate(path):
            e = edges[slot]
            require(e['source'] == cursor and e['target'] not in seen, '경로 단절/순환')
            cursor = e['target']; seen.add(cursor); expected.add(f'p:{pi}:{j}')
        require(cursor == obs['goal'], '목표 미도달 경로')
    require(set(state) == expected or not paths and not state, 'state slot/관계 identity 불일치')
    require(all(type(x) in (int, float) and isfinite(x) and 0 <= x <= 1 for x in state.values()), 'activation 범위')
    t = view['min_abs_score']
    require(type(t) in (int, float) and isfinite(t) and 0 <= t < 1, '지지 threshold')
    proof = view['original_proof']
    require(isinstance(proof, dict) and set(proof) == PROOF_FIELDS, '원 proof 필드')
    require(type(proof['under_assumptions_valid']) is bool and isinstance(proof['nodes'], list), '원 proof 형식')
    require(isinstance(proof['assumed_edges'], list) and isinstance(proof['paths'], list), '원 proof 목록')
    require(len(proof['nodes']) <= 128, '원 proof 노드 범위')
    # 자세한 DAG 의미 검사는 독립 evaluator의 책임이다. malformed ID는 보정하지 않는다.
    for n in proof['nodes']:
        require(isinstance(n, dict) and set(n) == {'id', 'rule', 'edge_id', 'parents', 'path_index'}, 'proof 노드 필드')
        require(valid_id(n['id']) and isinstance(n['parents'], list) and all(valid_id(p) for p in n['parents']), 'proof 참조 형식')
        require(n['edge_id'] is None or n['edge_id'] in {e['id'] for e in edges}, '알 수 없는 proof edge')
        pi = n['path_index']
        require(pi is None or type(pi) is int and 0 <= pi < len(paths), 'proof path index')
    require(len({n['id'] for n in proof['nodes']}) == len(proof['nodes']), '중복 proof ID')
    require(all(isinstance(a, list) and len(a) == 2 and a[0] in {e['id'] for e in edges}
        and type(a[1]) is bool for a in proof['assumed_edges']), '가정 형식')
    require(len(dict(proof['assumed_edges'])) == len(proof['assumed_edges']), '중복 가정')
