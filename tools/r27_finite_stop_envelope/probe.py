"""Analyze frozen R26 records on SSH; new native/learning/measurement/benchmark=0."""
import argparse,json,sys
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level import probe as old
from tools.r22_measurement_adoption import probe as runner
from tools.r26_contraction_warmstart import probe as source
from hcr.model import fingerprint
from tools.r27_finite_stop_envelope import envelope,verify
read,put,sha,require=old.read,old.put,old.sha,old.require
SPEC=ROOT/'experiments/exp-73-finite-stop-envelope/frozen_spec.json'
RAW=ROOT/'evidence/contraction-warmstart-20261019-r26/raw'

def spec():return read(SPEC)

def prohibit_native():
    from hcr import dynamics
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise AssertionError('new native/measurement/benchmark forbidden')
    dynamics.tick=dynamics.settle=World.measure=old.settle_one=source.execute=forbidden

def inputs():
    p=spec();manifest=read(SPEC.with_name('input_manifest.json'))
    require(all(sha(ROOT/n)==h for n,h in manifest.items()),'frozen input digests')
    p26,cfg,_,program=source.inputs()
    require(p['base']=='bad0c94e7c84f2018363756de898c577b5dcff27' and p['terms']==envelope.TERMS==128 and p['dyadic_bits']==envelope.BITS==192,'frozen math parameters')
    require(p['maximum_native_settle_calls']==p['maximum_measurement_requests']==p['new_timing_runs']==0 and p['saved_records']==72 and p['saved_pairs']==48,'frozen work scope')
    require(p['cases']==[dict(key=s['key']) for s in p26['streams']] and p['arms']==['saved_envelope'],'frozen stream matrix')
    return p,p26,cfg,program

def execute(out,key):
    p,p26,cfg,program=inputs();stream=next(s for s in p26['streams'] if s['key']==key);data=read(RAW/(key+'.json'));source.audit_one(data,stream,p26,program,cfg)
    rows=[dict(index=r['index'],cell=r['cell'],arm=r['arm'],source_row_fingerprint=fingerprint(r),bound=envelope.point(r['kernel'],p26['kernel'],p26['weights'])) for r in data['rows']]
    lookup={(r['index'],r['arm']):r for r in rows};kernels={(r['index'],r['arm']):r['kernel'] for r in data['rows']};pairs=[]
    for i,cell in enumerate(stream['cells']):
        for arm in ['carry','guarded']:
            c=envelope.pair(kernels[i,'reset'],kernels[i,arm],lookup[i,'reset']['bound'],lookup[i,arm]['bound'],p26['kernel'],p26['weights'],p26['terminal_state_tolerance'])
            pairs.append(dict(index=i,cell=cell['key'],arm=arm,certificate=c))
    put(out/(key+'.json'),dict(stream=key,rows=rows,pairs=pairs,new_native_calls=0,new_timing_runs=0,training_calls=0,world_measure_calls=0,retrospective_only=True))

def audit_scope(data):
    require(all(type(data[k]) is int and data[k]==0 for k in ['new_native_calls','new_timing_runs','training_calls','world_measure_calls']) and data['retrospective_only'] is True,'work scope')

def audit_stream(data,stream,p26,cfg,program):
    audit_scope(data);raw=read(RAW/(stream['key']+'.json'));source.audit_one(raw,stream,p26,program,cfg)
    require(data['stream']==stream['key'] and [(r['index'],r['cell'],r['arm']) for r in data['rows']]==[(r['index'],r['cell'],r['arm']) for r in raw['rows']],'record order')
    require([(r['index'],r['cell'],r['arm']) for r in data['pairs']]==[(i,c['key'],a) for i,c in enumerate(stream['cells']) for a in ['carry','guarded']],'pair order')
    lookup={};kernels={}
    for r,s in zip(data['rows'],raw['rows'],strict=True):
        require(r['source_row_fingerprint']==fingerprint(s),'row provenance')
        verify.point(s['kernel'],p26['kernel'],p26['weights'],r['bound']);lookup[r['index'],r['arm']]=r['bound'];kernels[r['index'],r['arm']]=s['kernel']
    outcomes=[]
    for row in data['pairs']:
        i,a=row['index'],row['arm'];result=verify.pair(kernels[i,'reset'],kernels[i,a],lookup[i,'reset'],lookup[i,a],p26['kernel'],p26['weights'],p26['terminal_state_tolerance'],row['certificate'])
        outcomes.append(dict(stream=stream['key'],index=i,cell=row['cell'],arm=a,**row['certificate'],**result))
    return outcomes

def cost_inputs(p26):
    s=read(RAW/'summary.json');rows=[]
    for unit in ['cpu','wall']:
        key=unit+'_seconds';gate='gate_'+key;r=s['totals']['reset'];c=s['totals']['guarded'];rows.append(('all',24,unit,r[key],c[key],c[gate]))
    for stream in p26['streams']:
        raw=read(RAW/(stream['key']+'.json'))['rows']
        for k in range(1,7):
            reset=[r for r in raw if r['index']<k and r['arm']=='reset'];candidate=[r for r in raw if r['index']<k and r['arm']=='guarded']
            for unit in ['cpu','wall']:
                key=unit+'_seconds';rows.append((stream['key'],k,unit,sum(r[key] for r in reset),sum(r[key] for r in candidate),sum(r['gate_'+key] for r in candidate)))
    return rows

def ledger(p26):return [dict(scope=s,length=k,unit=u,values=envelope.break_even(r,c,g)) for s,k,u,r,c,g in cost_inputs(p26)]

def audit_ledger(seen,p26):
    raw=cost_inputs(p26);require(len(seen)==len(raw)==50,'cost ledger')
    for row,(s,k,u,r,c,g) in zip(seen,raw,strict=True):
        require((row['scope'],row['length'],row['unit'])==(s,k,u),'cost ledger');verify.break_even(r,c,g,row['values'])

def aggregate(data,p,p26,cfg,program,cost):
    audit_ledger(cost,p26);outcomes=[]
    for stream in p26['streams']:outcomes+=audit_stream(data[stream['key']],stream,p26,cfg,program)
    totals={a:dict(pairs=0,certified=0,identity=0,contraction=0,unproven=0,observed_quality_disagreements=0,false_certifications=0) for a in ['carry','guarded']}
    for row in outcomes:
        t=totals[row['arm']];t['pairs']+=1;t['certified']+=row['certified'];t['identity']+=row['kind']=='EXACT_RECORD_IDENTITY';t['contraction']+=row['kind']=='CONTRACTION_ENVELOPE';t['unproven']+=not row['certified'];t['observed_quality_disagreements']+=not row['observed_quality_preserved'];t['false_certifications']+=row['certified'] and not row['observed_quality_preserved']
    counts={}
    for d in data.values():
        for r in d['rows']:counts[r['bound']['status']]=counts.get(r['bound']['status'],0)+1
    require(sum(counts.values())==72 and len(outcomes)==48,'global matrix')
    return dict(status='SAVED_FINITE_ENVELOPES_AUDITED',totals=totals,point_status_counts=counts,outcomes=outcomes,cost_ledger=cost,saved_records=72,saved_pairs=48,new_native_calls=0,new_timing_runs=0,training_calls=0,world_measure_calls=0,retrospective_only=True,production_adoption=False,statistical_speed_or_generalization_established=False,point_defect_is_uniform_native_roundoff_bound=False)

def targeted_checks(data,cost,p26,cfg,program):
    stream=p26['streams'][0];original=data[stream['key']];raw=read(RAW/(stream['key']+'.json'));at=next(i for i,r in enumerate(original['rows']) if r['bound']['status']=='FINITE_TERMINAL_ENVELOPE');checks={}
    def rejects(name,reason,call):
        try:call()
        except ValueError as exc:require(str(exc)==reason,'mutation cause '+str(exc));checks[name]=reason
        else:raise ValueError('mutation accepted '+name)
    for name,reason in [('interval','exp enclosure'),('q','global bound'),('radius','fixed-point radius')]:
        bad=deepcopy(original['rows'][at]['bound'])
        if name=='interval':bad['components'][0]['exp_upper']=envelope.enc(envelope.dec(bad['components'][0]['exp_lower'])-1)
        elif name=='q':bad['gate']['eligible']=not bad['gate']['eligible']
        else:bad['fixed_point_radius']=envelope.enc(envelope.dec(bad['fixed_point_radius'])+1)
        rejects(name,reason,lambda bad=bad:verify.point(raw['rows'][at]['kernel'],p26['kernel'],p26['weights'],bad))
    for name,reason in [('source','row provenance'),('order','record order'),('scope','work scope')]:
        bad=deepcopy(original)
        if name=='source':bad['rows'][0]['source_row_fingerprint']='0'*64
        elif name=='order':bad['rows'][0]['index']=99
        else:bad['new_native_calls']=1
        rejects(name,reason,lambda bad=bad:audit_stream(bad,stream,p26,cfg,program))
    index=next(i for i,r in enumerate(original['pairs']) if not r['certificate']['certified']);bad=deepcopy(original['pairs'][index]);bad['certificate']['certified']=True;i,a=bad['index'],bad['arm'];ks={(r['index'],r['arm']):r['kernel'] for r in raw['rows']};bs={(r['index'],r['arm']):r['bound'] for r in original['rows']}
    rejects('pair','pair decision',lambda:verify.pair(ks[i,'reset'],ks[i,a],bs[i,'reset'],bs[i,a],p26['kernel'],p26['weights'],p26['terminal_state_tolerance'],bad['certificate']))
    bad=deepcopy(cost);bad[0]['values']['gate']=envelope.enc(envelope.dec(bad[0]['values']['gate'])+1)
    rejects('cost','cost ledger',lambda:audit_ledger(bad,p26));return checks

def audit(out):
    p,p26,cfg,program=inputs();data={s['key']:read(out/(s['key']+'.json')) for s in p26['streams']};cost=ledger(p26)
    # Confirm saved source totals/prefixes before deriving any counterfactual arithmetic.
    original=source.aggregate({s['key']:read(RAW/(s['key']+'.json')) for s in p26['streams']},p26,program,cfg);saved=read(RAW/'summary.json')
    require(original['totals']==saved['totals'] and original['prefixes']==saved['prefixes'],'saved cost source')
    result=aggregate(data,p,p26,cfg,program,cost);result['targeted_rejections']=targeted_checks(data,cost,p26,cfg,program);put(out/'summary.json',result)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);parser.add_argument('--item',default='');parser.add_argument('--started',type=float);args=parser.parse_args();out=ROOT/'runs/technical';prohibit_native()
    if args.phase=='run':
        import time
        runner.spec=spec;runner.__file__=__file__;runner.run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':
        key,arm=args.item.split('__');require(arm=='saved_envelope','case arm');execute(out,key)
    elif args.phase=='audit':audit(out)
    else:
        import resource
        from tools.r27_finite_stop_envelope.selfcheck import check
        result=check();inputs();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE));p=spec();require(result['child_limits']==dict(address_space=(p['limits']['child_address_space_bytes'],)*2,file_size=(p['limits']['child_file_bytes'],)*2),'child resource limits');put(out/'preparation.json',result)
