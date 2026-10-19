"""Pure policy/math checks; no native recurrence or archived warm-start execution."""
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction as F
from hcr.model import Config
from tools.r19_cross_level.probe import programs
from tools.r26_contraction_warmstart import policy,verify

def check():
    cfg=asdict(Config(prior_gain=0));low,_=programs(Config(**cfg));pr=asdict(low);weights=dict(f0=1,f1=1,goal=8);ids=list(weights);count=0
    def assertion(ok,msg):
        nonlocal count
        if not ok:raise ValueError(msg)
        count+=1
    def reject(call,msg):
        try:call()
        except ValueError as exc:assertion(str(exc)==msg,'cause')
        else:raise ValueError('accepted '+msg)
    strong=policy.certificate(pr,cfg,dict(f0=4.,f1=3.2,goal=0.),weights);neutral=policy.certificate(pr,cfg,dict(f0=0.,f1=0.,goal=0.),weights)
    d,s,h=F(cfg['damping']),F(cfg['self_excitation']),F(cfg['inhibition'])
    assertion(policy.decoded(strong['q_upper'])==1-d+d*(s+h)/2+d/2,'strong rational row bound')
    assertion(strong['eligible'] and not neutral['eligible'],'current input matters')
    assertion(policy.decoded(neutral['q_upper'])>1,'neutral global bound inconclusive')
    assertion(all(policy.decoded(row['sigmoid_derivative_upper'])<=F(1,4) for row in strong['rows']),'derivative ceiling')
    neg=policy.certificate(pr,cfg,dict(f0=-4.,f1=-3.2,goal=0.),weights);assertion(neg==strong,'drive sign symmetry with zero biases')
    for drives in [dict(f0=4.,f1=3.2,goal=0.),dict(f0=0.,f1=0.,goal=0.),dict(f0=.8,f1=.6,goal=0.)]:
        assertion(policy.certificate(pr,cfg,drives,weights)==verify.rational_gate(pr,cfg,drives,weights),'separate rational formula')
    reject(lambda:policy.certificate(pr,cfg,{},dict(f0=1,goal=8)),'norm weights')
    previous=dict(cell='past',binding='same',state=dict(f0=.8,f1=.8,goal=.9),status='stable_decision')
    initial,choice=policy.choose('carry',previous,'same',None,ids);assertion(choice['action']=='warm' and initial==previous['state'] and initial is not previous['state'],'copy prior state')
    initial,choice=policy.choose('guarded',previous,'same',neutral,ids);assertion(choice['action']=='reset' and set(initial.values())=={.5},'reject neutral')
    initial,choice=policy.choose('guarded',previous,'same',strong,ids);assertion(choice['action']=='warm','allow screened input')
    for arm in ['carry','guarded']:
        assertion(policy.choose(arm,None,'same',strong,ids)[1]['reason']=='no_source','first cell cold')
        assertion(policy.choose(arm,previous,'different',strong,ids)[1]['reason']=='binding_changed','scope/source/config changed')
        bad=deepcopy(previous);bad['status']='budget_exhausted';assertion(policy.choose(arm,bad,'same',strong,ids)[1]['reason']=='nonstable_source','nonstable cold')
        bad=deepcopy(previous);bad['state']['goal']=float('nan');reject(lambda:policy.choose(arm,bad,'same',strong,ids),'source state')
    assertion(policy.choose('reset',previous,'same',strong,ids)[1]['reason']=='baseline','reset ignores source')
    reject(lambda:policy.choose('other',None,'same',None,ids),'arm')
    from tools.r26_contraction_warmstart.probe import binding_for,audit_one,mutate,MUTATIONS
    basep=dict(kernel=cfg,dynamics_sha256='a'*64);stream=dict(key='s');binding=binding_for(stream,'carry',pr,basep)
    variants=[]
    changed=deepcopy(pr);changed['groups'][0]['bias']=.01;variants.append(binding_for(stream,'carry',changed,basep))
    changed=deepcopy(basep);changed['kernel']['damping']=.2;variants.append(binding_for(stream,'carry',pr,changed))
    changed=deepcopy(basep);changed['dynamics_sha256']='b'*64;variants.append(binding_for(stream,'carry',pr,changed))
    variants.extend([binding_for(dict(key='s2'),'carry',pr,basep),binding_for(stream,'guarded',pr,basep)])
    for new in variants:assertion(new!=binding,'program/config/source/stream/arm binding coverage')
    # Synthetic known identity trace at neutral input; not a native run or research observation.
    from hcr.codec import plain
    from hcr.model import Cost,fingerprint
    fakepr=plain(low);fakep=dict(basep,arms_order=['reset','carry','guarded'],weights=weights,scalar_tolerance=1e-15,terminal_state_tolerance=1e-4)
    stream=dict(key='synthetic',order_offset=0,cells=[dict(key='step'+str(i),scores=[0.,0.]) for i in range(6)]);rows=[];past={a:None for a in fakep['arms_order']}
    for index,cell in enumerate(stream['cells']):
        order=fakep['arms_order'][index%3:]+fakep['arms_order'][:index%3]
        for arm in order:
            previous=past[arm];state={k:.5 for k in ids};gate=policy.certificate(fakepr,cfg,dict(f0=0.,f1=0.,goal=0.),weights) if arm=='guarded' and previous is not None else None
            if arm=='reset':choice=dict(action='reset',reason='baseline',source_cell=None)
            elif previous is None:choice=dict(action='reset',reason='no_source',source_cell=None)
            elif arm=='guarded':choice=dict(action='reset',reason='contraction_not_established',source_cell=None)
            else:choice=dict(action='warm',reason='past_state',source_cell=previous)
            cost=Cost().snapshot();cost.update(kernel_ticks=4,group_updates=12,signal_transmissions=16,normalization_ops=12)
            record=dict(program=fakepr,program_sha256=fingerprint(fakepr),drives=dict(f0=0.,f1=0.,goal=0.),initial=dict(state),ticks=[dict(tick=i,state=dict(state),residual=0.,stable_steps=i) for i in range(1,5)],state=dict(state),convergence=dict(status='stable_ambiguous',ticks=4,residual=0.,margin=0.,stable_steps=4),cost=cost,adopted=None)
            written=arm!='reset';rows.append(dict(index=index,cell=cell['key'],arm=arm,binding=binding_for(stream,arm,fakepr,fakep),kernel=record,gate=gate,choice=choice,source_available_cell=previous,state_values_written=3 if written else 0,state_values_read=3 if choice['action']=='warm' else 0,logical_state_payload_bytes=24 if written else 0,native_settle_calls=1,gate_evaluations=int(gate is not None),cpu_seconds=.001,wall_seconds=.001,gate_cpu_seconds=.0001 if gate is not None else 0.,gate_wall_seconds=.0001 if gate is not None else 0.));past[arm]=cell['key'] if written else None
    data=dict(stream='synthetic',rows=rows);quality,maximum=audit_one(data,stream,fakep,fakepr,Config(**cfg));assertion(len(quality)==18 and maximum==0,'synthetic audit accepted')
    for name,reason in MUTATIONS.items():reject(lambda name=name:audit_one(mutate(data,name),stream,fakep,fakepr,Config(**cfg)),reason)
    return dict(status='PURE_POLICY_MATH_PASSED',assertions=count,new_native_calls=0,new_timing_runs=0,synthetic_cells_not_research=18,real_math_bound_not_native_certificate=True)
