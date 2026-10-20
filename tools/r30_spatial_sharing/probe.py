"""R30 A1:32 cold native/shared pairs;64settles maximum, learning zero."""
import argparse
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r19_cross_level import probe as old
from tools.r22_measurement_adoption import probe as runner
from tools.r29_research_direction import probe as prior
from tools.r30_spatial_sharing import runtime,verify
from hcr.model import fingerprint
read,put,sha,require=old.read,old.put,old.sha,old.require
SPEC=ROOT/'experiments/exp-76-spatial-sharing/frozen_spec.json'
def spec():return read(SPEC)
def inputs():
    p=spec();base=prior.inputs()
    require(p['programs']==base['programs'] and p['conditions']==base['conditions'] and p['kernel']==base['kernel'] and p['native_source_sha256']==base['native_source_sha256'],'R29 unchanged inputs')
    require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'source input hashes')
    expected=[]
    for key in ['chain2','shared_bypass','lower','upper']:
        for c in p['conditions']:
            i=len(expected);expected.append(dict(key=f"q{i:02d}_{key}_{c['key']}",program=key,condition=c['key'],order=['native','shared'] if i%2==0 else ['shared','native']))
    require(p['cases']==expected and p['arms']==['pair'],'fixed pair schedule');return p
def entry_for(p,job):
    c=next(c for c in p['conditions'] if c['key']==job['condition']);key=job['program']
    return dict(program=p['programs'][key],drives=c['drives'][key],initial=c['initial'][key],top_down=True,config=p['kernel'],native_source_sha256=p['native_source_sha256'])
def execute(out,p,job):
    entry=entry_for(p,job);arms={}
    for arm in job['order']:arms[arm]=runtime.run(entry,arm)
    data=dict(job=job,entry_sha256=fingerprint(entry),order=job['order'],arms=arms,native_settle_calls=2,training_calls=0,world_measure_calls=0)
    verify.audit_pair(data,job,entry,p['scalar_tolerance']);put(out/(job['key']+'.json'),data)
def audit(out):
    p=inputs();data={j['key']:read(out/(j['key']+'.json')) for j in p['cases']};s=verify.audit_all(data,p);s['targeted_rejections']=verify.mutations(data,p);put(out/'summary.json',s)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args();out=ROOT/'runs/technical'
    from hcr.tasks.toy_world import World
    def no_measure(*a,**k):raise AssertionError('R30 world measurement forbidden')
    World.measure=no_measure
    if args.phase=='run':runner.spec=spec;runner.__file__=__file__;runner.run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='case':
        key,arm=args.item.rsplit('__',1);require(arm=='pair','pair arm');p=inputs();execute(out,p,next(j for j in p['cases'] if j['key']==key))
    elif args.phase=='audit':audit(out)
    else:
        import resource
        from tools.r30_spatial_sharing.selfcheck import check
        p=inputs();result=check();result['child_limits']=dict(address_space=resource.getrlimit(resource.RLIMIT_AS),file_size=resource.getrlimit(resource.RLIMIT_FSIZE))
        require(result['child_limits']['address_space']==(p['limits']['child_address_space_bytes'],)*2 and result['child_limits']['file_size']==(p['limits']['child_file_bytes'],)*2,'child resource limits');put(out/'preparation.json',result)
