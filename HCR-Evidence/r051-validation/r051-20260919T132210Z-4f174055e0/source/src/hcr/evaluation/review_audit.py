"""EXP-14 독립 controller/관측/비용 검산. review.py·runtime을 실행하지 않는다.

R0.2.1 상태 재생과 R0.3.2 지지 계약 검산은 재사용한다. snapshot마다 prefix를
중복 검사하지만 통계의 표본/비용에는 각 segment의 실제 전개를 한 번만 합산한다.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import fields
from math import isfinite
from .. import codec, session_io
from ..model import AdaptiveCost, fingerprint
from ..prior_policy import read_scope
from ..trace import check_chain
from .audit import require
from .session_audit import verify_document
from .grounding_audit import verify_diagnostic, verify_readout, compatible_worlds
from .reference import reachable, assess

POLICIES = ('hold', 'expand_only', 'observe_first', 'expand_then_observe', 'route_review')


def finite(v):
    return type(v) in (int, float) and isfinite(v) and v >= 0


def seal_check(packet, schema):
    require(packet.get('schema') == schema and packet.get('sha256') == fingerprint({k:v for k,v in packet.items() if k!='sha256'}), 'review seal')


def packet_states(packet):
    require(set(packet)=={'schema','document','sha256'} and packet['sha256']==fingerprint(packet['document']), 'session packet seal')
    doc=packet['document']
    require(doc['source_hashes']==session_io.source_hashes(), 'audit source differs; retain original source')
    ops=[t['operation'] for t in doc['transitions']]
    expected=('hcr-session-checkpoint-r033-v1' if 'continue_dependency' in ops else
              'hcr-session-checkpoint-r031-v1' if read_scope(doc['engine'])=='route_only' else
              'hcr-session-checkpoint-r03-v1' if 'prioritize_frontier' in ops else 'hcr-session-checkpoint-r021-v1')
    require(packet['schema']==expected,'review session schema')
    states={}
    audit=verify_document(doc,state_observer=lambda g,c:states.__setitem__(g,c))
    return states,audit


def verify_candidate(candidate, segment, states):
    ref=candidate['reference'];g=ref['generation'];doc=segment['document'];finished=candidate['packet']
    require(type(g)is int and g in states and states[g]['pending']['ready'], 'candidate from wrong boundary')
    j=doc['transitions'][:g+1];events=doc['events'][:j[-1]['event_end']]
    snap=dict(session_id=doc['session_id'],source_hashes=doc['source_hashes'],engine=states[g],events=events,transitions=j)
    require(ref['ready_sha256']==fingerprint(snap) and ref['finished_sha256']==finished['sha256']
            and candidate['candidate_id']=='review-candidate-'+fingerprint(ref),'candidate global identity')
    fd=finished['document']
    require(fd['transitions'][:-1]==j and fd['events'][:-1]==events and fd['transitions'][-1]['operation']=='finish',
            'candidate is not an unmodified finish branch')
    require(fd['events'][-1]['event']=='r02_decision' and fd['events'][-1]['payload']==candidate['decision'],'candidate decision source')
    _,audit=packet_states(finished)
    raw=dict(observation=states[g]['pending']['observation'],decision=candidate['decision'],packet=finished)
    verify_diagnostic(raw,candidate['diagnostic']);verify_readout(raw,candidate['diagnostic'],candidate['readout'],'dependency_gate')
    require(finite(candidate['capture_seconds']) and finite(candidate['proof_finish_seconds'])
            and candidate['proof_finish_seconds']==candidate['decision']['cost']['wall_seconds']-states[g]['pending']['active_seconds'],
            'proof readout time accounting')
    return audit


def next_action(policy,core,candidate,used,limits,switched):
    # 별도 구현: controller의 호출 순서/예산/관측 대상을 기록에서 재계산한다.
    p=core['pending']
    bound=core['config']['kernel']['max_ticks']*(2 if core['switches']['use_circuits'] and p['revision_of'] is None and core['memory']['circuits'] else 1)
    affordable=used['extra_advances']<limits['max_extra_advances'] and used['extra_kernel_ticks']+bound<=limits['max_extra_kernel_ticks']
    if p['ready'] and candidate is not None and candidate['readout']['accepted']:return 'stop_supported',None
    if policy=='hold':return 'stop_gate',None
    if p['failure_reason'] is not None:return 'stop_engine_failure',None
    if not p['ready']:return ('advance',None) if affordable else ('stop_compute_budget',None)
    if policy=='route_review':
        if switched:return 'stop_review_finished',None
        return ('restart_route_only',None) if affordable else ('stop_compute_budget',None)
    if policy in ('expand_only','expand_then_observe') and p['workspace']['frontier']:
        return ('continue_dependency',None) if affordable else ('stop_compute_budget',None)
    if policy=='expand_only':return 'stop_frontier_exhausted',None
    if used['measurements']>=limits['max_measurements']:return 'stop_measurement_budget',None
    if not affordable:return 'stop_compute_budget',None
    if candidate is None:return 'stop_no_diagnostic',None
    ids=candidate['diagnostic']['suggestion']['edge_ids']
    return ('request_measurement',ids[0]) if ids else ('stop_no_measurement_target',None)


def audit_rollout(baseline,run,*,world=None,provider_mode=None):
    seal_check(baseline,'hcr-review-baseline-r033-v1')
    require(set(run)=={'schema','baseline_sha256','policy','limits','candidates','segments','controller','result','usage','cost','timing','boundaries'},'review result fields')
    require(baseline['ready']['sha256']==fingerprint(baseline['ready']['document'])
        and baseline['first']['reference']['ready_sha256']==baseline['ready']['sha256']
        and baseline['first']['reference']['segment']==0
        and baseline['first']['reference']['generation']==len(baseline['ready']['document']['transitions'])-1,'initial snapshot/candidate lineage')
    require(run['schema']=='hcr-review-result-r033-v1' and run['baseline_sha256']==baseline['sha256'], 'rollout baseline')
    require(run['policy'] in POLICIES,'unknown controller')
    limits=run['limits']
    require(set(limits)=={'max_extra_advances','max_extra_kernel_ticks','max_measurements'},'limits fields')
    require(all(type(limits[k])is int and 0<=limits[k]<=n for k,n in [('max_extra_advances',128),('max_extra_kernel_ticks',100000),('max_measurements',16)]),'limit bounds')
    segments=run['segments'];require(segments and len(segments)<=18,'segment bound')
    state_maps=[];reports=[]
    bdoc=baseline['ready']['document'];memory=bdoc['engine']['memory'];config=bdoc['engine']['config']
    base_g=len(bdoc['transitions'])-1
    for i,p in enumerate(segments):
        sm,au=packet_states(p);state_maps.append(sm);reports.append(au)
        core=p['document']['engine']
        require(core['pending'] is not None and core['memory']==memory and core['config']==config
                and not core['held'] and not core['feedback'] and not core['requests'],'frozen continuation state')
        require(core['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True),'worker switches changed')
        require(set(t['operation'] for t in p['document']['transitions'])<={'init','begin','advance','continue_dependency'},'unlisted session intervention')
    sd=segments[0]['document']
    require(sd['transitions'][:base_g+1]==bdoc['transitions'] and sd['events'][:len(bdoc['events'])]==bdoc['events']
            and state_maps[0][base_g]==bdoc['engine'],'initial calculation rerun or changed')
    require(baseline['observation']==bdoc['engine']['pending']['observation'] and baseline['judgment_prior']==read_scope(bdoc['engine']), 'base input/scope')
    candidates=run['candidates'];require(candidates and candidates[0]==baseline['first'],'initial failure/readout not preserved')
    bykey={};byid={}
    for c in candidates:
        ref=c['reference'];i=ref['segment'];key=(i,ref['generation'])
        require(type(i)is int and 0<=i<len(segments) and key not in bykey and c['candidate_id'] not in byid,'duplicate/unbound candidate')
        verify_candidate(c,segments[i],state_maps[i]);bykey[key]=c;byid[c['candidate_id']]=c
    require(finite(baseline['preparation_seconds']),'baseline timing')
    trace=run['controller'];check_chain(trace,len(trace),trace[-1]['sha256'])
    require(trace[0]['event']=='review_start' and trace[0]['payload']==dict(baseline_sha256=baseline['sha256'],policy=run['policy'],
        limits=limits,initial_candidate=candidates[0]['candidate_id']),'controller start')
    pos=1;seg=0;gen=base_g;used=dict(extra_advances=0,extra_kernel_ticks=0,measurements=0,restarts=0)
    cand=candidates[0];switched=False;seen=[cand['candidate_id']];stop=None;turn=0
    def take(name):
        nonlocal pos
        require(pos<len(trace) and trace[pos]['event']==name,'unexpected controller event '+name)
        p=trace[pos]['payload'];pos+=1;return p
    while stop is None:
        core=state_maps[seg][gen];doc=segments[seg]['document'];tr=doc['transitions'][gen]
        ref=dict(session_id=doc['session_id'],generation=gen,state_hash=tr['after_state'],transition_hash=tr['sha256'])
        action,target=next_action(run['policy'],core,cand,used,limits,switched)
        require(take('review_action')==dict(turn=turn,action=action,target=target,segment=seg,reference=ref,
            source_candidate=None if cand is None else cand['candidate_id'],used=used),'controller decision differs')
        turn+=1
        if action.startswith('stop_'):stop=action;break
        if action in ('advance','continue_dependency'):
            require(gen+1 in state_maps[seg] and doc['transitions'][gen+1]['operation']==action,'missing/fabricated work')
            previous=core;gen+=1;core=state_maps[seg][gen]
            if action=='continue_dependency':cand=None
            else:
                used['extra_advances']+=1
                used['extra_kernel_ticks']+=core['pending']['cost']['kernel_ticks']-previous['pending']['cost']['kernel_ticks']
                if core['pending']['ready']:
                    require((seg,gen) in bykey,'missing actual candidate')
                    cand=bykey[(seg,gen)];seen.append(cand['candidate_id'])
                    require(take('review_candidate')==dict(candidate_id=cand['candidate_id'],reference=cand['reference'],
                        raw_value=cand['decision']['value'],accepted=cand['readout']['accepted']),'candidate controller binding')
        else:
            obs=deepcopy(core['pending']['observation']);scope=baseline['judgment_prior']
            if action=='request_measurement':
                used['measurements']+=1;req=take('review_measurement_request')
                seal_check(req,'hcr-review-measurement-request-v1')
                require({k:v for k,v in req.items() if k!='sha256'}==dict(schema='hcr-review-measurement-request-v1',ordinal=used['measurements'],
                    source_candidate_id=cand['candidate_id'],observation_digest=fingerprint(obs),episode_id=obs['episode_id'],
                    from_revision=obs['revision'],next_revision=obs['revision']+1,edge_ids=[target],
                    reason='selected_proof_or_explored_path_support_gap'),'measurement request scope')
                reply=take('review_measurement_response')
                require(set(reply)=={'request_sha256','status','scores','source'} and reply['request_sha256']==req['sha256']
                    and reply['status'] in ('measured','unavailable') and isinstance(reply['source'],str) and reply['source'],'response provenance')
                if reply['status']=='unavailable':
                    require(reply['scores']=={},'unavailable data');revised=None;status='measurement_unavailable'
                else:
                    require(set(reply['scores'])=={target},'unrequested observation')
                    score=reply['scores'][target]
                    require(score is None or (type(score) in (int,float) and isfinite(score) and -1<=score<=1),'score bounds')
                    prior=next(e for e in obs['edges'] if e['id']==target)['score']
                    if score==prior:revised=None;status='measurement_no_new_information'
                    else:
                        revised=deepcopy(obs);revised['revision']+=1
                        next(e for e in revised['edges'] if e['id']==target)['score']=score
                        status='measurement_applied'
                # 요청 선택에는 world를 쓰지 않았다. 아래는 실행 후 provider 충실도 검사다.
                if provider_mode is not None:
                    if provider_mode=='perfect':expected=dict(request_sha256=req['sha256'],status='measured',scores={target:.98 if world[target] else -.98},source='simulated_perfect_sensor')
                    elif provider_mode=='unchanged':expected=dict(request_sha256=req['sha256'],status='measured',scores={target:next(e['score'] for e in obs['edges'] if e['id']==target)},source='simulated_unchanged_sensor')
                    else:expected=dict(request_sha256=req['sha256'],status='unavailable',scores={},source='simulated_unavailable_sensor')
                    require(reply==expected,'provider reply differs from declared environment')
                require(take('review_measurement_consumed')==dict(status=status,observation=revised),'measurement revision')
                if revised is None:stop=status;break
                obs=revised
            else:switched=True;scope='route_only'
            require(gen==len(doc['transitions'])-1,'unused hidden computation in old segment')
            seg+=1;gen=1;used['restarts']+=1;cand=None
            require(seg<len(segments),'missing restart')
            nd=segments[seg]['document'];nc=state_maps[seg][1];t=nd['transitions'][1]
            require(nc['pending']['observation']==obs and read_scope(nc)==scope and nd['transitions'][0]['operation']=='init'
                    and nd['transitions'][1]['operation']=='begin','restarted input/policy')
            require(take('review_restarted')==dict(segment=seg,reason=action,observation=obs,judgment_prior=scope,
                initial_reference=dict(session_id=nd['session_id'],generation=1,state_hash=t['after_state'],transition_hash=t['sha256']),
                previous_work_discarded_from_cost=False),'restart provenance')
    require(seg==len(segments)-1 and gen==len(segments[seg]['document']['transitions'])-1,'extra unaccounted segment/work')
    require(seen==[c['candidate_id'] for c in candidates],'hidden/duplicated readout computation')
    accepted=cand is not None and cand['readout']['accepted'] and state_maps[seg][gen]['pending']['ready']
    value=cand['decision']['value'] if accepted else None;selected=cand['candidate_id'] if accepted else None
    require(take('review_finished')==dict(reason=stop,value=value,selected_candidate=selected,used=used) and pos==len(trace),'final trace')
    require(run['usage']==used and run['result']==dict(value=value,reason=stop,selected_candidate=selected),'final state/silent correction')
    require(used['extra_advances']<=limits['max_extra_advances'] and used['extra_kernel_ticks']<=limits['max_extra_kernel_ticks']
            and used['measurements']<=limits['max_measurements'],'shared budget exceeded')
    total={f.name:sum(p['document']['engine']['pending']['cost'][f.name] for p in segments) for f in fields(AdaptiveCost)}
    proof_items=sum(len(c['decision']['proof']['nodes']) for c in candidates)
    total['proof_nodes_reconstructed']+=proof_items
    total['wall_seconds']=sum(p['document']['engine']['pending']['active_seconds'] for p in segments)+sum(c['proof_finish_seconds'] for c in candidates)
    initial_ticks=bdoc['engine']['pending']['cost']['kernel_ticks']
    require(total['kernel_ticks']==initial_ticks+used['extra_kernel_ticks'],'cost reset/double count')
    require(run['cost']==dict(engine=total,initial_advances=sum(t['operation']=='advance' for t in bdoc['transitions']),
        initial_kernel_ticks=initial_ticks,extra_kernel_ticks=used['extra_kernel_ticks'],proof_readout_items=proof_items,
        measurement_features=used['measurements'],kernel_counters_exclude_controller=True),'cost ledger')
    require(all(finite(v) for k,v in run['timing'].items() if k!='measurement_latency_not_simulated'),'timing range')
    require(run['timing']['baseline_seconds']==baseline['preparation_seconds'] and run['timing']['candidate_capture_seconds']==sum(c['capture_seconds'] for c in candidates[1:])
        and run['timing']['measurement_latency_not_simulated'] is True,'timing scope')
    require(run['boundaries']==dict(original_decision_preserved=True,selected_value_requires_new_computation=True,
        candidate_id_is_global_local_engine_ids_can_repeat=True,frozen_memory=True,explicit_same_state_continuation=True,
        observation_restart_is_not_frontier_resume=True,policy_restart_is_not_free=True,no_hidden_world_input=True,
        no_host_proof_repair=True,no_claim_of_minimal_query=True,lifelong_learning=False,controller_checkpoint_resume=False),'boundary flags')
    return dict(verified=True,new_inferences=0,extra_advances=used['extra_advances'],extra_kernel_ticks=used['extra_kernel_ticks'],
        requests_checked=used['measurements'],candidate_readouts_checked=len(candidates),new_session_starts=used['restarts'],
        continuation_operations=sum(t['operation']=='continue_dependency' for p in segments for t in p['document']['transitions']),
        decision_rules_independently_reimplemented=True,session_and_grounding_auditors_reused=True)


def assess_rollout(baseline,run,world):
    initial_obs=codec.observation_from(baseline['observation'])
    expected=reachable(initial_obs,world)
    v=run['result']['value'];first=baseline['first'];last=run['candidates'][-1]
    final_obs=codec.observation_from(run['segments'][-1]['document']['engine']['pending']['observation'])
    comp=compatible_worlds(codec.plain(final_obs))
    return dict(expected=expected,external_correct=None if v is None else v==expected,
        initial_raw_correct=first['decision']['value'] is not None and first['decision']['value']==expected,
        initial_gated_value=first['readout']['value'],recovered_supported_output=first['readout']['value'] is None and v is not None,
        new_information=final_obs.digest!=initial_obs.digest,
        changed_conclusion=v is not None and v!=first['decision']['value'],
        unsupported_commitment=v is not None and last['diagnostic']['evidence_support_sufficient'] is not True,
        final_identifiable_under_sign_contract=comp['identifiable_under_sign_contract'],
        measured_edges=[e['payload']['edge_ids'][0] for e in run['controller'] if e['event']=='review_measurement_request'],
        # 이 지표는 초기 정보 기준의 비필수 질의를 표시한다. 실행 중 최적 질의 증명이 아니다.
        queries_on_initially_identifiable_input=run['usage']['measurements'] if compatible_worlds(baseline['observation'])['identifiable_under_sign_contract'] else 0)
