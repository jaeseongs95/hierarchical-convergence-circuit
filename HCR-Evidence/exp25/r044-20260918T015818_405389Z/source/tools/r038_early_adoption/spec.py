"""native 결과를 보지 않고 정의한 유한 입력 집합. 유리한 case를 선별하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from .contracts import ARMS, Budget, SCOPES, SELECTION_LIMITS, require, validate_public_observation

BASE_COMMIT = 'd25f4bd4e3bd8c8aae763e3ee6542dbfd590900f'
R037_MANIFEST_BLOB = '68050e726232796f7c6a1f2be2d1a51f64a32442'
BASE_CASES = ('strong_positive', 'weak_negative', 'critical_missing', 'critical_zero',
              'irrelevant_missing', 'known_cut_missing', 'two_branch_cut', 'misleading_direction')


def conditions() -> dict:
    return dict(protocol='exp19-r038-early-adoption-v1', basis_commit=BASE_COMMIT,
        arms=list(ARMS), scopes=list(SCOPES), budget=asdict(Budget()),
        selection_limits=dict(SELECTION_LIMITS), baseline_case_count=8, new_case_count=6,
        native_trial_count=84, timing_intervention='posthoc_vs_online_support_first',
        posthoc_base_policy='native_saved', posthoc_only_at_current_terminal_readout=True,
        same_session_identity_across_arms=True, native_kernel_modified=False,
        new_case_grid=dict(distractor_lengths=[2, 3, 4], side_branch_orders=['early', 'late']),
        opportunity='raw_true_and_activation_eligible_supported_completed_path_and_frontier_nonempty',
        differential_opportunity_requires_native_abstention=True,
        opportunity_detection='independent_audit_only_not_controller_input',
        counterbalance='cyclic_arm_order_by_case_and_scope',
        comparison_unit='base_input; arm/prior/world/readout are paired, not independent tasks',
        automatic_retry=False, frozen_memory=True, observations_requested=False,
        prior_switch=False, restart=False, external_llm=False,
        support_is_external_truth=False, support_must_preserve_raw_value=True,
        correctness_required_for_audit=False, opportunity_required_for_audit=False,
        improvement_required_for_audit=False)


def structural_inventory(obs: dict) -> dict:
    """계획 단계의 topology 범위 검사. score/world/native 실행은 사용하지 않는다."""
    validate_public_observation(obs)
    paths, dead_lengths = [], []
    stack = [(obs['start'], (obs['start'],), ())]
    while stack:
        node, seen, path = stack.pop()
        if node == obs['goal']:
            paths.append(path)
            continue
        outgoing = [(i, e) for i, e in enumerate(obs['edges'])
                    if e['source'] == node and e['target'] not in seen]
        if not outgoing:
            dead_lengths.append(len(path))
        for i, e in reversed(outgoing):
            require(len(path) < 4, '미리 정한 primitive path 길이 4 초과')
            stack.append((e['target'], seen + (e['target'],), path + (i,)))
    require(0 < len(paths) <= 4, '완성 가능 topology 경로 수 범위')
    return dict(edges=len(obs['edges']), topology_paths=len(paths),
                path_lengths=sorted(map(len, paths)), dead_end_lengths=sorted(dead_lengths))


def new_cases() -> list[dict]:
    result = []
    for length in (2, 3, 4):
        for order in ('early', 'late'):
            # uncertainty prior가 큰 missing 가지를 직접 선택시키지 않는다.
            # 선택과 완성 순서는 native 엔진이 정하며 아래 순서는 공개 edge 배열 조건이다.
            branches = [('support', 2), ('missing', 2), ('distractor', length)]
            if order == 'late':
                branches = list(reversed(branches))
            edges, branch_slots = [], {}
            for label, n in branches:
                middle = {'support': 'a', 'missing': 'b', 'distractor': 'c'}[label]
                vertices = ['s'] + [middle + str(j) for j in range(n - 1)] + ['g']
                scores = ([.92] * n if label == 'support' else
                          [None] + [.92] * (n - 1) if label == 'missing' else
                          [-.92] + [.92] * (n - 1))
                branch_slots[label] = []
                for j, score in enumerate(scores):
                    eid = 'e' + str(len(edges)); branch_slots[label].append(eid)
                    edges.append(dict(id=eid, source=vertices[j], target=vertices[j+1], score=score))
            obs = dict(episode_id=f'exp19-input-{8+len(result):02d}', revision=0,
                       start='s', goal='g', edges=edges)
            worlds = {}
            for flag in (False, True):
                world = {e['id']: True for e in edges}
                world[branch_slots['missing'][0]] = flag
                world[branch_slots['distractor'][0]] = False
                worlds['missing_open' if flag else 'missing_closed'] = world
            result.append(dict(name=f'three_branch_l{length}_{order}', family='frontier_timing',
                cohort='new_topology', observation=obs, worlds=worlds,
                manipulation=dict(distractor_length=length, side_branch_order=order,
                                  expected_boundary_is_prediction_not_filter=True),
                topology=structural_inventory(obs)))
    return result


def cases_from_parent(old: list[dict]) -> list[dict]:
    require(tuple(c['name'] for c in old) == BASE_CASES, '기존 8개 입력의 순서/범위 불일치')
    result = []
    for c in old:
        result.append(dict(name=c['name'], family=c['family'], cohort='baseline_control',
            observation=deepcopy(c['observation']), worlds=deepcopy(c['worlds']),
            manipulation=None, topology=structural_inventory(c['observation'])))
    result.extend(new_cases())
    for c in result:
        ids = {e['id'] for e in c['observation']['edges']}
        require(c['worlds'] and all(set(w) == ids and all(type(t) is bool for t in w.values())
                                   for w in c['worlds'].values()), '평가 world contract')
    return result


def public_cases(cases: list[dict]) -> list[dict]:
    return [{k:deepcopy(c[k]) for k in ('name','family','cohort','observation','manipulation','topology')}
            for c in cases]


def trials(cases: list[dict]) -> list[dict]:
    rows = []
    for ci, case in enumerate(cases):
        for si, scope in enumerate(SCOPES):
            offset = (ci + si) % 3
            for arm in ARMS[offset:] + ARMS[:offset]:
                rows.append(dict(id=f't{len(rows):04d}', case=case['name'], scope=scope, arm=arm))
    return rows
