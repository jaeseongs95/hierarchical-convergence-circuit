"""Query-local representative arithmetic; unchanged native settle controller."""
from copy import deepcopy
from math import exp
from pathlib import Path
import time
from hcr import dynamics
from hcr.codec import plain,dumps
from hcr.model import Config,Cost,Program,Group,Link,fingerprint
from tools.r19_cross_level.probe import require,sha
from tools.r29_research_direction.partition import analyze
from tools.r29_research_direction.verify import verify

NATIVE_TICK=dynamics.tick
ROOT=Path(__file__).resolve().parents[2]

def prepare(entry,program,config):
    require(plain(program)==entry['program'] and plain(config)==entry['config'],'actual program/config binding')
    require(sha(ROOT/'src/hcr/dynamics.py')==entry['native_source_sha256'],'native binding')
    plan=analyze(entry);checked=verify(entry,plan)
    groups={g.id:g for g in program.groups};reps=[groups[c[0]] for c in plan['classes']]
    alias={k:c[0] for c in plan['classes'] for k in c}
    edges=[e for e in program.links if e.target in {g.id for g in reps} and (entry['top_down'] or e.kind!='top_down')]
    return plan,checked,reps,alias,edges

def run(entry,arm):
    cpu=time.process_time();wall=time.perf_counter();e=deepcopy(entry)
    cfg=Config(**e['config']);pr=e['program'];program=Program(tuple(Group(**g) for g in pr['groups']),tuple(Link(**v) for v in pr['links']),tuple(tuple(v) for v in pr['paths']),pr['edge_count'])
    program.validate(cfg);require(sha(ROOT/'src/hcr/dynamics.py')==e['native_source_sha256'],'native binding')
    binding=fingerprint(dict(program=plain(program),drives=e['drives'],initial=e['initial'],top_down=e['top_down'],config=plain(cfg),native_source_sha256=e['native_source_sha256']))
    require(binding==fingerprint(e),'query binding')
    pc=time.process_time();pw=time.perf_counter();plan=checked=None
    if arm=='shared':plan,checked,reps,alias,edges=prepare(e,program,cfg)
    else:require(arm=='native','arm')
    preparation=dict(cpu=time.process_time()-pc,wall=time.perf_counter()-pw)
    cost=Cost();ticks=[];work=dict(tick_calls=0,full_state_output_slots=0,alias_copy_slots=0)
    def step(p,current,drives,config,cost,*,top_down=True):
        work['tick_calls']+=1
        if arm=='native':
            nxt=NATIVE_TICK(p,current,drives,config,cost,top_down=top_down);work['full_state_output_slots']+=len(nxt);return nxt
        totals={g.id:g.bias+drives.get(g.id,0.0) for g in reps}
        for edge in edges:
            totals[edge.target]+=edge.weight*(2*current[edge.source]-1);cost.signal_transmissions+=1
        computed={}
        for g in reps:
            old=current[g.id];drive=totals[g.id]
            positive=drive+config.self_excitation*old-config.inhibition*(1-old)
            negative=-drive+config.self_excitation*(1-old)-config.inhibition*old
            z=(positive-negative)/config.temperature
            target=1/(1+exp(-z)) if z>=0 else exp(z)/(1+exp(z))
            computed[g.id]=(1-config.damping)*old+config.damping*target
            cost.group_updates+=1;cost.normalization_ops+=1
        nxt={}
        for g in p.groups:
            nxt[g.id]=computed[alias[g.id]];work['full_state_output_slots']+=1
            if g.id!=alias[g.id]:work['alias_copy_slots']+=1
        cost.kernel_ticks+=1;return nxt
    original=dynamics.tick;require(original is NATIVE_TICK,'native tick restored')
    dynamics.tick=step
    try:
        state,conv=dynamics.settle(program,e['drives'],cfg,cost,initial=e['initial'],top_down=e['top_down'],observe=lambda n,s,r,k:ticks.append(dict(tick=n,state=dict(s),state_key_order=list(s),residual=r,stable_steps=k)))
    finally:dynamics.tick=original
    c=plain(conv)
    record=dict(program=pr,program_sha256=program.digest,drives=e['drives'],initial=e['initial'],ticks=ticks,state=state,state_key_order=list(state),convergence=c,cost=cost.snapshot(),adopted=state['goal']>=.5 if c['status']=='stable_decision' else None)
    payload=dict(arm=arm,binding=binding,plan=plan,verification=checked,kernel=record,work=work,native_settle_calls=1)
    serialized=dumps(payload)
    timing=dict(cold_cpu_seconds=time.process_time()-cpu,cold_wall_seconds=time.perf_counter()-wall,preparation_seconds=preparation,payload_serialized_bytes=len(serialized.encode()),clock_resolution_seconds=dict(cpu=time.get_clock_info('process_time').resolution,wall=time.get_clock_info('perf_counter').resolution))
    return dict(payload,timing=timing)
