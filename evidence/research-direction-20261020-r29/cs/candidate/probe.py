"""A-0 only: four source Programs,32frozen queries, no native execution."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level import probe as old
from tools.r22_measurement_adoption import probe as runner
from tools.r29_research_direction import partition
from tools.r29_research_direction.verify import verify
from hcr.model import Config,fingerprint
from hcr.codec import plain
read,put,sha,require=old.read,old.put,old.sha,old.require
SPEC=ROOT/'experiments/exp-75-research-direction/frozen_spec.json'
def spec():return read(SPEC)

def programs(cfg):
    from hcr.workspace import make_program
    low,upper=old.programs(cfg)
    return dict(chain2=make_program(2,((0,1),),cfg),shared_bypass=make_program(6,((0,1,2,5),(0,3,4,5)),cfg),lower=low,upper=upper)

def inputs():
    p=spec();actual=programs(Config(**p['kernel']))
    require(p['native_source_sha256']==sha(ROOT/'src/hcr/dynamics.py'),'native semantics binding')
    require({k:plain(v) for k,v in actual.items()}==p['programs'],'source Programs binding')
    require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input hashes')
    return p

def entries(p,key):
    return [dict(program=p['programs'][key],drives=c['drives'][key],initial=c['initial'][key],top_down=True,config=p['kernel'],native_source_sha256=p['native_source_sha256']) for c in p['conditions']]

def execute(out,key):
    p=inputs();results=[]
    for condition,entry in zip(p['conditions'],entries(p,key),strict=True):
        plan=partition.analyze(entry);checked=verify(entry,plan)
        results.append(dict(condition=condition['key'],entry_sha256=fingerprint(entry),plan=plan,verification=checked))
    put(out/(key+'.json'),dict(program=key,results=results,native_tick_calls=0,native_settle_calls=0,training_calls=0,world_measure_calls=0,new_timing_runs=0))

def audit_data(data,p):
    require(set(data)==set(p['programs']) and len(p['conditions'])==8 and len(p['programs'])==4,'frozen census matrix')
    totals=dict(queries=0,opportunity_queries=0,nontrivial_classes=0,projected_group_updates_omitted_per_one_tick_per_query=0,projected_links_omitted_per_one_tick_per_query=0);rows=[]
    for key in p['programs']:
        d=data[key];require(d['program']==key and len(d['results'])==8,'program matrix')
        require(all(d[n]==0 for n in ['native_tick_calls','native_settle_calls','training_calls','world_measure_calls','new_timing_runs']),'scope flags')
        for condition,entry,row in zip(p['conditions'],entries(p,key),d['results'],strict=True):
            require(row['condition']==condition['key'] and row['entry_sha256']==fingerprint(entry),'frozen query binding')
            checked=verify(entry,row['plan']);require(row['verification']==checked,'independent verification binding')
            n=checked['nontrivial_classes'];book=row['plan']['ledger'];totals['queries']+=1;totals['opportunity_queries']+=n>0;totals['nontrivial_classes']+=n
            totals['projected_group_updates_omitted_per_one_tick_per_query']+=book['projected_group_updates_omitted_per_tick'];totals['projected_links_omitted_per_one_tick_per_query']+=book['projected_link_operations_omitted_per_tick']
            rows.append(dict(program=key,condition=condition['key'],nontrivial_classes=[c for c in row['plan']['classes'] if len(c)>1],ledger=book))
    require(totals['queries']==32,'query count')
    return dict(status='A0_STATIC_OPPORTUNITY_AUDITED',totals=totals,rows=rows,admit_A1_contract=totals['opportunity_queries']>0,
        native_tick_calls=0,native_settle_calls=0,training_calls=0,world_measure_calls=0,new_timing_runs=0,
        actual_runtime_equivalence_tested=False,runtime_savings_measured=False,learned_compression_tested=False,production_adoption=False)

def audit(out):
    p=inputs();data={k:read(out/(k+'.json')) for k in p['programs']};summary=audit_data(data,p);rejects={}
    for name in ['binding','coverage','ledger','missing_query','scope']:
        bad=deepcopy(data);first=next(iter(p['programs']));row=bad[first]['results'][0]
        if name=='binding':row['entry_sha256']='0'*64
        elif name=='coverage':row['plan']['classes'][0].append(row['plan']['classes'][0][0])
        elif name=='ledger':row['plan']['ledger']['projected_group_updates_omitted_per_tick']+=1
        elif name=='missing_query':bad[first]['results'].pop()
        else:bad[first]['native_settle_calls']=1
        try:audit_data(bad,p)
        except ValueError as exc:rejects[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    summary['targeted_rejections']=rejects;put(out/'summary.json',summary)

def prohibit_native():
    from hcr import dynamics
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise AssertionError('A0 native/training/measurement forbidden')
    dynamics.tick=dynamics.settle=dynamics.settle_recorded=forbidden;World.measure=forbidden

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args();out=ROOT/'runs/technical';prohibit_native()
    if args.phase=='run':runner.spec=spec;runner.__file__=__file__;runner.run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':key,arm=args.item.split('__');require(arm=='static','static only');execute(out,key)
    elif args.phase=='audit':audit(out)
    else:
        from tools.r29_research_direction.selfcheck import check
        import resource
        p=inputs();result=check();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child limits');put(out/'preparation.json',result)
