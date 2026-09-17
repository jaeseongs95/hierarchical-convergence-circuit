"""EXP20의 동일 입력 6개를 재사용한다. 스케줄링 효과로 case를 선별하지 않는다."""
from dataclasses import asdict
from r039_order_isolation.spec import make_cases, public_cases, ORDERS
from .contracts import ARMS, SCOPES, SCHEDULERS, BASE_COMMIT, Budget, SELECTION_LIMITS


def conditions():
    return dict(protocol='exp21-r040-frontier-scheduler-v1',basis_commit=BASE_COMMIT,
        arms=list(ARMS),scopes=list(SCOPES),schedulers=list(SCHEDULERS),
        budget=asdict(Budget()),selection_limits=dict(SELECTION_LIMITS),
        native_trial_count=72,base_topology_count=1,order_variant_count=6,
        branch_orders=list(ORDERS),input_intervention='same_EXP20_fixed_identity_permutations',
        scheduling_boundary='before_each_affordable_running_advance',
        scheduling_key='lexicographic_tuple_of_existing_frontier_path_edge_IDs',
        scheduling_tie='duplicate_path_is_contract_failure_not_repaired',
        scheduling_action='prioritize_frontier_only_if_selected_index_is_not_zero',
        full_frontier_sort=False,first_candidate_pool_policy_modified=False,
        raw_or_scores_or_worlds_passed_to_scheduler=False,
        scheduler_public_fields=['schema','edge_ids','frontier_paths'],
        existing_native_API='AdaptiveSession.prioritize_frontier',
        native_kernel_modified=False,native_source_modified=False,
        native_schema='existing_replayable_prioritize_frontier_transition',
        same_session_identity_across_arms_and_schedulers=True,
        automatic_retry=False,frozen_memory=True,observations_requested=False,
        prior_switch=False,restart=False,external_llm=False,
        support_must_preserve_raw_value=True,support_is_external_truth=False,
        correctness_required_for_audit=False,improvement_required_for_audit=False,
        order_gap_reduction_required_for_audit=False,
        counterbalance='cyclic_six_scheduler_arm_cells_by_permutation_and_scope',
        comparison_unit='one_fixed_topology; order/prior/arm/scheduler/world/readout are paired',
        scheduler_cost_unit='inventory_not_full_CPU_operations; separate_from_native_ticks',
        sorted_ID_is_not_claimed_optimal=True)


def trials(cases):
    cells=[(scheduler,arm) for scheduler in SCHEDULERS for arm in ARMS]
    result=[]
    for ci,case in enumerate(cases):
        for si,scope in enumerate(SCOPES):
            shift=(ci+si)%len(cells)
            for scheduler,arm in cells[shift:]+cells[:shift]:
                result.append(dict(id=f't{len(result):04d}',case=case['name'],scope=scope,
                                   arm=arm,scheduler=scheduler))
    return result
