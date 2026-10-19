"""Verify transported bytes and replay frozen R22 records without new native calls."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.tasks.toy_world import World
from tools.r22_measurement_adoption import probe


def main():
    a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    started=time.perf_counter();e=args.evidence;raw=e/'raw';p=probe.spec();require=probe.require
    package=probe.read(e/'package.json');sources=probe.read(e/'source-manifest.json')
    require(probe.sha(e/'source-manifest.json')==package['source_manifest_sha256'],'source manifest digest')
    require(len(sources)==82 and all(probe.sha(ROOT/n)==h for n,h in sources.items()),'frozen source82')
    manifest=probe.read(raw/'manifest.json');files=[f for f in raw.glob('*.json') if f.name!='manifest.json']
    require(len(files)==43 and all(probe.sha(f)==manifest[f.name] for f in files),'raw43 digests')
    result=probe.read(raw/'result.json');completion=probe.read(e/'completion.json');post=probe.read(raw/'source-postcheck.json');prep=probe.read(raw/'preparation.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==41 and all(s['returncode']==0 for s in result['stages']),'server41 stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source binding')
    require(post['unchanged'] and set(post['files'])==set(sources) and all(post['files'].values()),'source postcheck')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'server completion')
    limits=p['limits']
    for observed,prefix in [(result['parent_limits'],'parent'),(prep['child_limits'],'child')]:
        require(observed==dict(address_space=[limits[prefix+'_address_space_bytes']]*2,file_size=[limits[prefix+'_file_bytes']]*2),'observed resource limits')
    require(all(0<=s['raw_bytes']<limits['raw_bytes'] and s['wall_seconds']<limits['stage_seconds'] for s in result['stages']),'observed stage limits')
    summary=probe.read(raw/'summary.json');truth=probe.read(probe.SPEC.with_name('reference.json'));fixtures=probe.read(probe.SPEC.with_name('sensor-fixtures.json'))
    require(len(summary['rows'])==39,'summary39')
    def forbidden(*args,**kwargs):raise AssertionError('new native execution forbidden in replay')
    dynamics.tick=dynamics.settle=probe.base.common.settle_one=World.measure=forbidden
    rows=[];records={};maximum=0.;tolerance=p['numeric_replay_absolute_tolerance_portable']
    for cell in p['cases']:
        key,public=cell['key'],cell['public']
        for arm in p['arms']:
            path=raw/(key+'__'+arm+'.json');record=probe.read(path);records[key,arm]=record
            maximum=max(maximum,probe.audit_execution(record,public,arm,p,fixtures[key],tolerance))
            row=next(r for r in summary['rows'] if r['key']==key and r['arm']==arm)
            expected=dict(key=key,arm=arm,category=record['final']['category'],relation=record['final']['relation'],initial_category=record['initial']['category'],
                request_reason=record['request_gate']['reason'],adoption_reason=None if record['adoption'] is None else record['adoption']['reason'],
                final_source=record['final_source'],requests=record['ledger']['requests_used'],feature_units=record['ledger']['feature_units_charged'],
                additional_settles_reserved=record['ledger']['additional_settles_reserved'],additional_settles_used=record['ledger']['additional_settles_used'],
                cost=record['cost'],measurement_wall_seconds=record['measurement_wall_seconds'],execution_bytes=path.stat().st_size)
            for name in ['category','relation']:
                v=record['final'][name];expected[name+'_correct']=v is not None and v==truth[key][name];expected[name+'_wrong']=v is not None and v!=truth[key][name];expected[name+'_abstained']=v is None
            require({k:v for k,v in row.items() if k!='numeric_replay_max_absolute_error'}==expected,'summary row binding')
            require(row['numeric_replay_max_absolute_error']==0,'server exact replay reported');rows.append(row)
    require(set(summary['totals'])==set(p['arms']),'all arms')
    for arm,total in summary['totals'].items():
        group=[r for r in rows if r['arm']==arm]
        for name,value in total.items():
            if name=='cost':require(value=={phase:{n:sum(r['cost'][phase][n] for r in group) for n in group[0]['cost'][phase]} for phase in ['initial','revision','total']},'aggregate costs')
            else:require(value==sum(r[name] for r in group),'aggregate '+name)
    rejections={}
    for mutation,expected in probe.MUTATIONS.items():
        key,arm=('clear_A','no_query') if mutation.startswith('upper_') else ('missing_aux_A','corroborated')
        public=next(c['public'] for c in p['cases'] if c['key']==key)
        try:probe.audit_execution(probe.mutate(records[key,arm],mutation),public,arm,p,fixtures[key],tolerance)
        except ValueError as exc:require(str(exc)==expected,'mutation rejection cause');rejections[mutation]=str(exc)
        else:raise ValueError('mutation accepted '+mutation)
    require(rejections==summary['targeted_rejections'],'server mutation binding')
    requests=sum(r['requests'] for r in rows);settles=sum(r['cost']['total']['native_settle_calls'] for r in rows);probe.global_caps(requests,settles,p)
    matched=[c['key'] for c in p['cases'] if records[c['key'],'single_contract']['provider_calls']==1 and records[c['key'],'corroborated']['provider_calls']==2]
    strata={arm:{n:sum(r[n] for r in rows if r['key'] in matched and r['arm']==arm) for n in ['category_correct','category_wrong','category_abstained','requests','feature_units']} for arm in p['arms']}
    receipt=dict(status='SAVED_RECORD_REPLAY_PASSED',raw_json_digest_count=43,cells=39,recorded_native_settle_calls=settles,recorded_world_measure_calls=requests,
        recorded_native_ticks=sum(r['cost']['total']['kernel_ticks'] for r in rows),new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,
        numeric_replay_max_absolute_error=maximum,numeric_replay_absolute_tolerance=tolerance,targeted_rejections=rejections,source_files_verified=82,
        source_manifest_exact_bytes_verified=True,source_postcheck_exact_bytes_verified=True,server_zip_received_locally=False,
        observed_parent_limits=result['parent_limits'],observed_preparation_worker_limits=prep['child_limits'],observed_stage_raw_max_bytes=max(s['raw_bytes'] for s in result['stages']),
        case_child_cpu_seconds={arm:sum(s['child_cpu_seconds'] for s in result['stages'] if s['phase']=='case' and s['item'].endswith('__'+arm)) for arm in p['arms']},
        case_wall_seconds={arm:sum(s['wall_seconds'] for s in result['stages'] if s['phase']=='case' and s['item'].endswith('__'+arm)) for arm in p['arms']},
        all_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),matched_request_case_keys=matched,matched_request_subset=strata,
        summary_sha256=probe.sha(raw/'summary.json'),replay_wall_seconds=time.perf_counter()-started)
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
