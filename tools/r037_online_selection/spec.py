"""EXP-17 이후의 최소 판별 실험. 성능 개선을 audit 성공 조건으로 강제하지 않는다."""
from dataclasses import asdict
from .contracts import Budget, POLICIES, SCOPES, SELECTION_LIMITS

BASE_COMMIT = 'b6b57589e18cc4be97cea10515f90ffbf100218f'
# 이 파일은 원격 b6b57589의 R036_MANIFEST.json을 LF 정규화한 Git blob SHA다.
R036_MANIFEST_BLOB = 'fa1000bedfc155c2fa4c8ef896fb611feb30ca1d'
CASE_NAMES = ('strong_positive', 'weak_negative', 'critical_missing', 'critical_zero',
              'irrelevant_missing', 'known_cut_missing', 'two_branch_cut', 'misleading_direction')


def conditions() -> dict:
    return dict(protocol='exp18-r037-online-proof-adoption-v1', basis_commit=BASE_COMMIT,
        scopes=list(SCOPES), policies=list(POLICIES), budget=asdict(Budget()),
        selection_limits=dict(SELECTION_LIMITS),
        intervention_boundary='after_native_readout_before_online_stop',
        selector_controls_stop=True, selector_changes_native_kernel=False,
        original_native_candidate_preserved=True, selected_proof_is_separate_adoption=True,
        same_raw_value_only=True, one_native_session_per_trial=True,
        same_session_identity_across_policy_pair=True,
        no_observations=True, no_restart=True, no_prior_switch=True,
        frozen_memory=True, retraining=False, automatic_retry=False,
        selection_budget_failure_stops=True,
        first_readout_and_terminal_pending_are_distinct=True,
        comparison_unit='base_case; scope/policy/readout/world are paired, not independent tasks',
        correctness_required_for_audit=False, improvement_required_for_audit=False,
        new_topology=False, representation_variants=False, external_llm=False)


def trials(cases: list[dict]) -> list[dict]:
    return [dict(id=f't{i:04d}', case=name, scope=scope, policy=policy)
            for i, (name, scope, policy) in enumerate(
                (c['name'], scope, policy) for c in cases for scope in SCOPES for policy in POLICIES)]
