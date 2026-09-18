"""Predictions are result fields. Cost, correctness, exposure and censoring remain distinct."""
from collections import Counter
import csv
import io
import json
from .storage import require, digest

FAMILIES = ('supported_len2', 'no_match_len1', 'conflict_len2')
VARIANTS = ('identity', 'fresh_ids')
CENSORED = {'stop_initial_budget', 'stop_compute_budget', 'stop_selection_budget', 'stop_engine_failure'}


def status(test, eligible=True):
    if not eligible or test is None: return 'not_evaluable'
    return 'supported_in_pair' if test else 'falsified_in_pair'


def comparison(a, b):
    return None if a is None or b is None else a == b


def uncensored(*records):
    return all(r['final']['reason'] not in CENSORED for r in records)


def cost_vector(record):
    result = {'native_kernel_ticks': record['usage']['native_kernel_ticks']}
    for prefix, values in (('native_cost', record['native_cost']), ('scheduler', record['scheduler_usage']),
                           ('online_selection', record['usage']['online_selection'])):
        for key, value in values.items():
            if key == 'wall_seconds': continue  # The inherited native placeholder is not a measurement.
            require(value is None or type(value) in (int,float), 'nonnumeric measured cost: ' + prefix + '.' + key)
            result[prefix + '.' + key] = value
    for key in ('pool_kernel_ticks','decision_kernel_ticks','macro_actions','primitive_actions','binding_scan_calls',
                'binding_edge_scans','circuit_inspections','macro_span_edge_items'):
        result['event_partition.' + key] = record['reuse_measurements'][key]
    return result


def decision_equal(a, b):
    left, right = a['direct_measurements']['decision_signature_sequence'], b['direct_measurements']['decision_signature_sequence']
    return None if not left or not right else left == right


def pair(on, off):
    m, n = on['reuse_measurements'], off['reuse_measurements']
    d = on['direct_measurements']; family = on['family']
    valid = uncensored(on, off)
    direct = valid and d['direct_circuit_use'] is True
    outcome = (on['final']['value'], on['final']['accepted']) == (off['final']['value'], off['final']['accepted'])
    ticks = on['usage']['native_kernel_ticks'] - off['usage']['native_kernel_ticks']
    expansion = on['native_cost']['expansions'] - off['native_cost']['expansions']
    dp = m['pool_kernel_ticks'] - n['pool_kernel_ticks']; dd = m['decision_kernel_ticks'] - n['decision_kernel_ticks']
    require(ticks == dp + dd, 'pair native tick accounting')
    predictions = {}
    if family == 'supported_len2':
        predictions = dict(H_direct=status(d['direct_circuit_use'] is True,valid),
            H_expansion=status(expansion < 0,direct), H_kernel=status(ticks < 0,direct),
            H_decision_same=status(decision_equal(on,off),direct), H_outcome=status(outcome,valid))
    elif family == 'no_match_len1':
        predictions = dict(H_no_match=status(d['matched_candidates'] == 0 and m['pool_networks'] == 0 and m['macro_actions'] == 0,valid),
                           H_no_match_ticks=status(ticks == 0,valid))
    else:
        evaluations = d['pool_candidate_evaluations']
        rejection_observed = (d['matched_candidates'] > 0 and evaluations > 0 and
            d['eligible_candidate_evaluations'] == 0 and d['mismatch_rejected_evaluations'] == evaluations and m['macro_actions'] == 0)
        # A missing pool is not silently counted as evidence of mismatch rejection.
        predictions = dict(H_conflict_reject=status(rejection_observed,valid),
            H_conflict_no_false_positive=status(not any(r['final']['accepted'] and r['final']['value'] is True for r in (on,off)),valid))
    return dict(family=family, id_variant=on['id_variant'], enabled_trial=on['trial']['id'], disabled_trial=off['trial']['id'],
        uncensored=valid, direct_effect_eligible=direct, direct_circuit_use_on=d['direct_circuit_use'],
        eligibility_reason='budget_or_engine_failure' if not valid else 'direct_positive_adoption' if direct else 'no_direct_positive_adoption',
        on_ticks=on['usage']['native_kernel_ticks'], off_ticks=off['usage']['native_kernel_ticks'], delta_ticks=ticks,
        on_expansions=on['native_cost']['expansions'], off_expansions=off['native_cost']['expansions'], delta_expansions=expansion,
        delta_pool_ticks=dp, delta_decision_ticks=dd, on_macro_actions=m['macro_actions'], off_macro_actions=n['macro_actions'],
        outcome_equal=outcome, on_value=on['final']['value'], off_value=off['final']['value'],
        on_accepted=on['final']['accepted'], off_accepted=off['final']['accepted'],
        on_reason=on['final']['reason'], off_reason=off['final']['reason'],
        on_classification=on['classification'], off_classification=off['classification'],
        decision_computation_signature_equal=decision_equal(on,off),
        support_signature_equal=comparison(on['diagnostics']['final_support_signature'],off['diagnostics']['final_support_signature']),
        full_readout_trajectory_equal=comparison(on['diagnostics']['canonical_readout_sha256'],off['diagnostics']['canonical_readout_sha256']),
        same_outcome_cost_comparison=valid and outcome,
        hypotheses=predictions, accounting_is_counterfactual=False, unlike_units_summed=False)


def summarize(records):
    require(len(records) == 12 and all(type(r['trial']['use_circuits']) is bool for r in records), 'native record population/type')
    cells = {(r['family'],r['id_variant'],r['trial']['use_circuits']):r for r in records}
    require(set(cells) == {(f,v,g) for f in FAMILIES for v in VARIANTS for g in (True,False)} and len(cells) == 12,
            'missing or duplicate cells')
    require(all(r['trial']['scope']=='route_only' and r['trial']['arm']=='online_support' and r['trial']['scheduler']=='input_order'
                for r in records),'non-target policy changed')
    pairs = []; differences = []; controls = []; conflict = []; rows = []
    networks = []; candidates = []; actions = []; readouts = []; bindings = []
    for family in FAMILIES:
        for variant in VARIANTS:
            on, off = (cells[(family,variant,g)] for g in (True,False))
            pairs.append(pair(on,off))
            a,b = cost_vector(on),cost_vector(off)
            for key in sorted(set(a)|set(b)):
                left,right=a.get(key),b.get(key)
                differences.append(dict(family=family,id_variant=variant,metric=key,enabled=left,disabled=right,
                    delta=None if left is None or right is None else left-right))
        for gate in (True,False):
            a,b = (cells[(family,v,gate)] for v in VARIANTS)
            av,bv = cost_vector(a),cost_vector(b)
            unequal = any(av.get(k) is not None and bv.get(k) is not None and av[k] != bv[k] for k in set(av)|set(bv))
            known = all(av.get(k) is not None and bv.get(k) is not None for k in set(av)|set(bv))
            equal = False if unequal else True if known else None
            trajectory = comparison(a['diagnostics']['canonical_readout_sha256'],b['diagnostics']['canonical_readout_sha256'])
            decision = decision_equal(a,b)
            test = False if equal is False or trajectory is False or decision is False else True if equal and trajectory and decision else None
            controls.append(dict(family=family,use_circuits=gate,identity_trial=a['trial']['id'],fresh_trial=b['trial']['id'],
                measured_cost_vector_equal=equal, canonical_readouts_equal=trajectory, decision_computation_signature_equal=decision,
                prediction=status(test,uncensored(a,b)), wall_time_identity_required=False))
    for variant in VARIANTS:
        for gate in (True,False):
            a,b = (cells[(f,variant,gate)] for f in ('supported_len2','conflict_len2'))
            conflict.append(dict(id_variant=variant,use_circuits=gate,positive_trial=a['trial']['id'],conflict_trial=b['trial']['id'],
                positive_matched=a['direct_measurements']['matched_candidates'],conflict_matched=b['direct_measurements']['matched_candidates'],
                positive_eligible=a['direct_measurements']['eligible_candidate_evaluations'],conflict_eligible=b['direct_measurements']['eligible_candidate_evaluations'],
                positive_macro=a['reuse_measurements']['macro_actions'],conflict_macro=b['reuse_measurements']['macro_actions'],
                positive_value=a['final']['value'],conflict_value=b['final']['value'],
                positive_accepted=a['final']['accepted'],conflict_accepted=b['final']['accepted'],
                positive_reason=a['final']['reason'],conflict_reason=b['final']['reason'],
                uncensored=uncensored(a,b), static_separate_sessions=True, dynamic_reexpansion_tested=False))
    for r in records:
        tags=dict(trial_id=r['trial']['id'],family=r['family'],id_variant=r['id_variant'],use_circuits=r['trial']['use_circuits'])
        sig=r['diagnostics']['final_support_signature']; d=r['direct_measurements']; m=r['reuse_measurements']
        rows.append(dict(**tags,value=r['final']['value'],accepted=r['final']['accepted'],reason=r['final']['reason'],
            classification=r['classification'],final_D_DAG=None if sig is None else sig['D_DAG'],
            direct_circuit_use=d['direct_circuit_use'],direct_circuit_use_count=d['direct_circuit_use_count'],
            exposure=m['exposure'],matched_candidates=d['matched_candidates'],eligible_candidates=d['eligible_candidate_evaluations'],
            mismatch_rejected=d['mismatch_rejected_evaluations'],
            measured_wall_seconds=r['reported_wall_seconds'],energy_joules=None,process_peak_memory_bytes=None,
            **cost_vector(r)))
        networks.extend(dict(**tags,**n) for n in d['decision_networks'])
        candidates.extend(dict(**tags,**n) for n in d['candidates'])
        actions.extend(dict(**tags,**n) for n in m['actions'])
        readouts.extend(dict(**tags,**n) for n in r['diagnostics']['canonical_readouts'])
        bindings.extend(dict(**tags,**n) for n in d['binding_rows'])
    hypotheses={}
    for p in pairs:
        for h,s in p['hypotheses'].items():
            hypotheses.setdefault(h,Counter())[s]+=1
    groups=[]
    for family in FAMILIES:
        for gate in (True,False):
            rs=[cells[(family,v,gate)] for v in VARIANTS]
            groups.append(dict(family=family,use_circuits=gate,conditions=2,
                ticks=[r['usage']['native_kernel_ticks'] for r in rs],expansions=[r['native_cost']['expansions'] for r in rs],
                accepted=sum(r['final']['accepted'] for r in rs),
                correct=sum(r['classification']=='correct_in_all_declared_worlds' for r in rs),
                abstained=sum(not r['final']['accepted'] for r in rs),
                direct_positive_adoptions=sum(r['direct_measurements']['direct_circuit_use'] is True for r in rs)))
    return dict(schema='hcr-exp26-summary-v1',native_trials=12,gate_pairs=6,primary_pairs=2,
        topology_count=2,condition_families=3,hypotheses={h:dict(c) for h,c in hypotheses.items()},
        comparisons=pairs,cost_differences=differences,ID_controls=controls,conflict_controls=conflict,
        trials=rows,groups=groups,decision_networks=networks,candidate_exposure=candidates,
        expansion_actions=actions,readouts=readouts,binding_scans=bindings,
        claims=dict(scope='native_toy_frozen_memory_static_direct_support_controls',
            efficacy_required_for_audit=False,old_raw_counted_as_new=False,selftests_counted_as_research=False,
            native_sources_modified=False,new_learning_tested=False,dynamic_reexpansion_tested=False,
            minimal_goal_DAG_isomorphism=None,lower_ticks_means_lower_energy=False,
            len1_vs_len2_is_pure_matching_intervention=False,total_compute_score=None))


def csv_text(rows):
    if not rows: return ''
    fields=list(dict.fromkeys(k for r in rows for k in r))
    out=io.StringIO(newline=''); writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for r in rows:
        writer.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')) if isinstance(v,(dict,list,tuple)) else v for k,v in r.items()})
    return out.getvalue()


def render(s):
    rows=['# EXP-26 / R045 — 최종 지원 경로의 직접 회로 사용', '', '## 결론', '',
        '본 실험 12조건 / 회로 gate 6쌍. 주 분석은 supported_len2의 2쌍이며 ID 대조를 독립 문제 반복으로 세지 않는다.',
        '아래 표는 사전 예측을 실제 기록에 적용한 결과다. 미적용·오답·보류는 보고하고, 효과를 audit 성공 조건으로 요구하지 않는다.', '',
        '| 예측 | pair 지지 | pair 예측 실패 | 평가 불가 |','|---|---:|---:|---:|']
    for h,c in s['hypotheses'].items():
        rows.append(f"| {h} | {c.get('supported_in_pair',0)} | {c.get('falsified_in_pair',0)} | {c.get('not_evaluable',0)} |")
    rows += ['', '## 관찰', '', '| 조건 | ID | 직접 사용 ON | ON ticks | OFF ticks | Δpool | Δdecision | ON/OFF expansion |',
             '|---|---|---|---:|---:|---:|---:|---|']
    for p in s['comparisons']:
        rows.append(f"| {p['family']} | {p['id_variant']} | {p['direct_circuit_use_on']} | {p['on_ticks']} | {p['off_ticks']} | {p['delta_pool_ticks']} | {p['delta_decision_ticks']} | {p['on_expansions']}/{p['off_expansions']} |")
    rows += ['', '## 해석', '',
        'H_direct는 양성 채택 경로에 explicit circuit use가 기록됐는지를 본다. ON에 macro action이 있었다는 것만으로 직접 사용으로 세지 않는다.',
        'H_expansion과 H_kernel은 직접 사용과 비검열 조건에서 각각 평가한다. H_decision_same은 decision program·drives와 모든 기록된 tick state의 서명이 같은지 비교하는 경쟁 설명의 예측이다.',
        '결과가 다르거나 예산 종료인 pair의 비용도 삭제하지 않되, 같은 성능에서의 효율 향상으로 표현하지 않는다.', '',
        '## 대안 설명과 판별 범위', '',
        'single-path 입력은 경로 경쟁에 의한 우회를 제거한다. host가 실행 궤적을 고정하거나 회로 승자를 지정하지 않는다.',
        'len1 미매칭 대조는 topology가 다른 별도 진단이다. len2와의 차이를 순수 matching 비용이나 D_DAG 인과효과라고 부르지 않는다.',
        'conflict_len2는 같은 topology의 관측 하나만 반전한 정적 대조다. 실제 mismatch 거부, activation 거부, pool 미형성을 candidate_exposure.csv에서 구분한다. 같은 session의 수정·재학습 실험은 아니다.', '',
        '## 현재 주장 가능한 범위', '',
        '고정된 native toy 입력 2개 topology, 3개 관측 조건에서의 회로 지원 분기 총효과다. 학습 memory·config·scheduler·selector는 유지한다.',
        'D_DAG는 독립 검산된 선택 proof 깊이다. path edge 수, expansion 수, kernel ticks와 동일시하지 않는다.',
        'wall time은 별도 기록이며 energy·peak memory·최소 goal proof DAG 동형성은 null이다. pool/decision tick 차이는 관찰 비용 분해이지 pool을 제거한 반사실 실험이 아니다.',
        'EXP25 부모 raw 재검산 및 native 회귀·self-test 결과는 새 연구 모집단에 합산하지 않는다.', '']
    return '\n'.join(rows)
