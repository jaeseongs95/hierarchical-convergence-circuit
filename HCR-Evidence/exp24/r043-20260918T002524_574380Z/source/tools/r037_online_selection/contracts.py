"""실험 제어 계약. 외부 정답을 실행기 인자로 전달하지 않는다."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
from math import isfinite


class ContractError(ValueError):
    """논리적 보류가 아닌 입력/실행 계약 위반."""


class AuditError(ValueError):
    """독립 검산 불일치. 정답 여부와 별개다."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ContractError(message)


def demand(ok: bool, message: str) -> None:
    if not ok:
        raise AuditError(message)


def digest(value: object) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def finite_nonnegative(value: object) -> bool:
    return type(value) in (int, float) and isfinite(value) and value >= 0


@dataclass(frozen=True)
class Budget:
    max_initial_advances: int = 64
    max_initial_kernel_ticks: int = 65536
    max_extra_advances: int = 8
    max_extra_kernel_ticks: int = 2048

    def __post_init__(self) -> None:
        ceilings = {'max_initial_advances': 128, 'max_initial_kernel_ticks': 100000,
                    'max_extra_advances': 128, 'max_extra_kernel_ticks': 100000}
        for key, value in asdict(self).items():
            require(type(value) is int and 0 <= value <= ceilings[key], '계산 예산: ' + key)


SELECTION_LIMITS = dict(max_ranked_paths=64, max_path_checks=64,
                        max_edge_checks=256, max_proof_nodes=128)
SCOPES = ('legacy', 'route_only')
POLICIES = ('native_saved', 'support_first')
SELECTION_BUDGET_REASONS = ('ranking_budget', 'scan_budget', 'proof_budget')
USAGE_KEYS = ('ranked_paths', 'path_checks', 'edge_checks', 'proof_nodes_created',
              'proof_nodes_reused', 'gate_assumptions_checked')


def validate_public_observation(obs: dict) -> None:
    require(isinstance(obs, dict) and set(obs) == {'episode_id', 'revision', 'start', 'goal', 'edges'},
            '관측 외의 case/world/정답 필드를 실행기에 전달할 수 없습니다.')
    for key in ('episode_id', 'start', 'goal'):
        require(isinstance(obs[key], str) and 0 < len(obs[key]) <= 128, '관측 identity: ' + key)
    require(obs['start'] != obs['goal'], '동일 endpoint')
    require(type(obs['revision']) is int and obs['revision'] >= 0, '관측 revision')
    require(isinstance(obs['edges'], list) and 1 <= len(obs['edges']) <= 8, '기존 selector의 edge 범위')
    seen_ids, seen_pairs, nodes = set(), set(), set()
    for edge in obs['edges']:
        require(isinstance(edge, dict) and set(edge) == {'id', 'source', 'target', 'score'}, 'edge 필드')
        require(all(isinstance(edge[k], str) and 0 < len(edge[k]) <= 128 for k in ('id', 'source', 'target')),
                'edge identity')
        require(edge['source'] != edge['target'], '자기 loop')
        score = edge['score']
        require(score is None or type(score) in (float, int) and isfinite(score) and -1 <= score <= 1,
                'score는 null 또는 [-1,1] 유한 수여야 합니다.')
        pair = (edge['source'], edge['target'])
        require(edge['id'] not in seen_ids and pair not in seen_pairs, '중복 edge')
        seen_ids.add(edge['id']); seen_pairs.add(pair); nodes.update(pair)
    require(obs['start'] in nodes and obs['goal'] in nodes, '관측 endpoint 누락')
