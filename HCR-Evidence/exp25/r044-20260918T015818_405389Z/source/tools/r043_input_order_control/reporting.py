"""Paired negative-control outcomes; an observed difference never becomes an audit failure."""
from r042_id_role_isolation.reporting import csv_text
from .storage import digest, require

ORDERS = ('SMD','SDM','MSD','MDS','DSM','DMS')


def comparable(left, right):
    return None if left is None or right is None else digest(left) == digest(right)


def outcome(record):
    f = record['final']
    return (f['accepted'],f['value'],record['classification'],f['reason'])


def first_readout_difference(a, b):
    if not a or not b:
        return dict(comparable=False, reason='missing_readout',ordinal=None,fields=None)
    for i in range(max(len(a),len(b))):
        if i >= min(len(a),len(b)):
            return dict(comparable=True,reason='readout_count',ordinal=i,fields=['readout_present'])
        keys = sorted(set(a[i]) | set(b[i]))
        changed = [k for k in keys if k not in a[i] or k not in b[i] or digest(a[i][k]) != digest(b[i][k])]
        if changed:
            return dict(comparable=True,reason='measured_readout_difference',ordinal=i,fields=changed)
    return dict(comparable=True,reason='equal',ordinal=None,fields=[])


def cost_vector(record):
    # Each unit has its own key. Missing or placeholder measurements never become zero.
    result = {'native_kernel_ticks':record['usage']['native_kernel_ticks']}
    result.update({'scheduler.'+k:v for k,v in record['scheduler_usage'].items()})
    result.update({'online_selection.'+k:v for k,v in record['usage']['online_selection'].items()})
    result.update({'native_cost.'+k:v for k,v in record.get('native_cost',{}).items()
                   if k != 'wall_seconds'})
    return result


def summarize(records):
    require(len(records) == 12, 'EXP24 requires exactly 12 native records')
    cells = {(r['id_variant'],r['branch_order'],r['trial']['scheduler']):r for r in records}
    require(set(cells) == {(v,o,'input_order') for o in ORDERS for v in ('identity','swap_SD')},
            'duplicate or missing EXP24 cells')
    comparisons, differences = [], []
    for order in ORDERS:
        a,b = (cells[(v,order,'input_order')] for v in ('identity','swap_SD'))
        da,db = a['diagnostics'],b['diagnostics']
        ta,tb = a['usage']['native_kernel_ticks'],b['usage']['native_kernel_ticks']
        require(type(ta) is int and type(tb) is int and ta >= 0 and tb >= 0, 'native ticks are measured integer counts')
        divergence = first_readout_difference(da['canonical_readouts'],db['canonical_readouts'])
        ca,cb = cost_vector(a),cost_vector(b)
        for key in sorted(set(ca) | set(cb)):
            x,y = ca.get(key),cb.get(key)
            require(x is None or type(x) in (int,float), 'non-numeric cost')
            require(y is None or type(y) in (int,float), 'non-numeric cost')
            differences.append(dict(branch_order=order,metric=key,identity=x,swap_SD=y,
                swap_minus_identity=None if x is None or y is None else y-x,
                equal=None if x is None or y is None else x == y))
        scope = [r for r in differences if r['branch_order'] == order]
        p = dict(branch_order=order,identity_trial=a['trial']['id'],swap_trial=b['trial']['id'],
            identity_native_ticks=ta,swap_native_ticks=tb,swap_minus_identity_ticks=tb-ta,
            native_ticks_equal=ta == tb,outcome_equal=outcome(a) == outcome(b),
            canonical_completion_equal=comparable(da['canonical_completion_sha256'],db['canonical_completion_sha256']),
            canonical_readout_trajectory_equal=(None if not divergence['comparable'] else divergence['reason'] == 'equal'),
            final_support_signature_equal=comparable(da['final_support_signature'],db['final_support_signature']),
            completed_path_inventory_equal=comparable(da['completed_path_inventory'],db['completed_path_inventory']),
            legacy_final_proof_projection_equal=comparable(da['final_proof_projection'],db['final_proof_projection']),
            minimal_goal_proof_DAG_isomorphism=None,
            first_readout_difference=divergence,
            scheduler_usage_equal=digest(a['scheduler_usage']) == digest(b['scheduler_usage']),
            scheduler_slot_trajectory_equal=digest([{k:v for k,v in row.items() if k != 'selected_native_IDs'}
                for row in a['input_order_policy_audit']['slot_decisions']]) == digest(
                [{k:v for k,v in row.items() if k != 'selected_native_IDs'}
                for row in b['input_order_policy_audit']['slot_decisions']]),
            online_selection_usage_equal=digest(a['usage']['online_selection']) == digest(b['usage']['online_selection']),
            observed_cost_vector_equal=(False if any(r['equal'] is False for r in scope) else
                None if any(r['equal'] is None for r in scope) else True),
            first_supported_readout_equal=comparable(da['first_supported_readout'],db['first_supported_readout']),
            identity_classification=a['classification'],swap_classification=b['classification'])
        p['primary_prediction_status'] = ('falsified_in_pair'
            if not p['native_ticks_equal'] or p['canonical_readout_trajectory_equal'] is False else
            'not_evaluable' if p['canonical_readout_trajectory_equal'] is None else 'supported_in_pair')
        p['secondary_difference_detected'] = any(p[k] is False for k in (
            'outcome_equal','canonical_completion_equal','final_support_signature_equal',
            'completed_path_inventory_equal','legacy_final_proof_projection_equal',
            'scheduler_usage_equal','scheduler_slot_trajectory_equal','online_selection_usage_equal',
            'observed_cost_vector_equal','first_supported_readout_equal'))
        comparisons.append(p)
    statuses = [p['primary_prediction_status'] for p in comparisons]
    if 'falsified_in_pair' in statuses:
        finding = 'ID_relabel_effect_in_input_order_measured_cost_or_trajectory'
    elif 'not_evaluable' in statuses:
        finding = 'negative_control_not_fully_evaluable'
    else:
        finding = ('secondary_ID_relabel_difference_despite_primary_invariance'
            if any(p['secondary_difference_detected'] for p in comparisons) else
            'no_ID_effect_detected_in_input_order_measured_cost_and_trajectory')
    groups, trials, readouts, scheduling = [], [], [], []
    for variant in ('identity','swap_SD'):
        rows = [cells[(variant,o,'input_order')] for o in ORDERS]
        costs = [r['usage']['native_kernel_ticks'] for r in rows]
        groups.append(dict(id_variant=variant,scheduler='input_order',permutations=6,
            min_native_ticks=min(costs),max_native_ticks=max(costs),tick_spread=max(costs)-min(costs),
            mean_native_ticks=sum(costs)/6,across_order_invariance_predicted=False))
    for r in records:
        d,f,t = r['diagnostics'],r['final'],r['trial']
        first,usable = d['first_supported_readout'],d.get('first_usable_supported_readout')
        row=dict(trial_id=t['id'],case=t['case'],id_variant=r['id_variant'],branch_order=r['branch_order'],
            scheduler=t['scheduler'],value=f['value'],accepted=f['accepted'],reason=f['reason'],
            classification=r['classification'],native_ticks=r['usage']['native_kernel_ticks'],
            readouts=len(r['readouts']),final_frontier_count=r['final_frontier_count'],
            support_route_completion_rank=d['support_route_completion_rank'],
            first_supported_ticks=None if first is None else first['ticks'],
            first_usable_supported_ticks=None if usable is None else usable['ticks'],
            final_D_DAG=None if d['final_support_signature'] is None else d['final_support_signature']['D_DAG'],
            measured_wall_seconds=r['reported_wall_seconds'],
            legacy_native_wall_seconds_placeholder=r.get('native_cost',{}).get('wall_seconds'),
            energy_joules=None,process_peak_memory_bytes=None,
            minimal_goal_proof_DAG_isomorphism=None)
        row.update(cost_vector(r))
        trials.append(row)
        readouts.extend(dict(trial_id=t['id'],id_variant=r['id_variant'],branch_order=r['branch_order'],
                             **{k:v for k,v in x.items() if k != 'state'}) for x in d['canonical_readouts'])
        scheduling.extend(dict(trial_id=t['id'],id_variant=r['id_variant'],branch_order=r['branch_order'],
            canonical_selected_IDs=None if x['selected_native_IDs'] is None else
                [d['inverse_mapping'][e] for e in x['selected_native_IDs']],**x)
                          for x in r['input_order_policy_audit']['slot_decisions'])
    return dict(schema='hcr-exp24-summary-v1',native_trials=12,base_topologies=1,paired_orders=6,
        finding=finding,secondary_difference_pairs=sum(p['secondary_difference_detected'] for p in comparisons),primary_supported_pairs=statuses.count('supported_in_pair'),
        primary_falsified_pairs=statuses.count('falsified_in_pair'),primary_not_evaluable_pairs=statuses.count('not_evaluable'),
        groups=groups,comparisons=comparisons,cost_differences=differences,trials=trials,
        readouts=readouts,scheduler_decisions=scheduling,
        parent_regression_checked=sum(r['parent_regression'] is not None for r in records),
        old_EXP23_trials_recounted_as_new=0,accuracy_required_for_audit=False,invariance_required_for_audit=False,
        cross_permutation_equality_required=False,external_LLM_used=False,
        evidence_level='native_toy_program',wall_time_superiority_claimed=False,energy_savings_claimed=False,
        ID_reading_absence_claimed=False)


def render(s):
    rows=['# EXP-24 / R043 — input_order ID 재명명 음성대조','', '## 결론','',
          f"관찰 분류: `{s['finding']}`.",
          f"동일 순열의 ID pair 예측 지지 {s['primary_supported_pairs']}/6, 예측 실패 {s['primary_falsified_pairs']}/6, 측정 불충분 {s['primary_not_evaluable_pairs']}/6.",
          f"보조 측정에서 차이가 검출된 pair: {s['secondary_difference_pairs']}/6.",
          'audit 통과는 실행·측정 계약의 검산이며, ID 불변성의 성공 조건이 아니다.','',
          '## 관찰','', '| 배열 순서 | 기존 ID ticks | 재명명 ticks | 차이 | readout 궤적 동일 |',
          '|---|---:|---:|---:|---|']
    for p in s['comparisons']:
        rows.append(f"| {p['branch_order']} | {p['identity_native_ticks']} | {p['swap_native_ticks']} | {p['swap_minus_identity_ticks']} | {p['canonical_readout_trajectory_equal']} |")
    rows += ['', '## 해석','',
        '기존 EXP-23의 min/max ID-key 개입과 달리, 기존 input_order는 frontier의 첫 slot을 고른다.',
        '선택 결정에 ID 순위를 사용하지 않지만, 입력 검증·로그용 ID 읽기는 그대로 존재한다.',
        '같은 순열의 재명명 전후를 비교한다. 서로 다른 배열 순열 사이의 tick 불변성은 예측하지 않는다.',
        '', '## 대안 설명','',
        '차이가 남으면 ID ranking 밖의 ID 의존성·참조 처리·투영 범위를 점검한다. 그 중 하나를 자동으로 원인으로 확정하지 않는다.',
        '차이가 없으면 측정된 조건·투영에서 ID 효과가 검출되지 않았다는 뜻이다. 전체 내부 상태의 ID 독립성을 증명한 것은 아니다.',
        '', '## 판별 실험','',
        '차이가 나타난 pair의 first_readout_difference 및 raw를 먼저 재생한다. 판정 전 topology나 scheduler를 추가하지 않는다.',
        '', '## 현재 주장 가능한 범위','',
        '고정 toy topology 1개, ID 배치 2개, 배열 순열 6개, input_order 1개의 12조건(6쌍). LLM 실험이 아니다.',
        f"EXP-22 동일 입력 input_order 회귀 {s['parent_regression_checked']}/6. 이 재검산과 EXP-23 기존 결과는 신규 독립 증거로 합산하지 않는다.",
        'D_DAG, native ticks, scheduler/selector 작업, wall time을 구분한다. 에너지와 프로세스 peak memory는 null이다.',
        '최종 지원 signature(value, D_DAG, assumptions)와 완성 경로 목록은 별도다. 최소 goal proof DAG 동치는 측정하지 않아 null로 둔다.',
        'native raw의 legacy wall_seconds placeholder는 실제 측정 시간과 별도 표기하고 비용 비교에서 제외한다.',
        '오답·abstention은 결과로 보존한다. schema/reference/runtime/audit 실패는 최초 실패와 부분 evidence를 남긴다.','']
    return '\n'.join(rows)
