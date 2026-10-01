"""R0.3 독립 스케줄·메시지·예산 감사. 생성기의 methods/integration/runtime을 호출하지 않는다.

각 worker의 수치·proof·상태 전이는 기존 session_audit의 독립 replay로 검사한다.
이 감사의 판정은 기록의 일관성이며 외부 환경이나 인간의 사고 메커니즘의 증명이 아니다.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from dataclasses import fields
from math import isfinite
from .. import codec, session_io
from ..model import AdaptiveCost, ContractError, fingerprint
from ..trace import check_chain
from .session_audit import verify_document
from .audit import require

_ALLOWED = ('sequential','associative','fixed','adaptive','fixed_no_messages','adaptive_no_messages')


def _cost(core):
    if core['pending'] is not None:
        result = {f.name: core['pending']['cost'][f.name] for f in fields(AdaptiveCost)}
        result['wall_seconds'] = core['pending']['active_seconds']
        return result
    return {f.name: next(iter(core['held'].values()))['decision']['cost'][f.name] for f in fields(AdaptiveCost)}


def _phase(core):
    p = core['pending']
    return 'idle' if p is None else 'readout_ready' if p['ready'] else 'running'


def verify_result(record, *, check_source=True):
    try:
        return _verify_result(record, check_source=check_source)
    except ContractError:
        raise
    except (KeyError, ValueError, TypeError, IndexError, AttributeError) as error:
        raise ContractError('malformed R0.3 result: ' + str(error)) from error


def _verify_result(r, *, check_source):
    require(r['schema'] == 'hcr-method-result-r03-v1', 'R0.3 schema')
    arm = r['arm']; require(arm in _ALLOWED, 'unknown M arm')
    obs = codec.observation_from(r['observation'])
    config = codec.adaptive_config_from(r['adaptive_config'])
    mc = r['method_config']
    require(set(mc) == {'max_advances','max_kernel_ticks','max_messages','first_method'}, 'method config fields')
    for k, limit in (('max_advances',256),('max_kernel_ticks',100000),('max_messages',1024)):
        require(type(mc[k]) is int and 0 <= mc[k] <= limit, 'method budget type/range')
    require(mc['first_method'] in ('sequential','associative'), 'first method')
    names = [arm] if arm in ('sequential','associative') else ['sequential','associative']
    order = list(dict.fromkeys(k for k in (mc['first_method'],'sequential','associative') if k in names))
    enabled = len(names) > 1 and not arm.endswith('_no_messages')
    require(r['methods'] == names and set(r['workers']) == set(names), 'worker inventory')
    require(fingerprint(r['initial_memory']) == r['memory_digest'], 'seed memory hash')
    states, reports = {}, {}
    for name in names:
        packet = r['workers'][name]; doc = packet['document']
        expected_schema = 'hcr-session-checkpoint-r03-v1' if any(t['operation']=='prioritize_frontier' for t in doc['transitions']) else 'hcr-session-checkpoint-r021-v1'
        require(packet['schema'] == expected_schema
                and packet['sha256'] == fingerprint(doc), 'worker packet hash')
        if check_source:
            require(doc['source_hashes'] == session_io.source_hashes(), 'source differs')
        require(doc['session_id'] == 'r03-' + name, 'worker session identity')
        timeline = {}
        reports[name] = verify_document(doc, state_observer=lambda g, c: timeline.__setitem__(g, c))
        states[name] = timeline
        require(doc['engine']['config'] == r['adaptive_config'], 'worker config differs')
        require(doc['engine']['switches'] == dict(use_circuits=name=='associative',top_down=True,allow_reexpansion=True), 'method flags')
        require(doc['engine']['memory'] == r['initial_memory']
                and timeline[0]['memory'] == r['initial_memory'], 'worker changed seed')
        require(doc['transitions'][1]['operation']=='begin'
                and timeline[1]['pending']['observation']==r['observation']
                and timeline[1]['pending']['mode']=='frozen_eval', 'public observation initialization')
        require(all(t['operation'] in ('init','begin','prioritize_frontier','advance','finish')
                    for t in doc['transitions']), 'learning or revision in frozen method comparison')
    events = r['controller']
    check_chain(events, len(events), events[-1]['sha256'])
    require(events[0]['event']=='r03_start' and events[0]['payload']==dict(
        observation=r['observation'], memory_digest=r['memory_digest'], adaptive_config=r['adaptive_config'],
        method_config=mc, arm=arm, methods=names, order=order, messages_enabled=enabled), 'scheduler start')
    pointer = {k:1 for k in names}; inbox={k:[] for k in names};guidance={k:[] for k in names};last={k:-1 for k in names}
    used=turn=sent=consumed=changed=0;seen=set();decisions={};i=1;boundary=False
    def event(kind):
        nonlocal i
        require(i < len(events) and events[i]['event'] == kind, 'controller order expected ' + kind)
        payload = events[i]['payload'];i+=1
        return payload
    while True:
        current = {k: states[k][pointer[k]] for k in names}
        running = [k for k in order if _phase(current[k])=='running']
        if not running:
            break
        if turn >= mc['max_advances']:
            p = event('r03_stopped')
            require(p==dict(reason='shared_advance_budget', used_advances=turn,used_kernel_ticks=used,
                            unused_kernel_ticks=mc['max_kernel_ticks']-used), 'shared advance stop')
            boundary=True;break
        reservations = {}
        for k in running:
            c=current[k]; pool=c['switches']['use_circuits'] and bool(c['memory']['circuits']) and c['pending']['revision_of'] is None
            reservations[k]=config.kernel.max_ticks*(1+int(pool))
        feasible=[k for k in running if reservations[k] <= mc['max_kernel_ticks']-used]
        if not feasible:
            p=event('r03_stopped')
            require(p==dict(reason='conservative_tick_admission', used_advances=turn,used_kernel_ticks=used,
                unused_kernel_ticks=mc['max_kernel_ticks']-used,reservations=reservations),'tick admission stop')
            boundary=True;break
        if arm.startswith('adaptive'):
            k=max(feasible,key=lambda k:(bool(inbox[k]),current[k]['pending']['mismatch']['magnitude'],
                                        -last[k],-order.index(k)))
            reason='peer_hint_then_mismatch_then_age'
        else:
            k=next(order[(turn+n)%len(order)] for n in range(len(order)) if order[(turn+n)%len(order)] in feasible)
            reason='fixed_round_robin'
        p=event('r03_scheduled')
        frontier=current[k]['pending']['workspace']['frontier']
        default=min(frontier,key=lambda v:(len(v['path']),tuple(v['path'])))['path'] if k=='sequential' else frontier[0]['path']
        chosen=default; selected=None; priority_reason='breadth_first_primitive' if k=='sequential' else 'depth_first_macro'
        available_hints=guidance[k]+inbox[k]
        for h in reversed(available_hints):
            matches=[v for v in frontier if v['path']==h['path'][:len(v['path'])]]
            if matches:
                chosen=min(matches,key=lambda v:(-len(v['path']),tuple(v['path'])))['path']
                selected=h['id'];priority_reason='peer_path_hint';break
        ids=[h['id'] for h in inbox[k]];consumed+=len(ids);guidance[k]=available_hints;inbox[k]=[]
        expected=dict(turn=turn,worker=k,reason=reason,before_generation=pointer[k],reservation_ticks=reservations[k],
            used_kernel_ticks=used,selected_path=chosen,default_path=default,priority_reason=priority_reason,
            selected_hint_id=selected,consumed_hint_ids=ids)
        require(p==expected,'scheduler read unauthorized state or lost/mutated hint')
        changed+=int(chosen!=default)
        doc=r['workers'][k]['document']; ts=doc['transitions'];before=pointer[k]
        require(ts[before+1]['operation']=='prioritize_frontier' and ts[before+1]['arguments']==dict(path=chosen), 'unapplied priority')
        require(ts[before+2]['operation']=='advance', 'missing worker quantum')
        g=before+2
        additions=[]
        if enabled:
            peer=next(n for n in names if n!=k)
            for e in doc['events'][ts[g]['event_start']:ts[g]['event_end']]:
                if e['event']!='r02_expansion':continue
                primary=e['payload']['prefix']['path']+e['payload']['candidate']['edges']
                for prefix in e['payload']['added']:
                    if prefix['path']!=primary:continue
                    h=dict(sender=k,receiver=peer,observation_digest=obs.digest,observation_revision=obs.revision,
                        memory_digest=r['memory_digest'],path=prefix['path'],
                        roles=[[f'R{n}',v] for n,v in enumerate(prefix['visited'])],
                        evidence_refs=[obs.digest+':'+obs.edges[slot].id for slot in prefix['path']],
                        source_event_seq=e['seq'],source_event_sha256=e['sha256'],source_generation=g,port='public_path_hint_v1')
                    additions.append(dict(id='hint-'+fingerprint(h),**h))
        if _phase(states[k][g])=='readout_ready':
            require(ts[g+1]['operation']=='finish','unfinalized component')
            g+=1;decisions[k]=next(iter(states[k][g]['held'].values()))['decision']
        before_cost, after_cost = _cost(current[k]), _cost(states[k][g])
        delta={n:after_cost[n]-before_cost[n] for n in before_cost}
        require(0<=delta['kernel_ticks']<=reservations[k], 'quantum reservation exceeded')
        p=event('r03_advanced')
        require(p==dict(turn=turn,worker=k,after_generation=g,phase=_phase(states[k][g]),cost_delta=delta,
                        provisional_value=decisions[k]['value'] if k in decisions else None), 'counter/provisional readout mismatch')
        pointer[k]=g;used+=delta['kernel_ticks'];last[k]=turn;turn+=1
        for h in additions:
            key=(h['sender'],h['receiver'],tuple(h['path']))
            if key in seen:continue
            seen.add(key)
            if sent>=mc['max_messages']:
                require(event('r03_message_dropped')==dict(id=h['id'],reason='message_budget'),'message budget drop');continue
            require(event('r03_message')==h,'message is not derived from the actual sender state')
            inbox[h['receiver']].append(h);sent+=1
    require(all(pointer[k]==len(r['workers'][k]['document']['transitions'])-1 for k in names), 'unaccounted worker computation')
    require(r['decisions']==decisions,'component decision substitution')
    vals={k:v['value'] for k,v in decisions.items()};all_done=set(vals)==set(names)
    resolved=all_done and all(v is not None for v in vals.values())
    value=next(iter(vals.values())) if resolved and len(set(vals.values()))==1 else None
    if value is not None:status='single_method' if len(names)==1 else 'agreement'
    elif len({v for v in vals.values() if v is not None})>1:status='conflict_abstention'
    else:status='incomplete_or_ambiguous'
    refs=sorted({obs.digest+':'+eid for d in decisions.values() for eid,_ in d['proof']['assumed_edges']})
    result=dict(value=value,status=status,component_values=vals,all_methods_finished=all_done,
        supporting_decision_ids={k:v['id'] for k,v in decisions.items()},unique_evidence_refs=refs,
        component_proofs={k:v['proof'] for k,v in decisions.items()},evidence_count_is_confidence=False,
        fabricated_combined_proof=False,external_truth_used=False,memory_updated=False)
    require(r['result']==result,'integration consensus/abstention/evidence contract')
    require(event('r03_integrated')==dict(result=result,used_advances=turn,used_kernel_ticks=used,
        messages_sent=sent,budget_boundary=boundary) and i==len(events),'integration/extra controller events')
    cost=Counter()
    for k in names:cost.update(_cost(states[k][pointer[k]]))
    require(r['cost']==dict(cost),'total method counters mismatch')
    require(r['budget']==dict(used_advances=turn,used_kernel_ticks=used,max_advances=mc['max_advances'],
        max_kernel_ticks=mc['max_kernel_ticks'],unused_kernel_ticks=mc['max_kernel_ticks']-used,
        messages_sent=sent,max_messages=mc['max_messages'],budget_boundary=boundary),'shared budget report')
    require(cost['kernel_ticks']==used and used<=mc['max_kernel_ticks'] and turn<=mc['max_advances'], 'global budget violation')
    timing=r['timing']
    for key in ('total_wall_seconds','initialization_seconds','engine_active_seconds','management_seconds','checkpoint_io_seconds'):
        require(type(timing[key]) in (int,float) and isfinite(timing[key]) and timing[key]>=0,'timing range')
    require(timing['engine_active_seconds']==cost['wall_seconds'] and timing['checkpoint_io_seconds']==0.0
        and timing['management_seconds']==max(0.0,timing['total_wall_seconds']-cost['wall_seconds']), 'timing scopes')
    require(r['boundaries']==dict(memory_updated=False,learning_policy_changed=False,prior_policy_changed=False,
        message_drives_injected=False,disk_checkpoint_in_interleaving=False,os_parallelism=False,
        kernel_tick_preemption=False,conservative_reservation_can_leave_unused_budget=True),'scope flags')
    return dict(schema='hcr-method-audit-r03-v1',verified=True,source_checked=check_source,
        advances_checked=turn,messages_checked=sent,messages_consumed=consumed,priority_changes=changed,
        scalar_ticks_replayed=sum(v['scalar_ticks_replayed'] for v in reports.values()),
        worker_audits=reports,new_inferences=0,external_truth_evaluated=False,
        scheduler_replayed=True,wall_time_reproduced=False)
