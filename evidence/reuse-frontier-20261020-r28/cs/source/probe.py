"""R26 changed-input warm-start screening, using unchanged native settle."""
import argparse,json,math,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.codec import plain
from hcr.model import Config,Cost,fingerprint
from tools.r19_cross_level import probe as old
from tools.r22_measurement_adoption import probe as runner
from tools.r26_contraction_warmstart import policy,verify
read,put,sha,require=old.read,old.put,old.sha,old.require
SPEC=ROOT/'experiments/exp-72-contraction-warmstart/frozen_spec.json'
def spec():return read(SPEC)

def inputs():
    p=spec();require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'frozen input digests')
    require(p['kernel']==read(ROOT/'experiments/exp-65-substitution-cross-level/frozen_spec.json')['kernel'] and p['dynamics_sha256']==sha(ROOT/'src/hcr/dynamics.py'),'native semantics binding')
    require(p['contraction_threshold']==dict(numerator=19,denominator=20) and p['arms_order']==['reset','carry','guarded'] and len(p['streams'])==4 and all(len(s['cells'])==6 for s in p['streams']),'frozen policy matrix')
    cfg=Config(**p['kernel']);program,_=old.programs(cfg);return p,cfg,program,plain(program)

def binding_for(stream,arm,program,p):
    return fingerprint(dict(scope=[stream['key'],arm],program=program,config=p['kernel'],dynamics_sha256=p['dynamics_sha256']))

def execute(out,key):
    p,cfg,program,pr=inputs();stream=next(s for s in p['streams'] if s['key']==key);ids=[g.id for g in program.groups];cache={arm:None for arm in p['arms_order']};bindings={arm:binding_for(stream,arm,pr,p) for arm in p['arms_order']};rows=[]
    for index,cell in enumerate(stream['cells']):
        shift=(index+stream['order_offset'])%3;order=p['arms_order'][shift:]+p['arms_order'][:shift]
        for arm in order:
            cpu=time.process_time();wall=time.perf_counter();previous=cache[arm];drives=dict(f0=cfg.evidence_gain*cell['scores'][0],f1=cfg.evidence_gain*cell['scores'][1],goal=0.)
            gate=None;gate_cpu=gate_wall=0.
            if arm=='guarded' and previous is not None:
                gc=time.process_time();gw=time.perf_counter();gate=policy.certificate(pr,p['kernel'],drives,p['weights']);gate_wall=time.perf_counter()-gw;gate_cpu=time.process_time()-gc
            initial,choice=policy.choose(arm,previous,bindings[arm],gate,ids);cost=Cost();ticks=[]
            state,conv=dynamics.settle(program,drives,cfg,cost,initial=initial,top_down=True,observe=lambda n,s,r,k:ticks.append(dict(tick=n,state=dict(s),residual=r,stable_steps=k)))
            c=plain(conv);record=dict(program=pr,program_sha256=program.digest,drives=drives,initial=initial,ticks=ticks,state=state,convergence=c,cost=cost.snapshot(),adopted=state['goal']>=.5 if c['status']=='stable_decision' else None)
            written=arm!='reset' and c['status'] in ('stable_decision','stable_ambiguous')
            cache[arm]=dict(cell=cell['key'],binding=bindings[arm],state=dict(state),status=c['status']) if written else None
            row=dict(index=index,cell=cell['key'],arm=arm,binding=bindings[arm],gate=gate,choice=choice,source_available_cell=None if previous is None else previous['cell'],kernel=record,state_values_read=len(ids) if choice['action']=='warm' else 0,state_values_written=len(ids) if written else 0,logical_state_payload_bytes=8*len(ids) if written else 0,native_settle_calls=1,gate_evaluations=int(gate is not None),gate_cpu_seconds=gate_cpu,gate_wall_seconds=gate_wall)
            row['wall_seconds']=time.perf_counter()-wall;row['cpu_seconds']=time.process_time()-cpu;rows.append(row)
    put(out/(key+'.json'),dict(stream=key,rows=rows,training_calls=0,world_measure_calls=0))

def audit_one(data,stream,p,pr,cfg):
    vp=dict(p,arms=p['arms_order']);return verify.audit_stream(data,stream,vp,pr,p['kernel'],lambda arm:binding_for(stream,arm,pr,p))

def aggregate(data_by_stream,p,pr,cfg):
    totals={arm:dict(native_settle_calls=0,kernel_ticks=0,group_updates=0,signal_transmissions=0,normalization_ops=0,warm_starts=0,gate_evaluations=0,state_values_read=0,state_values_written=0,logical_state_payload_bytes_peak=0,cpu_seconds=0.,wall_seconds=0.,gate_cpu_seconds=0.,gate_wall_seconds=0.,quality_disagreements=0,readout_changes=0,status_changes=0) for arm in p['arms_order']};outcomes=[];maximum=0.;prefixes=[]
    for stream in p['streams']:
        data=data_by_stream[stream['key']];require(data['training_calls']==data['world_measure_calls']==0,'scope flags');quality,error=audit_one(data,stream,p,pr,cfg);maximum=max(maximum,error)
        for row,q in zip(data['rows'],quality,strict=True):
            target=totals[row['arm']];outcomes.append(dict(stream=stream['key'],**q));target['native_settle_calls']+=1;target['warm_starts']+=row['choice']['action']=='warm'
            for name in ['kernel_ticks','group_updates','signal_transmissions','normalization_ops']:target[name]+=row['kernel']['cost'][name]
            for name in ['gate_evaluations','state_values_read','state_values_written','cpu_seconds','wall_seconds','gate_cpu_seconds','gate_wall_seconds']:target[name]+=row[name]
            target['logical_state_payload_bytes_peak']=max(target['logical_state_payload_bytes_peak'],row['logical_state_payload_bytes']);target['quality_disagreements']+=not q['quality_preserved'];target['readout_changes']+=q['readout_changed'];target['status_changes']+=q['status_changed']
        for length in range(1,7):
            for arm in p['arms_order']:
                rows=[row for row in data['rows'] if row['arm']==arm and row['index']<length]
                prefixes.append(dict(stream=stream['key'],length=length,arm=arm,kernel_ticks=sum(r['kernel']['cost']['kernel_ticks'] for r in rows),cpu_seconds=sum(r['cpu_seconds'] for r in rows),wall_seconds=sum(r['wall_seconds'] for r in rows),gate_cpu_seconds=sum(r['gate_cpu_seconds'] for r in rows)))
    require(sum(t['native_settle_calls'] for t in totals.values())==p['maximum_native_settle_calls']==72,'global settle count');require(sum(t['kernel_ticks'] for t in totals.values())<=p['maximum_logical_ticks'],'global tick cap')
    return dict(status='NATIVE_WARMSTART_SCREEN_AUDITED',totals=totals,outcomes=outcomes,prefixes=prefixes,scalar_max_absolute_error=maximum,scalar_tolerance=p['scalar_tolerance'],terminal_state_tolerance=p['terminal_state_tolerance'],guarded_observed_quality_preserved=totals['guarded']['quality_disagreements']==0,unconditional_carry_changed_readouts=totals['carry']['readout_changes']>0,training_calls=0,world_measure_calls=0,real_map_contraction_is_native_bit_certificate=False,statistical_speed_or_generalization_established=False,production_adoption=False)

MUTATIONS={'gate':'rational gate','initial':'initial provenance','state':'scalar trace','cost':'native cost','source':'initial provenance','order':'cell order','timing':'timing inclusion'}
def mutate(data,name):
    bad=deepcopy(data)
    if name=='gate':next(r for r in bad['rows'] if r['gate'] is not None)['gate']['eligible']=not next(r for r in bad['rows'] if r['gate'] is not None)['gate']['eligible']
    elif name=='initial':bad['rows'][0]['kernel']['initial']['goal']+=.01
    elif name=='state':bad['rows'][0]['kernel']['ticks'][0]['state']['goal']+=.01
    elif name=='cost':bad['rows'][0]['kernel']['cost']['kernel_ticks']-=1
    elif name=='source':bad['rows'][0]['source_available_cell']='future'
    elif name=='order':bad['rows'][0]['index']=5
    else:bad['rows'][0]['gate_cpu_seconds']=bad['rows'][0]['cpu_seconds']+1.
    return bad

def audit(out):
    p,cfg,_,pr=inputs();data={s['key']:read(out/(s['key']+'.json')) for s in p['streams']};summary=aggregate(data,p,pr,cfg);rejections={};stream=p['streams'][0]
    for name,reason in MUTATIONS.items():
        try:audit_one(mutate(data[stream['key']],name),stream,p,pr,cfg)
        except ValueError as exc:require(str(exc)==reason,'mutation cause '+str(exc));rejections[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    summary['targeted_rejections']=rejections;put(out/'summary.json',summary)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);parser.add_argument('--item',default='');parser.add_argument('--started',type=float);args=parser.parse_args();out=ROOT/'runs/technical'
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise AssertionError('measurement/training forbidden')
    World.measure=forbidden
    if args.phase=='run':runner.spec=spec;runner.__file__=__file__;runner.run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':key,arm=args.item.split('__');require(arm=='three_policies','single policy matrix per stream');execute(out,key)
    elif args.phase=='audit':audit(out)
    else:
        from tools.r26_contraction_warmstart.selfcheck import check
        import resource
        result=check();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE));p=spec();require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits');put(out/'preparation.json',result)
