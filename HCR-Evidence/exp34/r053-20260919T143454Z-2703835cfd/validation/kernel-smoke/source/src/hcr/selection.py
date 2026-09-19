"""R0.3.4: 이미 생성된 양성 경로의 증명 선택을 별도 개입으로 수행한다.

기존 decision/activation/finish/grounding을 수정하지 않는다. 현재 raw 값이 True인
경우에만, 기존 활성 상태와 관측 부호가 함께 지지하는 경로를 새 proof로 만든다.
새 경로 탐색, 참값 조회, 반대 값 생성, 학습은 이 모듈에 없다.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from math import isfinite
from time import perf_counter


class SelectionContractError(ValueError):
    """측정/계약 실패. task의 오답 또는 보류와 구분한다."""


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SelectionContractError(message)


@dataclass(frozen=True)
class SelectionLimits:
    """rollout 전체 예산. 호출마다 초기화하면 안 된다. CPU 명령 수와는 다르다."""
    max_ranked_paths: int = 64
    max_path_checks: int = 64
    max_edge_checks: int = 256
    max_proof_nodes: int = 128

    def __post_init__(self) -> None:
        for k, v in asdict(self).items():
            require(type(v) is int and 0 <= v <= 100000, 'invalid selection budget: ' + k)


def empty_usage() -> dict:
    return dict(ranked_paths=0, path_checks=0, edge_checks=0, proof_nodes=0)


def validate_view(view: dict) -> None:
    expected = {'schema', 'source_candidate_id', 'source_reference', 'source_decision_sha256',
        'source_packet_sha256', 'observation', 'observation_digest', 'raw_value',
        'state', 'completed_paths', 'graph_complete', 'original_proof', 'min_abs_score'}
    require(isinstance(view, dict) and set(view) == expected, 'selection view fields')
    require(view['schema'] == 'hcr-selection-view-r034-v1', 'selection view schema')
    require(type(view['raw_value']) in (bool, type(None)), 'raw value must be bool or None')
    require(type(view['graph_complete']) is bool, 'graph_complete type')
    require(isinstance(view['source_candidate_id'], str) and view['source_candidate_id'], 'source candidate')
    ref = view['source_reference']
    require(isinstance(ref, dict) and set(ref) == {'segment', 'generation', 'ready_sha256', 'finished_sha256'}, 'source reference fields')
    require(all(type(ref[k]) is int and ref[k] >= 0 for k in ('segment', 'generation')), 'source reference coordinates')
    for h in (view['source_decision_sha256'], view['source_packet_sha256'],
              view['observation_digest'], ref['ready_sha256'], ref['finished_sha256']):
        require(isinstance(h, str) and len(h) == 64 and all(c in '0123456789abcdef' for c in h), 'digest format')
    require(ref['finished_sha256'] == view['source_packet_sha256'], 'finished source mismatch')
    require(view['source_candidate_id'] == 'review-candidate-' + digest(ref), 'source candidate identity')
    obs = view['observation']
    require(isinstance(obs, dict) and set(obs) == {'episode_id', 'revision', 'start', 'goal', 'edges'}, 'public observation fields')
    require(digest(obs) == view['observation_digest'], 'observation digest mismatch')
    require(type(obs['revision']) is int and obs['revision'] >= 0, 'revision type')
    require(all(isinstance(obs[k], str) and obs[k] for k in ('episode_id', 'start', 'goal')), 'observation identifiers')
    require(isinstance(obs['edges'], list) and len(obs['edges']) <= 4096, 'edge bound')
    ids = set()
    for edge in obs['edges']:
        require(isinstance(edge, dict) and set(edge) == {'id', 'source', 'target', 'score'}, 'edge fields')
        require(all(isinstance(edge[k], str) and edge[k] for k in ('id', 'source', 'target')), 'edge identifiers')
        require(edge['id'] not in ids, 'duplicate edge identity')
        ids.add(edge['id'])
        s = edge['score']
        require(s is None or type(s) in (int, float) and isfinite(s) and -1 <= s <= 1, 'observation score')
    state = view['state']
    require(isinstance(state, dict) and all(isinstance(k, str) and type(v) in (float, int)
        and isfinite(v) and 0 <= v <= 1 for k, v in state.items()), 'activation state')
    paths = view['completed_paths']
    require(isinstance(paths, list) and len(paths) <= 4096, 'completed path bound')
    require(all(isinstance(p, list) for p in paths), 'path type')
    require(len({tuple(p) for p in paths}) == len(paths), 'duplicate completed path')
    for pi, path in enumerate(paths):
        require(path and all(type(s) is int and 0 <= s < len(obs['edges']) for s in path), 'path slot')
        cursor = obs['start']; seen = {cursor}
        for slot in path:
            edge = obs['edges'][slot]
            require(edge['source'] == cursor and edge['target'] not in seen, 'non-contiguous or cyclic path')
            cursor = edge['target']; seen.add(cursor)
            require(f'e:{slot}' in state, 'missing edge activation')
        require(cursor == obs['goal'], 'path does not reach goal')
        require(f'p:{pi}:{len(path)-1}' in state, 'missing terminal activation')
    threshold = view['min_abs_score']
    require(type(threshold) in (float, int) and isfinite(threshold) and 0 <= threshold < 1, 'support threshold')
    require(isinstance(view['original_proof'], dict), 'original proof type')


def project_candidate(candidate: dict) -> dict:
    """감사 가능한 finish candidate에서 공개 선택 입력만 추출한다.

    해시/계보 결속을 검사한다. 수치 recurrence의 독립 검산을 대체하지 않는다.
    EXP-15 evaluator는 별도로 기존 session auditor를 호출한다.
    """
    require(isinstance(candidate, dict), 'candidate type')
    packet = candidate['packet']; doc = packet['document']; decision = candidate['decision']
    require(digest(doc) == packet['sha256'], 'source packet checksum')
    require(candidate['reference']['finished_sha256'] == packet['sha256'], 'source finish binding')
    require(candidate['candidate_id'] == 'review-candidate-' + digest(candidate['reference']), 'source id binding')
    events = doc['events']
    require(events and events[-1]['event'] == 'r02_decision' and events[-1]['payload'] == decision, 'source decision event')
    starts = [e['payload'] for e in events if e['event'] == 'r02_attempt_started'
              and e['payload']['decision_id'] == decision['id']]
    require(len(starts) == 1, 'source observation start')
    obs = starts[0]['observation']
    require(decision['observation_digest'] == digest(obs) and decision['episode_id'] == obs['episode_id']
        and decision['observation_revision'] == obs['revision'], 'observation/decision binding')
    nets = [e['payload'] for e in events if e['event'] == 'r02_network'
            and e['payload']['kind'] == 'decision' and e['payload']['decision_id'] == decision['id']]
    paths = decision['expanded_paths']
    if nets:
        net = nets[-1]
        require(digest(net['program']) == decision['program_digest'] == net['program_digest'], 'source program')
        require(paths == net['program']['paths'] == [r['path'] for r in net['metadata']['routes']], 'generated route binding')
    else:
        require(not paths and decision['program_digest'] is None, 'path without source network')
    require(candidate['diagnostic']['source']['decision_sha256'] == digest(decision), 'diagnostic source')
    require(len(dict(decision['state'])) == len(decision['state']), 'duplicate state identity')
    view = dict(schema='hcr-selection-view-r034-v1', source_candidate_id=candidate['candidate_id'],
        source_reference=deepcopy(candidate['reference']), source_decision_sha256=digest(decision),
        source_packet_sha256=packet['sha256'], observation=deepcopy(obs), observation_digest=digest(obs),
        raw_value=decision['value'], state=dict(decision['state']), completed_paths=deepcopy(paths),
        graph_complete=decision['graph_complete'], original_proof=deepcopy(decision['proof']),
        min_abs_score=candidate['diagnostic']['contract']['min_abs_score'])
    validate_view(view)
    return view


def select_supported(view: dict, limits: SelectionLimits | None = None,
                     used: dict | None = None) -> dict:
    """활성도 순위를 유지하되 현재 관측도 지지하는 첫 기존 경로를 선택한다.

    True 이외의 raw 값을 뒤집지 않는다. 예산 부족은 실패를 감추지 않는 보류다.
    선택 입력 검증/정렬/증명 생성의 시간은 wall_seconds에 포함된다. counters는
    명시한 작업의 inventory이며 전체 CPU 연산량이나 에너지의 추정값이 아니다.
    """
    started = perf_counter()
    validate_view(view)
    limits = limits or SelectionLimits()
    require(isinstance(limits, SelectionLimits), 'typed selection limits')
    before = deepcopy(used) if used is not None else empty_usage()
    require(set(before) == set(empty_usage()) and all(type(x) is int and x >= 0 for x in before.values()), 'selection usage')
    cap = asdict(limits)
    require(all(before[k] <= cap['max_' + k] for k in before), 'previous usage exceeds budget')
    delta = empty_usage(); checks = []; selected = None; proof = None
    reason = 'raw_value_not_true'
    paths = view['completed_paths']; obs = view['observation']; state = view['state']
    def affordable(name: str, n: int) -> bool:
        return before[name] + delta[name] + n <= cap['max_' + name]
    if view['raw_value'] is True:
        if not affordable('ranked_paths', len(paths)):
            reason = 'selection_ranking_budget'
        else:
            delta['ranked_paths'] = len(paths)
            order = sorted(range(len(paths)), key=lambda i: (-state[f'p:{i}:{len(paths[i])-1}'], i))
            reason = 'no_supported_existing_path'
            for pi in order:
                path = paths[pi]
                if not affordable('path_checks', 1) or not affordable('edge_checks', len(path)):
                    reason = 'selection_scan_budget'; break
                delta['path_checks'] += 1; delta['edge_checks'] += len(path)
                active = all(state[f'e:{s}'] >= .5 for s in path)
                supported = all(obs['edges'][s]['score'] is not None
                    and obs['edges'][s]['score'] > view['min_abs_score'] for s in path)
                checks.append(dict(path_index=pi, slots=list(path), activation_eligible=active,
                                   observation_supported=supported))
                if not (active and supported):
                    continue
                if not affordable('proof_nodes', 2 * len(path)):
                    reason = 'selection_proof_budget'; break
                nodes = []; assumptions = []; previous = None
                for j, slot in enumerate(path):
                    fid = f'f:{slot}:1'; rid = f'r:{pi}:{j}'; edge_id = obs['edges'][slot]['id']
                    nodes.append(dict(id=fid, rule='assumed_open', edge_id=edge_id, parents=[], path_index=None))
                    nodes.append(dict(id=rid, rule='start_edge' if j == 0 else 'extend_path', edge_id=None,
                        parents=[fid] if j == 0 else [previous, fid], path_index=pi))
                    assumptions.append([edge_id, True]); previous = rid
                proof = dict(nodes=nodes, final=previous, primitive_depth=len(path),
                    assumed_edges=sorted(assumptions), under_assumptions_valid=True,
                    paths=[[obs['edges'][s]['id'] for s in p] for p in paths])
                delta['proof_nodes'] = len(nodes); selected = pi; reason = 'supported_existing_positive_path'; break
    after = {k: before[k] + delta[k] for k in before}
    body = dict(schema='hcr-proof-selection-r034-v1', policy='support_first_same_value',
        source_candidate_id=view['source_candidate_id'], source_view_sha256=digest(view),
        source_reference=deepcopy(view['source_reference']), source_decision_sha256=view['source_decision_sha256'],
        source_packet_sha256=view['source_packet_sha256'], limits=cap, usage_before=before,
        usage_delta=delta, usage_after=after, path_checks=checks, selected_path_index=selected,
        proof=proof, value=True if selected is not None else None, accepted=selected is not None,
        reason=reason, boundaries=dict(original_decision_modified=False, activation_modified=False,
            new_paths_generated=False, hidden_truth_accessed=False, learned_memory_modified=False,
            value_flip_allowed=False, explicit_proof_selection_intervention=True,
            counters_are_full_cpu_cost=False))
    body['candidate_id'] = 'selection-candidate-' + digest(body)
    body['wall_seconds'] = perf_counter() - started
    return body
