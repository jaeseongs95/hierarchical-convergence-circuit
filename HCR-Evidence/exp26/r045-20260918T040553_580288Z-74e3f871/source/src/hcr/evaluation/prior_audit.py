"""EXP-12 수치/정책/입력/seed/조건 감사. production runtime/dynamics/learning을 실행하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from math import isfinite
from .. import codec, session_io
from ..model import AdaptiveCost, fingerprint
from ..prior_policy import read_scope
from ..trace import check_chain
from .audit import require, independent_step
from .adaptive_audit_support import decision_network
from .session_audit import verify_document
from .reference import assess, reachable


def audit_packet(packet):
    require(set(packet)=={'schema','document','sha256'} and packet['sha256']==fingerprint(packet['document']), 'session checksum')
    doc=packet['document'];scope=read_scope(doc['engine'])
    schema=('hcr-session-checkpoint-r031-v1' if scope=='route_only' else
            'hcr-session-checkpoint-r03-v1' if any(t['operation']=='prioritize_frontier' for t in doc['transitions']) else
            'hcr-session-checkpoint-r021-v1')
    require(packet['schema']==schema,'policy schema')
    require(doc['source_hashes']==session_io.source_hashes(),'verifier source differs; use frozen source')
    return verify_document(doc)


def verify_task(raw, case, n, arm, seed_memory, config):
    from .prior_spec import arm_options
    require(set(raw)=={'schema','training_count','case','family','arm','use_circuits','judgment_prior',
                       'observation','initial_memory','packet','decision','timing'},'task fields')
    require(raw['schema']=='hcr-exp12-task-r031-v1' and raw['case']==case['name'] and raw['family']==case['family']
            and raw['training_count']==n and type(raw['training_count']) is int and raw['arm']==arm,'cell identity')
    require(raw['observation']==case['observation'] and raw['initial_memory']==seed_memory,'paired input/memory')
    require(type(raw['use_circuits']) is bool and {k:raw[k] for k in arm_options(arm)}==arm_options(arm),'prior ablation flags')
    report=audit_packet(raw['packet']);doc=raw['packet']['document'];core=doc['engine']
    require(core['config']==codec.plain(config) and core['memory']==seed_memory
            and doc['events'][0]['payload']['memory_document']==seed_memory,'frozen configuration/memory')
    require(core['switches']==dict(use_circuits=arm!='graph_only',top_down=True,allow_reexpansion=True)
            and read_scope(core)==raw['judgment_prior'],'engine policy binding')
    require(len(core['held'])==1 and len(core['attempts'])==1 and core['pending'] is None
            and not core['feedback'] and not core['requests'],'single frozen inference, no retry')
    require(all(t['operation'] in ('init','begin','advance','finish') for t in doc['transitions']), 'unexpected method/learning intervention')
    held=next(iter(core['held'].values()))
    require(held['observation']==raw['observation'] and held['decision']==raw['decision']
            and raw['decision']['mode']=='frozen_eval','decision/observation provenance')
    timing=raw['timing']
    require(set(timing)=={'total_wall_seconds','initialization_seconds','engine_active_seconds','management_seconds','packet_seconds'},'timing schema')
    require(all(type(v) in (int,float) and isfinite(v) and v>=0 for v in timing.values()),'timing range')
    require(timing['engine_active_seconds']==raw['decision']['cost']['wall_seconds']
            and timing['management_seconds']==max(0.0,timing['total_wall_seconds']-timing['engine_active_seconds'])
            and timing['initialization_seconds']<=timing['total_wall_seconds'],'timing scope')
    obs=codec.observation_from(raw['observation']);d=codec.adaptive_decision_from(raw['decision'])
    outcomes={name:codec.plain(assess(d,obs,truth)) for name,truth in case['worlds'].items()}
    return dict(schema='hcr-exp12-task-audit-v1',verified=True,task_inferences=1,
                scalar_ticks_replayed=report['scalar_ticks_replayed'],graph_steps_checked=report['graph_steps_checked'],
                worlds_evaluated=len(outcomes),new_inferences=0),outcomes


def source_network(raw):
    networks=[e for e in raw['packet']['document']['events'] if e['event']=='r02_network' and e['payload']['kind']=='decision']
    require(networks,'legacy has no final decision network')
    event=networks[-1]
    return event,dict(event_seq=event['seq'],event_sha256=event['sha256'],
                      program_digest=event['payload']['program_digest'],decision_id=raw['decision']['id'])


def verify_fixed(raw, legacy):
    require(set(raw)=={'schema','training_count','case','scope','source_ref','config','program','initial',
                       'drives','events','state','convergence','cost'},'fixed diagnostic fields')
    require(raw['schema']=='hcr-exp12-fixed-network-v1' and raw['scope'] in ('legacy','route_only'),'fixed schema/policy')
    event,ref=source_network(legacy);p=event['payload'];doc=legacy['packet']['document']
    require(raw['training_count']==legacy['training_count'] and raw['case']==legacy['case']
            and raw['source_ref']==ref and raw['config']==doc['engine']['config'],'fixed source provenance')
    obs=codec.observation_from(legacy['observation']);cfg=codec.adaptive_config_from(raw['config'])
    program,drives=decision_network(obs,p['metadata']['routes'],cfg,judgment_prior=raw['scope'])
    initial={g['id']:.5 for g in program['groups']}
    require(raw['program']==p['program']==program and raw['initial']==initial and raw['drives']==drives,'fixed structure/drive mismatch')
    # For the legacy member this is also a replay of the actually executed network drives.
    if raw['scope']=='legacy':require(drives==p['drives'],'fixed legacy is not the original network')
    events=raw['events'];check_chain(events,len(events),events[-1]['sha256'])
    require(events[0]['event']=='r02_network' and events[-1]['event']=='r02_settled','fixed trace bounds')
    expected0=dict(network_id='network-0',decision_id='fixed-network',kind='decision',program=program,
                   program_digest=fingerprint(program),drives=drives,top_down=True,
                   metadata=dict(fixed_network=True,source_ref=ref,scope=raw['scope']))
    require(events[0]['payload']==expected0,'fixed start metadata')
    state=initial;stable=0;history=[];conv=None;cost=AdaptiveCost()
    for e in events[1:-1]:
        require(conv is None and e['event']=='r02_tick','extra/premature fixed tick')
        t=e['payload'];require(t['network_id']=='network-0' and t['decision_id']=='fixed-network','fixed tick binding')
        nxt=independent_step(program,state,drives,cfg.kernel,True)
        require(set(t['state'])==set(nxt) and all(isfinite(v) and abs(v-nxt[k])<2e-12 for k,v in t['state'].items()),'fixed recurrence')
        residual=max(abs(nxt[k]-state[k]) for k in nxt)
        stable=stable+1 if residual<=cfg.kernel.residual_tolerance else 0
        cost.kernel_ticks+=1;cost.group_updates+=len(nxt);cost.normalization_ops+=len(nxt)
        cost.signal_transmissions+=len(program['links'])
        require(t['tick']==cost.kernel_ticks and cost.kernel_ticks<=cfg.kernel.max_ticks and t['stable_steps']==stable
                and abs(t['residual']-residual)<2e-12,'fixed tick/residual contract')
        oscillating=bool(history and residual>cfg.kernel.residual_tolerance*10
                         and max(abs(nxt[k]-history[-1][k]) for k in nxt)<cfg.kernel.residual_tolerance)
        actual=t['state'];margin=abs(2*actual['goal']-1)
        if stable>=cfg.kernel.patience:status='stable_decision' if margin>=cfg.kernel.margin_threshold else 'stable_ambiguous'
        elif oscillating:status='oscillating'
        elif cost.kernel_ticks==cfg.kernel.max_ticks:status='budget_exhausted'
        else:status=None
        if status:conv=dict(status=status,ticks=cost.kernel_ticks,residual=t['residual'],margin=margin,stable_steps=stable)
        history=(history+[state])[-3:];state=actual
    require(conv is not None,'fixed network stopped without a terminal condition')
    require(events[-1]['payload']==dict(network_id='network-0',decision_id='fixed-network',state=state,convergence=conv), 'fixed settled')
    require(raw['state']==state and raw['convergence']==conv and raw['cost']==cost.snapshot(),'fixed endpoint/cost')
    return dict(verified=True,scalar_ticks_replayed=cost.kernel_ticks,new_inferences=0,
                fixed_network_is_not_full_inference=True)


def fixed_pair(left,right,legacy):
    verify_fixed(left,legacy);verify_fixed(right,legacy)
    require(left['scope']=='legacy' and right['scope']=='route_only','fixed pair ordering')
    return dict(training_count=left['training_count'],case=left['case'],same_program=left['program']==right['program'],
                same_initial=left['initial']==right['initial'],legacy_goal=left['state']['goal'],
                route_only_goal=right['state']['goal'],legacy_ticks=left['cost']['kernel_ticks'],
                route_only_ticks=right['cost']['kernel_ticks'],
                scalar_ticks_replayed=left['cost']['kernel_ticks']+right['cost']['kernel_ticks'])
