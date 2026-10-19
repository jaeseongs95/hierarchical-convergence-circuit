"""R25 exact fixed-point arithmetic shortcut: paired native component probe."""
import argparse,json,math,platform,statistics,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level import probe as old
from tools.r22_measurement_adoption import probe as runner
from tools.r24_trust_boundary import probe as prior,census
from tools.r25_fixedpoint_elision import shortcut
read,put,sha,require=old.read,old.put,old.sha,old.require
SPEC=ROOT/'experiments/exp-71-fixedpoint-elision/frozen_spec.json'
def spec():return read(SPEC)

def kernels():
    p=spec();original,records,error=prior.verified_inputs(prior.spec());result=[]
    for case in prior.spec()['source_case_order']:
        for arm in prior.spec()['transition_arms']:
            for i,kernel in enumerate(records[case,arm]['kernels']):
                result.append(dict(id=case+'__'+arm+'__'+str(i),kernel=kernel))
    require(len(result)==36,'36 kernels')
    require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'r25 input binding')
    return result,original['kernel'],error

def execute(out):
    items,cfg,error=kernels();pairs=[]
    for item in items:
        pairs.append(dict(id=item['id'],baseline=shortcut.invoke(item['kernel'],cfg,'baseline'),fixed_point=shortcut.invoke(item['kernel'],cfg,'fixed_point')))
    correctness=dict(pairs=pairs,source_scalar_error=error,training_calls=0,world_measure_calls=0)
    put(out/'correctness.json',correctness)
    validate_correctness(correctness,items,cfg)  # Stop before timing if semantic preservation fails.
    p=spec();blocks=[]
    for block in range(p['timing_pairs']):
        order=['baseline','fixed_point'] if block%2==0 else ['fixed_point','baseline'];times={}
        for arm in order:
            totals={};checksum=0;cpu=time.process_time();wall=time.perf_counter()
            for repeat in range(p['repeats_per_block']):
                for item in items:
                    result=shortcut.invoke(item['kernel'],cfg,arm)
                    for n,v in result['physical'].items():totals[n]=totals.get(n,0)+v
                    checksum+=result['record']['convergence']['ticks']+int(result['record']['state']['goal']>=.5)
            elapsed_wall=time.perf_counter()-wall;elapsed_cpu=time.process_time()-cpu
            times[arm]=dict(cpu_seconds=elapsed_cpu,wall_seconds=elapsed_wall,physical=totals,checksum=checksum,settles=len(items)*p['repeats_per_block'])
        blocks.append(dict(block=block,order=order,arms=times))
    import os
    put(out/'timing.json',dict(blocks=blocks,environment=dict(python=sys.version,platform=platform.platform(),machine=platform.machine(),cpu_count=os.cpu_count(),timer_cpu='process_time',timer_wall='perf_counter'),warmth='same-process repeated workload; correctness pass ran both arms first',includes='input rehydration, wrapper installation/restoration, fixed-point detection, trace copies, logical Cost, record construction and common counters; excludes imports/input file I/O and post-run audit',training_calls=0,world_measure_calls=0))

def validate_correctness(data,items,cfg):
    require([r['id'] for r in data['pairs']]==[r['id'] for r in items],'pair binding');maximum=0.;totals={};logical=0;checksum=0
    for pair,item in zip(data['pairs'],items,strict=True):
        a,b=pair['baseline'],pair['fixed_point'];ra,rb=a['record'],b['record']
        require(census.freeze(ra)==census.freeze(rb),'exact semantic trace')
        require(ra['initial']==item['kernel']['initial'] and ra['drives']==item['kernel']['drives'] and ra['program']==item['kernel']['program'],'input kernel binding')
        maximum=max(maximum,old.independent_kernel(ra,cfg,spec()['scalar_tolerance']))
        require(ra['cost']==item['kernel']['cost'] and ra['adopted']==item['kernel']['adopted'],'historical cost/readout')
        previous=ra['initial'];first=None
        for i,row in enumerate(ra['ticks'],1):
            if first is None and census.freeze(previous)==census.freeze(row['state']):first=i
            previous=row['state']
        length=len(ra['ticks']);native=length if first is None else first;logical+=length
        checksum+=ra['convergence']['ticks']+int(ra['state']['goal']>=.5)
        for arm,r,expected_native in [('baseline',a,length),('fixed_point',b,native)]:
            m=r['physical'];skip=length-expected_native;groups=len(ra['program']['groups']);links=len(ra['program']['links'])
            expected=dict(native_tick_calls=expected_native,skipped_tick_arithmetic=skip,logical_ticks=length,physical_group_updates=expected_native*groups,physical_signal_transmissions=expected_native*links,omitted_group_updates=skip*groups,omitted_signal_transmissions=skip*links,detection_checks=0 if arm=='baseline' else expected_native)
            require(m==expected,'physical ledger')
            for n,v in m.items():totals.setdefault(arm,{});totals[arm][n]=totals[arm].get(n,0)+v
    require(logical==988 and len(data['pairs'])==36,'original workload count')
    require(data['training_calls']==0 and data['world_measure_calls']==0,'correctness scope')
    return totals,maximum,checksum

def validate_timing(data,totals,checksum):
    p=spec();blocks=data['blocks'];require(len(blocks)==p['timing_pairs'],'timing block count');ratios_cpu=[];ratios_wall=[]
    for i,block in enumerate(blocks):
        require(block['block']==i and block['order']==(['baseline','fixed_point'] if i%2==0 else ['fixed_point','baseline']),'timing order')
        for arm in ['baseline','fixed_point']:
            row=block['arms'][arm]
            require(row['settles']==36*p['repeats_per_block'] and row['physical']=={n:v*p['repeats_per_block'] for n,v in totals[arm].items()},'timing workload ledger')
            require(all(type(row[n]) in (int,float) and math.isfinite(row[n]) and row[n]>0 for n in ['cpu_seconds','wall_seconds']),'timing values')
        a,b=block['arms']['baseline'],block['arms']['fixed_point'];require(a['checksum']==b['checksum']==checksum*p['repeats_per_block'],'timing checksum')
        ratios_cpu.append(b['cpu_seconds']/a['cpu_seconds']);ratios_wall.append(b['wall_seconds']/a['wall_seconds'])
    require(data['training_calls']==0 and data['world_measure_calls']==0,'timing scope')
    accepted=statistics.median(ratios_cpu)<=p['adoption_max_median_ratio'] and statistics.median(ratios_wall)<=p['adoption_max_median_ratio'] and sum(r<1 for r in ratios_cpu)>=p['adoption_min_improved_pairs']
    return dict(cpu_ratios=ratios_cpu,wall_ratios=ratios_wall,median_cpu_ratio=statistics.median(ratios_cpu),median_wall_ratio=statistics.median(ratios_wall),cpu_improved_pairs=sum(r<1 for r in ratios_cpu),local_component_adoption_criterion_met=accepted,product_efficiency_established=False)

def mutated(data,name):
    bad=deepcopy(data)
    if name=='state':bad['pairs'][0]['fixed_point']['record']['ticks'][0]['state']['goal']+=.01
    elif name=='cost':bad['pairs'][0]['fixed_point']['record']['cost']['kernel_ticks']-=1
    elif name=='stable':bad['pairs'][0]['fixed_point']['record']['ticks'][0]['stable_steps']+=1
    elif name=='ledger':bad['pairs'][0]['fixed_point']['physical']['native_tick_calls']-=1
    return bad

def audit(out):
    items,cfg,source_error=kernels();data=read(out/'correctness.json');require(data['source_scalar_error']==source_error,'source replay binding');totals,error,checksum=validate_correctness(data,items,cfg);timing=read(out/'timing.json');ratios=validate_timing(timing,totals,checksum);rejections={}
    for name,reason in [('state','exact semantic trace'),('cost','exact semantic trace'),('stable','exact semantic trace'),('ledger','physical ledger')]:
        try:validate_correctness(mutated(data,name),items,cfg)
        except ValueError as exc:require(str(exc)==reason,'mutation cause');rejections[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    bad=deepcopy(timing);bad['blocks'][0]['arms']['baseline']['settles']-=1
    try:validate_timing(bad,totals,checksum)
    except ValueError as exc:require(str(exc)=='timing workload ledger','timing mutation cause');rejections['timing_workload']=str(exc)
    else:raise ValueError('timing mutation accepted')
    p=spec();settles=36*2*(1+p['timing_pairs']*p['repeats_per_block']);logical=988*2*(1+p['timing_pairs']*p['repeats_per_block'])
    require(settles<=p['maximum_native_settle_calls'] and logical<=p['maximum_logical_ticks'],'global work caps')
    put(out/'summary.json',dict(status='NATIVE_FIXEDPOINT_COMPONENT_AUDITED',correctness_bit_exact=True,pairs=36,totals_per_workload=totals,performance=ratios,scalar_max_absolute_error=error,scalar_tolerance=p['scalar_tolerance'],targeted_rejections=rejections,total_native_settle_calls=settles,total_logical_ticks=logical,training_calls=0,world_measure_calls=0,original_r19_status='FAILED_AT_AUDIT',original_source_postcheck_complete=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);parser.add_argument('--item',default='');parser.add_argument('--started',type=float);args=parser.parse_args();out=ROOT/'runs/technical'
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise AssertionError('training/measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':runner.spec=spec;runner.__file__=__file__;runner.run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':require(args.item=='saved36__paired_native','single matrix');execute(out)
    elif args.phase=='audit':audit(out)
    else:
        from tools.r25_fixedpoint_elision.selfcheck import check
        import resource
        result=check();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE));p=spec()
        require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits')
        put(out/'preparation.json',result)
