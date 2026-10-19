"""R24 archived transition opportunity screen. Original native run is never replayed natively."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level import probe as source
from tools.r22_measurement_adoption import probe as runner
from tools.r24_trust_boundary import census
read,put,sha,require=source.read,source.put,source.sha,source.require
SPEC=ROOT/'experiments/exp-70-trust-boundary/frozen_spec.json'
def spec():return read(SPEC)

def forbid_native():
    from hcr import dynamics
    from hcr.tasks.toy_world import World
    def forbidden(*args,**kwargs):raise AssertionError('new native work forbidden in archived census')
    dynamics.tick=dynamics.settle=World.measure=source.settle_one=forbidden

def verified_inputs(p):
    manifests=read(SPEC.with_name('input_manifest.json'))
    require(all(sha(ROOT/n)==h for n,h in manifests.items()),'archived input digests')
    historical=read(ROOT/'evidence/substitution-cross-level-20261019-r19/source-manifest.actual.json')
    require(historical['src/hcr/dynamics.py']==manifests['src/hcr/dynamics.py'] and
        historical[p['original_spec']]==manifests[p['original_spec']],'historical semantics/config binding')
    require(historical['tools/r19_cross_level/probe.py']==manifests['evidence/substitution-cross-level-20261019-r19/executed-probe.py.txt'],'executed source provenance')
    prior=read(ROOT/p['original_spec']);raw=ROOT/p['original_raw_root'];oldmanifest=read(raw/'manifest.json');records={};maximum=0.
    require([c['id'] for c in prior['cases']]==p['source_case_order'] and prior['arms']==p['source_arms'],'source order')
    for case in prior['cases']:
        for arm in prior['arms']:
            name=case['id']+'__'+arm+'.json';path=raw/name
            require(sha(path)==oldmanifest[name],'original manifest binding')
            record=read(path);maximum=max(maximum,source.audit_execution(record,case,arm,prior,p['numeric_replay_absolute_tolerance_server']))
            records[case['id'],arm]=record
    kernels=[k for r in records.values() for k in r['kernels']]
    require(len(records)==18 and len(kernels)==36 and sum(len(k['ticks']) for k in kernels)==988,'source data count')
    return prior,records,maximum

def events_for(p,prior,records,arm):
    events=[];semantics=read(SPEC.with_name('input_manifest.json'))['src/hcr/dynamics.py']
    for key in p['source_case_order']:
        record=records[key,arm];public={n:record['public'][n] for n in ['measurements','context']}
        for kernel_index,kernel in enumerate(record['kernels']):
            current=kernel['initial']
            for row in kernel['ticks']:
                events.append(dict(case=key,kernel_index=kernel_index,tick=row['tick'],program=kernel['program'],config=prior['kernel'],
                    current=current,next=row['state'],initial=kernel['initial'],drives=kernel['drives'],top_down=True,
                    semantics_sha256=semantics,public_numeric=public))
                current=row['state']
    return events

def execute(out):
    p=spec();prior,records,maximum=verified_inputs(p);analyses={}
    for arm in p['transition_arms']:
        events=events_for(p,prior,records,arm)
        for scope in p['scopes']:analyses[arm+'__'+scope]=census.analyze(events,scope,p)
    put(out/'census.json',dict(analyses=analyses,saved_scalar_replay_max_absolute_error=maximum,
        numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_server'],source_case_files=18,source_settles=36,source_ticks=988,
        original_status=p['original_status'],original_source_postcheck_complete=False,new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,training_calls=0))

def audit(out):
    p=spec();prior,records,maximum=verified_inputs(p);data=read(out/'census.json');rejections={};summaries={}
    require(set(data['analyses'])=={a+'__'+s for a in p['transition_arms'] for s in p['scopes']},'analysis set')
    for arm in p['transition_arms']:
        events=events_for(p,prior,records,arm)
        for scope in p['scopes']:
            key=arm+'__'+scope;analysis=data['analyses'][key];census.audit(analysis,events,scope,p)
            if (arm,scope)==('bottom_up','case_local'):
                for name,expected in census.MUTATIONS.items():
                    try:census.audit(census.mutated(analysis,name),events,scope,p)
                    except ValueError as exc:require(str(exc)==expected,'mutation cause '+str(exc));rejections[name]=str(exc)
                    else:raise ValueError('accepted census mutation '+name)
            summaries[key]=dict(analysis['summary'],analysis_cpu_seconds=analysis['analysis_cpu_seconds'],analysis_wall_seconds=analysis['analysis_wall_seconds'])
    require(data['saved_scalar_replay_max_absolute_error']==maximum and data['numeric_replay_absolute_tolerance']==p['numeric_replay_absolute_tolerance_server'],'saved replay binding')
    require([data[n] for n in ['source_case_files','source_settles','source_ticks']]==[18,36,988],'saved count binding')
    require(data['original_status']=='FAILED_AT_AUDIT' and not data['original_source_postcheck_complete'],'historical failure preserved')
    require(all(data[n]==0 for n in ['new_native_tick_calls','new_native_settle_calls','new_world_measure_calls','training_calls']),'no new native work')
    require(len(rejections)==5,'census mutation count')
    put(out/'summary.json',dict(status='ARCHIVED_TRANSITION_CENSUS_AUDITED',analyses=summaries,targeted_rejections=rejections,
        source_case_files=18,source_settles=36,source_ticks=988,analytical_transition_rows=1976,
        numeric_replay_max_absolute_error=maximum,numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_server'],
        original_status='FAILED_AT_AUDIT',new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,training_calls=0,
        original_native_costs_modified=False,net_efficiency_established=False,learned_circuit_reuse_established=False,
        case_local_candidate_opportunities=sum(v['case_local_non_repeated_invocation_hits'] for k,v in summaries.items() if k.endswith('__case_local'))))

def run(started):
    runner.spec=spec;runner.__file__=__file__;runner.run(started)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);parser.add_argument('--item',default='');parser.add_argument('--started',type=float);args=parser.parse_args();out=ROOT/'runs/technical'
    forbid_native()
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':require(args.item=='archived_r19__exact_transition_census','single analytical stage');execute(out)
    elif args.phase=='audit':audit(out)
    else:
        from tools.r24_trust_boundary.selfcheck import check
        result=check()
        import resource
        limits=spec()['limits'];result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(result['child_limits']['address_space']==(limits['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(limits['child_file_bytes'],)*2,'child resource limits')
        put(out/'preparation.json',result)
