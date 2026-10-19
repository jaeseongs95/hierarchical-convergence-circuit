"""Local saved-result verifier. No native recurrence or new timing is allowed."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r26_contraction_warmstart import probe

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();e=args.evidence;raw=e/'raw';require=probe.require
    package=probe.read(e/'package.json');sources=probe.read(e/'source_manifest.pre-frozen.json')
    require(probe.sha(e/'source_manifest.pre-frozen.json')==package['source_manifest_sha256'],'pre-frozen manifest digest')
    require(len(sources)==package['source_files']==96 and all(probe.sha(ROOT/n)==h for n,h in sources.items()),'local frozen source96')
    from hcr import dynamics
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise AssertionError('native/timing forbidden in saved replay')
    dynamics.tick=dynamics.settle=World.measure=probe.execute=probe.old.settle_one=forbidden
    p,cfg,_,pr=probe.inputs();names=[s['key']+'.json' for s in p['streams']]+['preparation.json','result.json','summary.json'];manifest=probe.read(raw/'manifest.json')
    require(len(names)==7 and all(probe.sha(raw/n)==manifest[n] for n in names),'seven exact raw JSON digests')
    result=probe.read(raw/'result.json');prep=probe.read(raw/'preparation.json');completion=probe.read(e/'completion.json');summary=probe.read(raw/'summary.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==6 and all(s['returncode']==0 for s in result['stages']),'six server stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source report binding')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<p['limits']['total_seconds'],'completion')
    require(prep['status']=='PURE_POLICY_MATH_PASSED' and prep['assertions']==35 and prep['new_native_calls']==prep['new_timing_runs']==0,'server preparation')
    for seen,prefix in [(result['parent_limits'],'parent'),(prep['child_limits'],'child')]:
        require(seen==dict(address_space=[p['limits'][prefix+'_address_space_bytes']]*2,file_size=[p['limits'][prefix+'_file_bytes']]*2),'observed limits')
    require(all(0<=s['raw_bytes']<p['limits']['raw_bytes'] and s['wall_seconds']<p['limits']['stage_seconds'] for s in result['stages']),'stage bounds')
    data={s['key']:probe.read(raw/(s['key']+'.json')) for s in p['streams']};rebuilt=probe.aggregate(data,p,pr,cfg);maximum=rebuilt.pop('scalar_max_absolute_error');saved=dict(summary);server_maximum=saved.pop('scalar_max_absolute_error');rejections=saved.pop('targeted_rejections')
    require(rebuilt==saved and maximum<=p['scalar_tolerance'] and server_maximum<=p['scalar_tolerance'],'saved aggregate binding')
    stream=p['streams'][0];observed={}
    for name,reason in probe.MUTATIONS.items():
        try:probe.audit_one(probe.mutate(data[stream['key']],name),stream,p,pr,cfg)
        except ValueError as exc:require(str(exc)==reason,'mutation cause');observed[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    require(observed==rejections,'saved mutation binding')
    receipt=dict(status='SAVED_WARMSTART_REPLAY_PASSED',exact_raw_json_digest_count=7,local_frozen_source_files_verified=96,native_settle_calls_on_server=sum(t['native_settle_calls'] for t in summary['totals'].values()),native_ticks_on_server=sum(t['kernel_ticks'] for t in summary['totals'].values()),local_scalar_max_absolute_error=maximum,server_scalar_max_absolute_error=server_maximum,scalar_tolerance=p['scalar_tolerance'],terminal_state_tolerance=p['terminal_state_tolerance'],totals=summary['totals'],targeted_rejections=observed,guarded_observed_quality_preserved=summary['guarded_observed_quality_preserved'],unconditional_carry_changed_readouts=summary['unconditional_carry_changed_readouts'],new_local_native_calls=0,new_local_timing_runs=0,all_server_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),stage_raw_peak_bytes=max(s['raw_bytes'] for s in result['stages']),summary_sha256=probe.sha(raw/'summary.json'),source_verification_scope='Local pre-frozen source bytes plus server unchanged report; remote source list retrieval limitations belong in transport receipt.',independent_audit=False)
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
