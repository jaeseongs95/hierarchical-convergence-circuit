"""Post-run saved evidence verifier; never performs native work or new timing."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r25_fixedpoint_elision import probe,shortcut

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();e=args.evidence;raw=e/'raw';p=probe.spec();require=probe.require
    package=probe.read(e/'package.json');sources=probe.read(e/'source_manifest.pre-frozen.json')
    require(probe.sha(e/'source_manifest.pre-frozen.json')==package['source_manifest_sha256'],'pre-frozen manifest digest')
    require(len(sources)==package['source_files']==121 and all(probe.sha(ROOT/n)==h for n,h in sources.items()),'local frozen source121')
    manifest=probe.read(raw/'manifest.json');names=['correctness.json','timing.json','preparation.json','result.json','summary.json']
    require(all(probe.sha(raw/n)==manifest[n] for n in names),'five exact raw digests')
    result=probe.read(raw/'result.json');prep=probe.read(raw/'preparation.json');completion=probe.read(e/'completion.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==3 and all(s['returncode']==0 for s in result['stages']),'server three stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source report binding')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'completion')
    require(prep['status']=='PURE_BOUNDARIES_PASSED' and prep['assertions']==18,'server preparation')
    limits=p['limits']
    for seen,prefix in [(result['parent_limits'],'parent'),(prep['child_limits'],'child')]:
        require(seen==dict(address_space=[limits[prefix+'_address_space_bytes']]*2,file_size=[limits[prefix+'_file_bytes']]*2),'observed limits')
    require(all(0<=s['raw_bytes']<limits['raw_bytes'] and s['wall_seconds']<limits['stage_seconds'] for s in result['stages']),'observed stage bounds')
    from hcr import dynamics
    from hcr.tasks.toy_world import World
    def forbidden(*args,**kwargs):raise AssertionError('new native/timing forbidden in saved replay')
    dynamics.tick=dynamics.settle=World.measure=shortcut.NATIVE_TICK=shortcut.invoke=probe.old.settle_one=forbidden
    items,cfg,source_maximum=probe.kernels();data=probe.read(raw/'correctness.json');summary=probe.read(raw/'summary.json');timing=probe.read(raw/'timing.json')
    totals,maximum,checksum=probe.validate_correctness(data,items,cfg);performance=probe.validate_timing(timing,totals,checksum);rejections={}
    require(totals==summary['totals_per_workload'] and performance==summary['performance'] and summary['correctness_bit_exact'] and summary['pairs']==36,'summary binding')
    require(data['source_scalar_error']<=p['scalar_tolerance'] and summary['scalar_max_absolute_error']<=p['scalar_tolerance'] and summary['scalar_tolerance']==p['scalar_tolerance'],'server numeric tolerance')
    for name,reason in [('state','exact semantic trace'),('cost','exact semantic trace'),('stable','exact semantic trace'),('ledger','physical ledger')]:
        try:probe.validate_correctness(probe.mutated(data,name),items,cfg)
        except ValueError as exc:require(str(exc)==reason,'mutation cause');rejections[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    bad=probe.deepcopy(timing);bad['blocks'][0]['arms']['baseline']['settles']-=1
    try:probe.validate_timing(bad,totals,checksum)
    except ValueError as exc:require(str(exc)=='timing workload ledger','mutation cause');rejections['timing_workload']=str(exc)
    else:raise ValueError('timing mutation accepted')
    require(rejections==summary['targeted_rejections'],'targeted rejections')
    repeats=1+p['timing_pairs']*p['repeats_per_block'];settles=36*2*repeats;logical=988*2*repeats;actual=sum(t['native_tick_calls'] for t in totals.values())*repeats
    require(summary['total_native_settle_calls']==settles==2088 and summary['total_logical_ticks']==logical==57304<=p['maximum_logical_ticks'],'global work binding')
    require(summary['training_calls']==summary['world_measure_calls']==0 and summary['original_r19_status']=='FAILED_AT_AUDIT' and not summary['original_source_postcheck_complete'],'scope/history binding')
    receipt=dict(status='SAVED_NATIVE_COMPONENT_REPLAY_PASSED',exact_raw_json_digest_count=5,local_source_files_verified=121,local_pre_frozen_manifest_verified=True,remote_source_reports_redacted=True,remote_manifest_exact_bytes_verified=False,remote_source_postcheck_exact_bytes_verified=False,server_reports_source_unchanged=True,server_zip_received_locally=False,stdout_stderr_files_received=0,stdout_stderr_files_in_manifest=6,bit_exact_kernel_pairs=36,source_scalar_max_absolute_error=source_maximum,native_trace_scalar_max_absolute_error=maximum,scalar_absolute_tolerance=p['scalar_tolerance'],targeted_rejections=rejections,performance=performance,totals_per_workload=totals,total_server_native_settle_calls=settles,total_server_native_tick_calls=actual,total_server_logical_ticks=logical,total_server_omitted_tick_arithmetic=logical-actual,new_local_native_calls=0,new_local_timing_runs=0,all_server_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),stage_raw_peak_bytes=max(s['raw_bytes'] for s in result['stages']),summary_sha256=probe.sha(raw/'summary.json'),review_kind='same-implementation saved replay; not independent audit')
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
