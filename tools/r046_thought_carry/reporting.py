"""Descriptive paired reports only; no hypothesis outcome is a validation precondition."""
import csv,io,json
from .storage import require,digest
from .contracts import ARMS,SCENARIOS,VARIANTS


def csv_bytes(rows):
    if not rows:return b''
    fields=list(dict.fromkeys(k for row in rows for k in row))
    f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
    for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    return f.getvalue().encode('utf-8')


def status(value,available=True):
    return 'not_evaluable' if not available else 'supported' if value else 'falsified'


def summarize(plan,sources,rows,audits):
    cells={};trials=[];diffs=[];pairs=[];ids=[];transfer=[];refs=[];signature=[]
    cases={c['id']:c for c in plan['cases']}
    for t in plan['trials']:
        r=rows[t['id']];a=audits[t['id']];c=cases[t['case']];key=(c['scenario'],c['variant'],t['arm']);cells[key]=r
        nc=r['native_cost'];bc=r['bridge_cost'];proof=a.get('proof',{})
        sa=sources[t['source']];usable=a['measurement_available']
        row=dict(trial_id=t['id'],scenario=c['scenario'],variant=c['variant'],arm=t['arm'],
            source_record_sha256=digest(sa),raw_value=r['raw_value'],accepted=r['accepted'],classification=a['classification'],
            predecision_B_candidate=r['pre_decision_candidate'] is not None,censored=r['censored'],gate_valid=r['gate_valid'],gate_reason=r['gate_reason'],
            A_kernel_ticks=sa['native_cost']['kernel_ticks'],B_kernel_ticks=nc['kernel_ticks'],
            A_plus_B_kernel_ticks=sa['native_cost']['kernel_ticks']+nc['kernel_ticks'],
            D_DAG=proof.get('D_DAG'),expanded_proof_nodes=proof.get('expanded_reachable_nodes'),
            B_wall_seconds=r['wall_seconds'],energy_joules=None,peak_memory_bytes=None,
            native_adaptive_expansions=None,bridge_is_native_AdaptiveSession=False)
        row.update({'native.'+k:v for k,v in nc.items() if k!='wall_seconds'})
        row.update({'carry.'+k:v for k,v in bc.items()});trials.append(row)
        transfer.extend(dict(trial_id=t['id'],**m) for m in r['transfer_map'])
        if r['proof_graph']:
            refs.extend(dict(trial_id=t['id'],node_id=n,origin='A',source_record_sha256=digest(sa)) for n in r['proof_graph']['external_node_refs'])
        signature.append(dict(trial_id=t['id'],raw_program_drive_sha256=a.get('raw_program_drive_sha256'),
            effective_program_drive_sha256=a.get('effective_program_drive_sha256'),dynamics_sha256=a.get('dynamics_sha256'),
            initial_state_sha256=digest(r['initial_state'])))
    require(len(cells)==24,'trial matrix')
    for sc in SCENARIOS:
        for v in VARIANTS:
            cold=cells[sc,v,'cold']
            for arm in ARMS[1:]:
                r=cells[sc,v,arm];ok=not r['censored'] and not cold['censored']
                equal=(r['raw_value'],r['accepted'])==(cold['raw_value'],cold['accepted'])
                bc,cc=r['bridge_cost'],cold['bridge_cost']
                hp={'H_outcome':status(equal,ok)}
                if sc=='extend' and arm=='state_carry':hp['H_state_ticks']=status(r['native_cost']['kernel_ticks']<cold['native_cost']['kernel_ticks'],ok and bc['state_groups_written']>0)
                if sc=='extend' and arm=='relation_carry':hp['H_proof_reuse']=status(r['pre_decision_candidate'] is not None and bc['proof_nodes_reused']>0 and bc['proof_nodes_created']<cc['proof_nodes_created'],ok)
                if sc in ('different_subject','premise_changed'):
                    hp['H_binding' if sc=='different_subject' else 'H_invalidation']=status(not r['gate_valid'] and bc['proof_nodes_reused']==bc['state_groups_written']==0,ok)
                pairs.append(dict(scenario=sc,variant=v,arm=arm,baseline='cold',outcome_equal=equal,
                    delta_B_kernel_ticks=r['native_cost']['kernel_ticks']-cold['native_cost']['kernel_ticks'],
                    delta_new_proof_nodes=bc['proof_nodes_created']-cc['proof_nodes_created'],
                    borrowed_A_nodes=bc['proof_nodes_reused'],transferred_groups=bc['state_groups_written'],
                    effective_program_drives_equal=(r['program'],r['effective_drives'])==(cold['program'],cold['effective_drives']),
                    raw_trajectory_equal=r['ticks']==cold['ticks'],hypotheses=hp,
                    cost_improvement_requires_same_outcome=equal,gate_reason=r['gate_reason']))
                for group in ('native_cost','bridge_cost'):
                    for k in sorted(r[group]):
                        if k=='wall_seconds':continue
                        diffs.append(dict(scenario=sc,variant=v,arm=arm,metric=group+'.'+k,
                            carry=r[group][k],cold=cold[group][k],delta=r[group][k]-cold[group][k]))
    def count_vector(r):
        return dict(native={k:v for k,v in r['native_cost'].items() if k!='wall_seconds'},
                    carry={k:v for k,v in r['bridge_cost'].items() if not k.endswith('_bytes')})
    for sc in SCENARIOS:
        for arm in ARMS:
            a,b=(cells[sc,v,arm] for v in VARIANTS)
            equal=(a['raw_value'],a['accepted'])==(b['raw_value'],b['accepted'])
            counts=count_vector(a)==count_vector(b)
            ids.append(dict(scenario=sc,arm=arm,outcome_equal=equal,operation_counts_equal=counts,
                effective_program_equal=(a['program'],a['effective_drives'])==(b['program'],b['effective_drives']),
                numeric_trajectory_equal=a['ticks']==b['ticks'],
                export_byte_difference=b['bridge_cost']['export_bytes']-a['bridge_cost']['export_bytes'],
                prediction=status(equal and counts and a['ticks']==b['ticks'],not a['censored'] and not b['censored']),
                byte_invariance_predicted=False))
    memo=[]
    for sc in SCENARIOS:
        for v in VARIANTS:
            m,r=cells[sc,v,'proof_memo'],cells[sc,v,'relation_carry']
            memo.append(dict(scenario=sc,variant=v,outcome_equal=(m['raw_value'],m['accepted'])==(r['raw_value'],r['accepted']),
                proof_graph_equal=m['proof_graph']==r['proof_graph'],kernel_ticks_equal=m['native_cost']['kernel_ticks']==r['native_cost']['kernel_ticks'],
                delta_new_proof_nodes=r['bridge_cost']['proof_nodes_created']-m['bridge_cost']['proof_nodes_created'],
                delta_export_bytes=r['bridge_cost']['export_bytes']-m['bridge_cost']['export_bytes'],
                unique_HCC_advantage_established=False))
    claims=dict(backend='native_HCR_core_plus_explicit_adapter',new_learning_tested=False,
        full_HCC_cycle_confirmed=False,brain_mechanism_confirmed=False,relation_carry_is_unique_to_HCC=False,
        proof_reuse_is_not_native_decision_skip=True,native_AdaptiveSession_performance_measured=False,
        parent_results_recounted_as_independent=False,synthetic_tests_in_research_population=False)
    return dict(schema='hcr-exp27-summary-v1',sources=2,followups=24,paired_conditions=6,
        trials=trials,pairs=pairs,cost_differences=diffs,ID_controls=ids,memo_controls=memo,
        transfer_maps=transfer,proof_refs=refs,signatures=signature,claims=claims)


def render(s):
    out=['# EXP-27 / R046 — A의 계산을 B의 추론에 전달하기','','## 결론','',
         '원천 A 2회, 후속 B 24조건. 아래는 실제 관찰값이며 예측 지지는 audit 통과 조건이 아니다.',
         '기존 HCR native 핵심 함수에 순차 carry 어댑터를 붙인 실험이다. AdaptiveSession 전체 또는 새 회로 학습의 효과와 동일시하지 않는다.','',
         '| 상황 | ID | 군 | B ticks | 새 proof node | A 참조 node | state 전달 | 판정 |',
         '|---|---|---|---:|---:|---:|---:|---|']
    for t in s['trials']:
        out.append(f"| {t['scenario']} | {t['variant']} | {t['arm']} | {t['B_kernel_ticks']} | {t['carry.proof_nodes_created']} | {t['carry.proof_nodes_reused']} | {t['carry.state_groups_written']} | {t['classification']} |")
    out+=['','## 사전 예측의 pair별 판정','']
    for p in s['pairs']:
        out.append(f"- {p['scenario']} / {p['variant']} / {p['arm']}: "+', '.join(k+'='+v for k,v in p['hypotheses'].items()))
    out+=['','## 해석','',
        '수치 상태 전달과 proof 관계 전달은 서로 다른 개입이다. native 탐색·decision program은 모든 군에서 유지된다. proof node를 덜 만들었다고 decision 계산이 줄었다고 하지 않는다.',
        '일반 dependency-aware proof memo와 relation-carry 결과는 memo_controls.csv에 따로 비교한다. 동치이면 관계 표기만의 독립적인 이득으로 세지 않는다.',
        'old goal과 안정화 이력을 넘기지 않는다. state는 근거로 채택하는 것이 아니라 초기값 제안이며 B에서 다시 수렴·검증한다.','',
        '## 근거 변경과 Binding','',
        'gate_reason, proof_refs.csv, transfer_maps.csv에서 대상 불일치·근거 변경 후 A의 상태/노드가 사용됐는지 확인한다. rejection 후 cold 처리는 사전 등록된 정책이며 ID/proof 자동 수정이 아니다.','',
        '## 현재 주장 가능한 범위','',
        '정적 topology 2종, 순차 관측 3상황의 최소 계산 실험이다. 유효 관계의 구조적 재사용과 warm initialization을 분리하며, 새 학습·생물학·HCC 고유성을 입증하지 않는다.',
        'D_DAG는 A의 외부 parent까지 펼친 proof에서 독립 계산한다. 신규 node 수·native ticks와 같지 않다.',
        'A_plus_B ticks는 각 pair가 필요로 한 A 한 번과 B의 합이며, 공유된 A를 서로 다른 독립 실행으로 중복 집계하지 않는다.',
        'carry byte·검사·native 비용·wall time은 별개다. ID 문자열 길이가 다르면 byte 수는 달라질 수 있다. energy/peak memory는 null이다.','']
    return '\n'.join(out).encode('utf-8')
