"""Post-run verifier. Verifies four complete JSON files; remote source lists are redacted."""
import argparse,json,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r24_trust_boundary import probe,census

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    started=time.perf_counter();e=args.evidence;raw=e/'raw';p=probe.spec();require=probe.require
    package=probe.read(e/'package.json');sources=probe.read(e/'source_manifest.pre-frozen.json')
    require(probe.sha(e/'source_manifest.pre-frozen.json')==package['source_manifest_sha256'],'pre-frozen manifest digest')
    require(len(sources)==package['source_files']==107 and all(probe.sha(ROOT/n)==h for n,h in sources.items()),'local frozen source107')
    manifest=probe.read(raw/'manifest.json');names=['census.json','preparation.json','result.json','summary.json']
    require(all(probe.sha(raw/n)==manifest[n] for n in names),'four exact raw digests')
    result=probe.read(raw/'result.json');prep=probe.read(raw/'preparation.json');completion=probe.read(e/'completion.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==3 and all(s['returncode']==0 for s in result['stages']),'server three stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source report binding')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'completion')
    limits=p['limits']
    for seen,prefix in [(result['parent_limits'],'parent'),(prep['child_limits'],'child')]:
        require(seen==dict(address_space=[limits[prefix+'_address_space_bytes']]*2,file_size=[limits[prefix+'_file_bytes']]*2),'observed limits')
    require(all(0<=s['raw_bytes']<limits['raw_bytes'] and s['wall_seconds']<limits['stage_seconds'] for s in result['stages']),'observed stage bounds')
    probe.forbid_native();prior,records,maximum=probe.verified_inputs(p)
    data=probe.read(raw/'census.json');summary=probe.read(raw/'summary.json');summaries={};rejections={};details={}
    for arm in p['transition_arms']:
        events=probe.events_for(p,prior,records,arm)
        for scope in p['scopes']:
            key=arm+'__'+scope;a=data['analyses'][key];census.audit(a,events,scope,p)
            summaries[key]=dict(a['summary'],analysis_cpu_seconds=a['analysis_cpu_seconds'],analysis_wall_seconds=a['analysis_wall_seconds'])
            hits=[(row,event) for row,event in zip(a['rows'],events,strict=True) if row['hit']]
            details[key]=dict(fixed_point_hits=sum(census.freeze(ev['current'])==census.freeze(ev['next']) for _,ev in hits),
                same_settle_nonfixed_hits=sum(row['locality']=='same_settle' and census.freeze(ev['current'])!=census.freeze(ev['next']) for row,ev in hits),
                hit_cases={case:sum(ev['case']==case for _,ev in hits) for case in p['source_case_order']},
                original_group_updates=sum(len(ev['program']['groups']) for ev in events),original_signal_transmissions=sum(len(ev['program']['links']) for ev in events))
            if (arm,scope)==('bottom_up','case_local'):
                for name,reason in census.MUTATIONS.items():
                    try:census.audit(census.mutated(a,name),events,scope,p)
                    except ValueError as exc:require(str(exc)==reason,'mutation cause');rejections[name]=str(exc)
                    else:raise ValueError('mutation accepted '+name)
    require(summaries==summary['analyses'] and rejections==summary['targeted_rejections'],'aggregate/mutation binding')
    require(data['saved_scalar_replay_max_absolute_error']==summary['numeric_replay_max_absolute_error']<=p['numeric_replay_absolute_tolerance_server'],'server replay binding')
    require(summary['case_local_candidate_opportunities']==sum(v['case_local_non_repeated_invocation_hits'] for k,v in summaries.items() if k.endswith('__case_local')),'candidate count')
    for record in [data,summary]:
        require([record[n] for n in ['source_case_files','source_settles','source_ticks']]==[18,36,988],'source count binding')
        require(record['original_status']=='FAILED_AT_AUDIT','history binding')
        require(all(record[n]==0 for n in ['new_native_tick_calls','new_native_settle_calls','new_world_measure_calls','training_calls']),'native scope flags')
    receipt=dict(status='SAVED_CENSUS_REPLAY_PASSED',exact_raw_json_digest_count=4,analytical_rows=1976,original_saved_ticks=988,
        local_source_files_verified=107,local_pre_frozen_manifest_verified=True,remote_manifest_exact_bytes_verified=False,remote_source_postcheck_exact_bytes_verified=False,
        remote_source_reports_redacted=True,summary_source_report_unchanged=result['source_unchanged'],server_zip_received_locally=False,
        numeric_replay_max_absolute_error=maximum,numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_portable'],
        new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,new_census_performance_run=False,targeted_rejections=rejections,
        hit_details=details,observed_parent_limits=result['parent_limits'],observed_preparation_worker_limits=prep['child_limits'],
        observed_stage_raw_max_bytes=max(s['raw_bytes'] for s in result['stages']),all_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),
        stdout_stderr_files_received=0,stdout_stderr_files_in_manifest=sum(n.endswith(('.stdout','.stderr')) for n in manifest),
        summary_sha256=probe.sha(raw/'summary.json'),replay_wall_seconds=time.perf_counter()-started)
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
