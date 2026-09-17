"""EXP-17 입력 변환·native 계보 검산. 생산 입력 변환/실행/선택 함수는 호출하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from math import isfinite
from r035_frozen_selection.audit import demand, sha, view_check, audit_result
from r035_frozen_selection import storage as io
from .diagnostics import diagnose_state, canonical_state, reachable


def check_transform(source: dict, packet: dict, variant: dict) -> dict:
    demand(set(packet)=={'schema','boundary','variant','source_observation_sha256','observation','maps'},'입력 변환 필드')
    demand(packet['schema']=='hcr-input-transform-r036-v1' and packet['boundary']=='before_native_begin','입력 변환 경계')
    demand(packet['source_observation_sha256']==sha(source) and sha(packet['variant'])==sha(variant),'입력 변환 출처')
    demand(set(variant)=={'id','node_alias','edge_alias','edge_reverse'} and
        all(type(variant[k]) is bool for k in ('node_alias','edge_alias','edge_reverse')),'변환 변수 타입')
    ns=sorted({n for e in source['edges'] for n in (e['source'],e['target'])},reverse=True)
    es=sorted((e['id'] for e in source['edges']),reverse=True)
    nm={n:('n_%03d'%i if variant['node_alias'] else n) for i,n in enumerate(ns)}
    em={n:('q_%03d'%i if variant['edge_alias'] else n) for i,n in enumerate(es)}
    order=list(range(len(source['edges'])))[::-1 if variant['edge_reverse'] else 1]
    demand(packet['maps']==dict(node_names=nm,edge_names=em,edge_new_to_old=order),'변환 대응표')
    obs=packet['observation']
    demand(set(obs)==set(source) and obs['episode_id']==source['episode_id'] and obs['revision']==source['revision'], 'episode/revision 변경')
    demand(obs['start']==nm[source['start']] and obs['goal']==nm[source['goal']], 'endpoint 대응')
    expected=[]
    for j in order:
        e=source['edges'][j]
        expected.append(dict(id=em[e['id']],source=nm[e['source']],target=nm[e['target']],score=e['score']))
    demand(sha(obs['edges'])==sha(expected),'edge 순서/부호/위상 변경')
    return obs


def reference(doc: dict, generation: int) -> dict:
    t=doc['transitions'][generation]
    return dict(session_id=doc['session_id'],generation=generation,state_hash=t['after_state'],transition_hash=t['sha256'])


def check_seed(root, plan):
    from hcr import codec
    from hcr.model import AdaptiveConfig, Feedback
    from hcr.circuits import AdaptiveMemory
    from hcr.prior_policy import read_scope
    from hcr.evaluation.review_audit import packet_states
    from hcr.evaluation.prior_spec import training_world
    from hcr.evaluation.reference import assess
    seed=io.load(root/'upstream/seed/6.json');old=io.load(root/'upstream/plan.json')
    _,report=packet_states(seed);c=seed['document']['engine'];cfg=AdaptiveConfig()
    native_hashes={n:h for n,h in plan['dependency_source_hashes'].items() if n.startswith('src/hcr/')}
    demand(old['schema']=='hcr-exp15-plan-v1' and old['source_hashes']==native_hashes,'EXP-15 source baseline')
    demand(c['config']==codec.plain(cfg) and read_scope(c)=='legacy' and c['pending'] is None,'학습 config/scope')
    demand(c['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True),'학습 switches')
    demand(seed['document']['events'][0]['payload']['memory_document']==AdaptiveMemory.empty(cfg).document(),'빈 memory부터의 학습 계보')
    rows=io.load(root/'upstream/training.json')
    demand(len(rows)==6 and len(c['held'])==len(c['feedback'])==6,'학습 횟수')
    for i,row in enumerate(rows):
        w=training_world(i);dec=codec.adaptive_decision_from(row['decision'])
        assessment=assess(dec,w.observation,dict(w.hidden))
        demand(row==dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),
            decision=row['decision'],assessment=codec.plain(assessment)) and assessment.correct is True,'학습 원자료 평가')
        demand(c['held'][dec.id]['decision']==row['decision'],'학습 판단 계보')
        feedback=Feedback('f-'+dec.id,dec.id,w.observation.digest,assessment.correct,
                          assessment.proof_valid and assessment.assumption_correct is True)
        demand(c['feedback'][dec.id]==codec.plain(feedback),'학습 feedback 계보')
    demand(sha(c['memory'])==plan['memory_sha256'] and sha(c['config'])==plan['config_sha256'],'동결 memory/config')
    return c,old,report


def check_native(native: dict, obs: dict, seed_core: dict, scope: str, conditions: dict) -> tuple:
    from hcr.prior_policy import read_scope
    from hcr.evaluation.review_audit import packet_states
    from hcr.evaluation.selection_audit import audit_flow, source_view
    demand(set(native)=={'schema','status','initial_advances','initial_packet','initial_actions','baseline','flow','wall_seconds'},'native 결과 필드')
    demand(native['schema']=='hcr-input-native-r036-v1' and type(native['wall_seconds']) in (int,float)
           and isfinite(native['wall_seconds']) and native['wall_seconds']>=0,'native schema/time')
    packet=native['initial_packet'];doc=packet['document'];states,initial_audit=packet_states(packet)
    ops=[t['operation'] for t in doc['transitions']];count=native['initial_advances']
    demand(type(count) is int and 0<=count<=conditions['max_initial_advances'],'초기 advance 한도')
    demand(ops==['init','begin']+['advance']*count,'초기 계산에 개입/재시작 포함')
    core=doc['engine'];p=core['pending']
    demand(doc['session_id']=='input-r036-'+scope+'-'+sha(obs)[:20],'새 실행 session identity')
    for c in states.values():
        demand(c['memory']==seed_core['memory'] and c['config']==seed_core['config'],'동결 memory/config 변경')
        demand(read_scope(c)==scope and c['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True),'scope/switches 변경')
        demand(not c['held'] and not c['feedback'] and not c['requests'],'새 session에 과거 attempt 유입')
    demand(p is not None and p['observation']==obs and p['mode']=='frozen_eval','native 입력 출처')
    demand(not states[1]['pending']['ready'],'begin에서 예기치 않은 즉시 readout')
    expected=[dict(operation='begin_committed',reference=reference(doc,1),phase='running')]
    for g in range(2,len(ops)):
        before=states[g-1]['pending'];after=states[g]['pending']
        demand(before is not None and not before['ready'],'첫 판단을 건너뛴 초기 실행')
        expected.append(dict(operation='advance_requested',reference=reference(doc,g-1),kernel_ticks=before['cost']['kernel_ticks']))
        expected.append(dict(operation='advance_committed',reference=reference(doc,g),
            phase='readout_ready' if after['ready'] else 'running',kernel_ticks=after['cost']['kernel_ticks']))
    if native['status']=='initial_budget_exhausted':
        demand(count==conditions['max_initial_advances'] and not p['ready'] and native['baseline'] is None and native['flow'] is None,
               '가짜 최초 보류/초기 예산 종료')
        demand(native['initial_actions']==expected,'초기 stream 기록')
        return dict(initial_audit=initial_audit,continuation_audit=None,kernel_ticks=p['cost']['kernel_ticks'],
                    extra_kernel_ticks=0,advances=count,status=native['status'],stop_reason='initial_budget_exhausted',
                    terminal_pending_ready=False),[],expected
    demand(native['status']=='readout_ready' and p['ready'],'초기 경계 불일치')
    b=native['baseline'];run=native['flow']
    demand(b['ready']==packet and b['judgment_prior']==scope and b['observation']==obs,'공유 baseline 출처')
    demand(run['arm']==conditions['continuation_policy']=='expand_only' and run['limits']==conditions['continuation_limits'], '후속 개입 범위')
    demand(run['selection_limits']==conditions['selection_limits'],'원 selection 예산 baseline')
    continuation_audit=audit_flow(b,run)
    demand(not run['selections'] and run['usage']['selection_calls']==0 and run['usage']['restarts']==0,'후속 계산에 selector/restart 개입')
    expected.append(dict(operation='first_readout',candidate_id=b['first']['candidate_id'],generation=len(ops)-1))
    demand(native['initial_actions']==expected,'초기 first-attempt 로그')
    log=expected+[dict(operation='continuation_action',record=a) for a in run['actions']]
    views=[]
    for candidate in run['candidates']:
        raw=source_view(candidate)
        v={k:deepcopy(raw[k]) for k in ('observation','raw_value','state','completed_paths','graph_complete','original_proof','min_abs_score')}
        v['schema']='hcr-frozen-proof-view-r035-v1';view_check(v);views.append(v)
    final=run['segments'][-1]['document']['engine']['pending']
    return dict(initial_audit=initial_audit,continuation_audit=continuation_audit,
        kernel_ticks=run['cost']['pathway_kernel_ticks'],extra_kernel_ticks=run['usage']['extra_kernel_ticks'],
        advances=count+run['usage']['extra_advances'],status=native['status'],stop_reason=run['result']['reason'],
        terminal_pending_ready=final['ready'],native_cost_counters=final['cost'],
        native_proof_nodes=run['cost']['native_proof_nodes']),views,log


def check_readouts(raw: dict, views: list[dict], case: dict) -> tuple[list,list]:
    outputs=raw['readouts'];native=raw['native'];rows=[];reports=[]
    candidates=[] if native['flow'] is None else native['flow']['candidates']
    demand(len(outputs)==len(views)==len(candidates),'native readout/정책 비교 population')
    for ordinal,(saved,view,candidate) in enumerate(zip(outputs,views,candidates)):
        demand(set(saved)=={'ordinal','candidate_id','candidate_sha256','input_sha256','results'} and
            type(saved['ordinal']) is int and saved['ordinal']==ordinal and saved['candidate_id']==candidate['candidate_id'] and
            saved['candidate_sha256']==sha(candidate) and saved['input_sha256']==sha(view),'정책 입력 출처')
        results=saved['results'];demand(set(results)=={'native_saved','native_rebuild','support_first'},'정책 population')
        audits={}
        for policy,result in results.items():
            demand(result['policy']==policy,'정책 이름 결합');audits[policy]=audit_result(view,result)
        demand(results['native_saved']['value'] is candidate['readout']['value'] and
            results['native_saved']['accepted'] is candidate['readout']['accepted'],'native gate/source 불일치')
        demand(results['native_rebuild']['proof']==view['original_proof'],'동일 상태 native 재구성 불일치: evaluator disagreement')
        world_results={policy:{name:dict(expected=reachable(case['observation'],world),
            external_correct=None if result['value'] is None else result['value'] is reachable(case['observation'],world))
            for name,world in case['worlds'].items()} for policy,result in results.items()}
        canon=canonical_state(view,results,raw['transformed']['maps']['edge_names'])
        row=dict(trial_id=raw['trial']['id'],case=case['name'],scope=raw['trial']['scope'],variant=raw['trial']['variant']['id'],
            ordinal=ordinal,first_readout=ordinal==0,last_available_readout=ordinal==len(views)-1,
            native_candidate_id=candidate['candidate_id'],native_kernel_ticks_at_readout=candidate['decision']['cost']['kernel_ticks'],
            convergence=candidate['decision'].get('convergence'),canonical=canon,
            diagnostic=diagnose_state(view,candidate,results),world_results=world_results,
            selection_usage={k:v['usage'] for k,v in results.items()})
        rows.append(row);reports.append(audits)
    return rows,reports
