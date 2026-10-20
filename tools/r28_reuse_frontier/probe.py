"""Cold six-input lifecycles, original choose/native, fixed paired workload."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.codec import plain
from hcr.model import Config,Cost,fingerprint
from tools.r19_cross_level import probe as old
from tools.r22_measurement_adoption import probe as runner
from tools.r26_contraction_warmstart import policy
from tools.r28_reuse_frontier import predicate
read,put,sha,require=old.read,old.put,old.sha,old.require
SPEC=ROOT/'experiments/exp-74-reuse-frontier/frozen_spec.json'

def spec():return read(SPEC)

def context(p):
    base=read(ROOT/p['base_spec']);require(sha(ROOT/p['base_spec'])==p['base_spec_sha256'],'base spec binding')
    cfg=Config(**base['kernel']);program,_=old.programs(cfg);pr=plain(program)
    sources={key:sha(ROOT/path) for key,path in p['predicate_sources'].items()}
    value=predicate.profile(pr,base['kernel'],base['weights'],sources,True)
    require(fingerprint(value)==p['predicate_profile_sha256'],'source profile binding')
    return base,cfg,program,pr,value

def execute(out,key):
    cpu=time.process_time();wall=time.perf_counter();p=spec();job=next(j for j in p['cases'] if j['key']==key)
    base,cfg,program,pr,value=context(p);stream=next(s for s in base['streams'] if s['key']==job['stream'])
    arm=job['policy'];compiled=None;cc=time.process_time();cw=time.perf_counter()
    if arm=='compiled_guarded':compiled=predicate.compile_predicate(value,p['predicate_profile_sha256'])
    compiler_cpu=time.process_time()-cc;compiler_wall=time.perf_counter()-cw
    binding=fingerprint(dict(scope=[stream['key'],'reset' if arm=='reset' else 'guarded'],program=pr,config=base['kernel'],dynamics_sha256=value['sources']['native']))
    previous=None;rows=[];ids=[g.id for g in program.groups]
    for index,cell in enumerate(stream['cells']):
        drives=dict(f0=cfg.evidence_gain*cell['scores'][0],f1=cfg.evidence_gain*cell['scores'][1],goal=0.);gate=None
        if arm!='reset' and previous is not None:
            eligible=(predicate.eligible(compiled,drives) if compiled is not None else policy.certificate(pr,base['kernel'],drives,base['weights'])['eligible'])
            gate=dict(eligible=eligible)
        initial,choice=policy.choose('reset' if arm=='reset' else 'guarded',previous,binding,gate,ids)
        before=deepcopy(previous);cost=Cost();ticks=[]
        state,conv=dynamics.settle(program,drives,cfg,cost,initial=initial,top_down=True,
            observe=lambda n,s,r,k:ticks.append(dict(tick=n,state=dict(s),residual=r,stable_steps=k)))
        convergence=plain(conv);kernel=dict(program=pr,program_sha256=program.digest,drives=drives,initial=initial,ticks=ticks,state=state,
            convergence=convergence,cost=cost.snapshot(),adopted=state['goal']>=.5 if convergence['status']=='stable_decision' else None)
        written=arm!='reset' and convergence['status'] in ('stable_decision','stable_ambiguous')
        previous=dict(cell=cell['key'],binding=binding,state=dict(state),status=convergence['status']) if written else None
        rows.append(dict(index=index,cell=cell['key'],gate=gate,choice=choice,cache_before=before,cache_after=deepcopy(previous),kernel=kernel,native_settle_calls=1))
    result=dict(job=job,binding=binding,rows=rows,clock_resolution_seconds=dict(cpu=time.get_clock_info('process_time').resolution,wall=time.get_clock_info('perf_counter').resolution),compiler_iterations=0 if compiled is None else compiled.iterations,
        compiler_cpu_seconds=compiler_cpu,compiler_wall_seconds=compiler_wall,store_load_calls=0,
        native_settle_calls=len(rows),training_calls=0,world_measure_calls=0)
    # Include one complete result serialization in the algorithm lifecycle. The final
    # timing-bearing file write and imports also appear in the runner's case-process ledger.
    result['constructed_result_bytes']=len(json.dumps(result,sort_keys=True,allow_nan=False).encode())
    result['cold_wall_seconds']=time.perf_counter()-wall;result['cold_cpu_seconds']=time.process_time()-cpu
    put(out/(key+'.json'),result)

def audit(out):
    from tools.r28_reuse_frontier.verify import audit_all,mutations
    p=spec();data={j['key']:read(out/(j['key']+'.json')) for j in p['cases']}
    summary=audit_all(data,p);summary['targeted_rejections']=mutations(data,p)
    put(out/'summary.json',summary)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);parser.add_argument('--item',default='');parser.add_argument('--started',type=float);args=parser.parse_args();out=ROOT/'runs/technical'
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise AssertionError('training/measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':runner.spec=spec;runner.__file__=__file__;runner.run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':key,arm=args.item.split('__');require(arm=='one','single lifecycle process');execute(out,key)
    elif args.phase=='audit':audit(out)
    else:
        from tools.r28_reuse_frontier.selfcheck import check
        import resource
        p=spec();_,_,_,_,value=context(p);result=check(value,p['predicate_profile_sha256'])
        result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child limits')
        require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'frozen inputs')
        put(out/'preparation.json',result)
