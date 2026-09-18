"""Research predictions are outputs, never validity checks. No runtime/selector imports."""
from collections import Counter
from r042_id_role_isolation.reporting import csv_text
from r043_input_order_control.reporting import comparable, first_readout_difference, cost_vector
from .contracts import ORDERS, VARIANTS
from .storage import digest, require

CENSORED={'stop_initial_budget','stop_compute_budget','stop_selection_budget','stop_engine_failure'}


def exposure_eligibility(on,off):
    if on['final']['reason'] in CENSORED or off['final']['reason'] in CENSORED:
        return False,'budget_or_engine_failure'
    if on['reuse_measurements']['macro_actions']==0:
        return False,'no_applied_macro; gate_total_effect_still_reported'
    return True,'applied_macro_and_uncensored_pair'


def status(test,eligible):
    return 'not_evaluable_for_registered_prediction' if not eligible else 'supported_in_pair' if test else 'falsified_in_pair'


def metric_vector(r):
    result=cost_vector(r)
    for key in ('pool_kernel_ticks','decision_kernel_ticks','macro_actions','primitive_actions',
                'binding_scan_calls','binding_edge_scans','circuit_inspections','macro_span_edge_items'):
        result['event_partition.'+key]=r['reuse_measurements'][key]
    # These are deliberately not counted as zeros or included in vector superiority.
    return result


def vector_equal(a,b):
    pairs=[(a.get(k),b.get(k)) for k in set(a)|set(b)]
    if any(x is not None and y is not None and x!=y for x,y in pairs): return False
    if any(x is None or y is None for x,y in pairs): return None
    return True


def summarize(records):
    require(len(records)==24,'expected 24 native records')
    require(all(type(r['trial']['use_circuits']) is bool for r in records),'gate must be bool')
    cells={(r['id_variant'],r['branch_order'],r['trial']['use_circuits']):r for r in records}
    require(set(cells)=={(v,o,g) for v in VARIANTS for o in ORDERS for g in (True,False)},'missing/duplicate cells')
    require(all(r['trial']['scope']=='route_only' and r['trial']['scheduler']=='input_order'
        and r['trial']['arm']=='online_support' for r in records),'non-target policy changed')
    comparisons=[];differences=[]
    for order in ORDERS:
        for variant in VARIANTS:
            on,off=(cells[(variant,order,g)] for g in (True,False))
            a,b=on['usage']['native_kernel_ticks'],off['usage']['native_kernel_ticks']
            x,y=on['native_cost']['expansions'],off['native_cost']['expansions']
            eligible,why=exposure_eligibility(on,off)
            outcome=(on['final']['accepted'],on['final']['value'])==(off['final']['accepted'],off['final']['value'])
            supported=comparable(on['diagnostics']['final_support_signature'],off['diagnostics']['final_support_signature'])
            row=dict(branch_order=order,id_variant=variant,enabled_trial=on['trial']['id'],disabled_trial=off['trial']['id'],
                enabled_native_ticks=a,disabled_native_ticks=b,enabled_minus_disabled_ticks=a-b,
                enabled_expansions=x,disabled_expansions=y,enabled_minus_disabled_expansions=x-y,
                macro_actions_enabled=on['reuse_measurements']['macro_actions'],
                enabled_exposure=on['reuse_measurements']['exposure'],prediction_eligible=eligible,eligibility_reason=why,
                H_expansion=status(x<y,eligible),H_kernel=status(a<b,eligible),H_outcome=status(outcome,eligible),
                value_acceptance_equal=outcome,final_support_signature_equal=supported,
                enabled_classification=on['classification'],disabled_classification=off['classification'],
                enabled_reason=on['final']['reason'],disabled_reason=off['final']['reason'],
                enabled_pool_ticks=on['reuse_measurements']['pool_kernel_ticks'],
                disabled_pool_ticks=off['reuse_measurements']['pool_kernel_ticks'],
                enabled_decision_ticks=on['reuse_measurements']['decision_kernel_ticks'],
                disabled_decision_ticks=off['reuse_measurements']['decision_kernel_ticks'],
                measured_trajectory_equal=comparable(on['diagnostics']['canonical_readouts'] or None,
                                                     off['diagnostics']['canonical_readouts'] or None),
                trajectories_forced_equal=False,minimal_goal_proof_DAG_isomorphism=None)
            row['observation_class']=(
                'budget_or_engine_failure_censored' if why=='budget_or_engine_failure' else
                'no_macro_applied_gate_effect_only' if not eligible else
                'value_or_acceptance_changed' if not outcome else
                'fewer_expansions_and_fewer_native_ticks' if x<y and a<b else
                'fewer_expansions_but_more_native_ticks' if x<y and a>b else
                'fewer_expansions_same_native_ticks' if x<y and a==b else
                'no_expansion_reduction')
            comparisons.append(row)
            ca,cb=metric_vector(on),metric_vector(off)
            for key in sorted(set(ca)|set(cb)):
                left,right=ca.get(key),cb.get(key)
                require(left is None or type(left) in (int,float),'non-numeric measured cost')
                require(right is None or type(right) in (int,float),'non-numeric measured cost')
                differences.append(dict(branch_order=order,id_variant=variant,metric=key,enabled=left,disabled=right,
                    enabled_minus_disabled=None if left is None or right is None else left-right,
                    equal=None if left is None or right is None else left==right))
    controls=[]
    for order in ORDERS:
        for gate in (True,False):
            a,b=(cells[(v,order,gate)] for v in VARIANTS)
            divergence=first_readout_difference(a['diagnostics']['canonical_readouts'],b['diagnostics']['canonical_readouts'])
            ticks=a['usage']['native_kernel_ticks']==b['usage']['native_kernel_ticks']
            trajectory=None if not divergence['comparable'] else divergence['reason']=='equal'
            pred='falsified_in_pair' if not ticks or trajectory is False else 'not_evaluable_in_pair' if trajectory is None else 'supported_in_pair'
            controls.append(dict(branch_order=order,use_circuits=gate,identity_trial=a['trial']['id'],swap_trial=b['trial']['id'],
                native_ticks_equal=ticks,canonical_readout_trajectory_equal=trajectory,
                observed_count_vector_equal=vector_equal(metric_vector(a),metric_vector(b)),
                prediction=pred,first_readout_difference=divergence,across_array_orders_invariance_predicted=False))
    groups=[]
    for variant in VARIANTS:
        for gate in (True,False):
            rs=[cells[(variant,o,gate)] for o in ORDERS]
            ticks=[r['usage']['native_kernel_ticks'] for r in rs]
            groups.append(dict(id_variant=variant,use_circuits=gate,conditions=6,
                min_native_ticks=min(ticks),max_native_ticks=max(ticks),tick_spread=max(ticks)-min(ticks),
                mean_native_ticks=sum(ticks)/6,accepted=sum(r['final']['accepted'] for r in rs),
                correct_in_declared_worlds=sum(r['classification']=='correct_in_all_declared_worlds' for r in rs)))
    trials=[];readouts=[];scheduling=[];networks=[];actions=[]
    for r in records:
        d,t,m=r['diagnostics'],r['trial'],r['reuse_measurements'];f=r['final']
        first=d['first_supported_readout'];signature=d['final_support_signature']
        tags=dict(trial_id=t['id'],use_circuits=t['use_circuits'],id_variant=r['id_variant'],branch_order=r['branch_order'])
        row=dict(**tags,scope=t['scope'],scheduler=t['scheduler'],value=f['value'],accepted=f['accepted'],
            reason=f['reason'],classification=r['classification'],native_ticks=r['usage']['native_kernel_ticks'],
            readout_count=len(r['readouts']),final_frontier_count=r['final_frontier_count'],
            first_supported_ticks=None if first is None else first['ticks'],
            final_D_DAG=None if signature is None else signature['D_DAG'],
            exposure=m['exposure'],adopted_route=m['adopted_route'],
            measured_wall_seconds=r['reported_wall_seconds'],
            legacy_native_wall_seconds_placeholder=r['native_cost'].get('wall_seconds'),
            energy_joules=None,process_peak_memory_bytes=None,minimal_goal_proof_DAG_isomorphism=None)
        row.update(metric_vector(r));trials.append(row)
        readouts.extend(dict(**tags,**{k:v for k,v in x.items() if k!='state'}) for x in d['canonical_readouts'])
        scheduling.extend(dict(**tags,**x) for x in r['input_order_policy_audit']['slot_decisions'])
        networks.extend(dict(**tags,**x) for x in m['networks'])
        actions.extend(dict(**tags,**x) for x in m['actions'])
    hypotheses={h:dict(Counter(p[h] for p in comparisons)) for h in ('H_expansion','H_kernel','H_outcome')}
    claims=dict(scope='native_toy_frozen_memory_total_circuit_branch_gate',
        registered_predictions=hypotheses,ID_relabel_controls=dict(Counter(p['prediction'] for p in controls)),
        new_learning_tested=False,compression_learning_gain_tested=False,retention_tested=False,
        full_HCC_cycle_confirmed=False,macro_application_isolated_from_pool=False,
        lower_ticks_is_lower_energy=False,minimum_goal_proof_DAG_identity_measured=False,
        old_parent_raw_recounted_as_new=False,
        interpretation='prediction status is per pair, not whole-theory falsification; count fields are not independent samples')
    return dict(schema='hcr-exp25-summary-v1',native_trials=24,base_topologies=1,reuse_pairs=12,
        prediction_eligible_pairs=sum(p['prediction_eligible'] for p in comparisons),hypotheses=hypotheses,
        observation_classes=dict(Counter(p['observation_class'] for p in comparisons)),
        comparisons=comparisons,cost_differences=differences,ID_controls=controls,groups=groups,
        trials=trials,readouts=readouts,scheduler_decisions=scheduling,network_costs=networks,expansion_actions=actions,
        parent_regression_checked=sum(r['parent_regression'] is not None for r in records),claims=claims)


def render(s):
    text=['# EXP-25 / R044 — 학습 memory를 유지한 회로 재사용 기여 분리','',
        '## 결론','',
        f"본 실험 {s['native_trials']}조건 / {s['reuse_pairs']}쌍, 실제 macro 적용과 무중단 조건을 만족한 예측 평가 대상 {s['prediction_eligible_pairs']}쌍.",
        '회로 재사용의 이득을 미리 성공으로 판정하지 않는다. 다음은 동결된 예측을 실제 결과에 적용한 판정이다.','',
        '| 예측 | pair 지지 | pair 예측 실패 | 평가 조건 미충족 |','|---|---:|---:|---:|']
    for h,counts in s['hypotheses'].items():
        text.append(f"| {h} | {counts.get('supported_in_pair',0)} | {counts.get('falsified_in_pair',0)} | {counts.get('not_evaluable_for_registered_prediction',0)} |")
    text+=['','H_expansion: 재사용 허용 시 expansion 감소. H_kernel: native ticks 감소. H_outcome: 값·채택 보존.',
        '각 예측은 별도이며, 하나의 실패를 다른 성공으로 상쇄하지 않는다. 비용 비교는 결과가 다른 pair에서도 원값을 보존하되 효율 향상이라 부르지 않는다.','',
        '## 관찰','', '| 배열 | ID 배치 | ON ticks | OFF ticks | ON expansion | OFF expansion | 관찰 분류 |',
        '|---|---|---:|---:|---:|---:|---|']
    for p in s['comparisons']:
        text.append(f"| {p['branch_order']} | {p['id_variant']} | {p['enabled_native_ticks']} | {p['disabled_native_ticks']} | {p['enabled_expansions']} | {p['disabled_expansions']} | {p['observation_class']} |")
    text+=['','## 해석','',
        '`route_only`와 `input_order`, 동일 학습 memory·관측·config·selector·예산을 두고 native 생성자 use_circuits만 조작했다.',
        '이 스위치는 회로 검색·binding·pool 경쟁·macro 적용 전체 경로를 허용/차단한다. macro 적용만의 순수 효과와 동일하지 않다.',
        'pool/decision network ticks는 raw tick event에서 분리한다. expansion·binding·selector·wall time은 다른 단위로 보존한다.',
        'macro의 span_edges는 실제 적용 span 길이이며 그 숫자를 곧바로 생략된 실행 단계 수로 바꾸지 않는다.',
        'native가 자연스럽게 만든 경로·readout 수·실행 순서를 강제로 맞추지 않는다. 표의 차이는 강제 동기화 결과가 아니다.','',
        '## 대안 설명','',
        '회로 재사용 분기의 총 효과에는 후보 검색과 경쟁 비용, 적용 길이, 달라진 경로 및 채택 시점이 모두 포함된다.',
        'route_only는 learned judgment drive만 차단한다. 회로 활성화 pool의 학습 routing prior까지 0으로 만들지는 않는다.',
        '공통 예산 상한은 유지하지만 기존 보수적 tick 예약량은 회로 스위치에 의존한다. 예산 종료가 낀 pair는 별도 표시한다.',
        '새 학습이나 회로 형성 전후를 비교한 실험이 아니다. 기존에 학습된 회로의 사용 기여를 시험한 단계다.','',
        '## 판별 실험','',
        'expansion 감소와 native ticks 증가가 함께 나타나면 network_costs.csv의 pool/decision 분해 및 binding 비용부터 확인한다.',
        '값·채택·지원 signature가 바뀌면 비용 절감 주장을 멈추고 raw의 최초 경로 분기와 proof 선택을 검토한다.',
        '회로 사용 자체가 없으면 새로운 회로를 자동 추가하지 않는다. 노출 실패와 gate overhead를 먼저 기록한다.','',
        '## 현재 주장 가능한 범위','',
        f"동일 입력의 enabled/identity 부모 회귀 {s['parent_regression_checked']}/6. 부모 raw 재검산과 self-test는 신규 독립 연구 결과에 합산하지 않는다.",
        '고정 toy topology 하나와 기존 seed 하나의 24조건이다. LLM·인간 인지·하드웨어 효율 결과가 아니다.',
        'D_DAG는 proof 의존 깊이이다. 에너지·peak memory·최소 goal proof DAG 동형성은 null이다.',
        '완전한 Graph→Circuit 학습·오류 후 장기 재학습·계층 수렴을 확인한 것으로 확장하지 않는다.','']
    return '\n'.join(text)
