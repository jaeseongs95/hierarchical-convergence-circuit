"""Post-run byte checks and portable scalar replay; no new native experiment."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.tasks.toy_world import World
from tools.r21_active_measurement import probe


def main():
    a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    started=time.perf_counter();e=args.evidence;raw=e/'raw';p=probe.spec();require=probe.require
    package=probe.read(e/'package.json');sources=probe.read(e/'source-manifest.json')
    require(probe.sha(e/'source-manifest.json')==package['source_manifest_sha256'],'source manifest digest')
    require(len(sources)==78 and all(probe.sha(ROOT/n)==h for n,h in sources.items()),'frozen local source')
    manifest=probe.read(raw/'manifest.json');files=[f for f in raw.glob('*.json') if f.name!='manifest.json']
    require(len(files)==34 and all(probe.sha(f)==manifest[f.name] for f in files),'raw34 digests')
    result=probe.read(raw/'result.json');completion=probe.read(e/'completion.json');post=probe.read(raw/'source-postcheck.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==32 and all(s['returncode']==0 for s in result['stages']),'server32 stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source digest')
    require(post['unchanged'] and set(post['files'])==set(sources) and all(post['files'].values()),'source postcheck')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'server completion')
    summary=probe.read(raw/'summary.json');truth=probe.read(probe.SPEC.with_name('reference.json'));fixtures=probe.read(probe.SPEC.with_name('sensor-fixtures.json'))
    require(len(summary['rows'])==30,'summary30')
    def forbidden(*args,**kwargs):raise AssertionError('new native execution forbidden')
    dynamics.tick=dynamics.settle=probe.base.common.settle_one=World.measure=forbidden
    rows=[];records={};maximum=0.0;tolerance=p['numeric_replay_absolute_tolerance_portable']
    for cell in p['cases']:
        key,public=cell['key'],cell['public']
        for arm in p['arms']:
            path=raw/(key+'__'+arm+'.json');record=probe.read(path);records[key,arm]=record
            maximum=max(maximum,probe.audit_execution(record,public,arm,p,fixtures[key],tolerance))
            row=next(r for r in summary['rows'] if r['key']==key and r['arm']==arm)
            expected=dict(key=key,arm=arm,category=record['final']['category'],relation=record['final']['relation'],
                initial_category=record['initial']['category'],initial_primary_status=record['initial']['kernels'][0]['convergence']['status'],
                request_reason=record['request_gate']['reason'],response_error=record['response_error'],measurement_changed=record['measurement_changed'],
                final_source=record['final_source'],requests=record['ledger']['requests_used'],feature_units=record['ledger']['feature_units_charged'],
                additional_settles_reserved=record['ledger']['additional_settles_reserved'],additional_settles_used=record['ledger']['additional_settles_used'],
                cost=record['cost'],measurement_wall_seconds=record['measurement_wall_seconds'],execution_bytes=path.stat().st_size)
            for name in ['category','relation']:
                value=record['final'][name]
                expected[name+'_correct']=value is not None and value==truth[key][name]
                expected[name+'_wrong']=value is not None and value!=truth[key][name]
                expected[name+'_abstained']=value is None
            require({k:v for k,v in row.items() if k!='numeric_replay_max_absolute_error'}==expected,'summary row binding')
            require(row['numeric_replay_max_absolute_error']==0,'server exact replay reported')
            rows.append(row)
    for arm,total in summary['totals'].items():
        group=[r for r in rows if r['arm']==arm]
        for name,value in total.items():
            if name=='cost':
                require(value=={phase:{n:sum(r['cost'][phase][n] for r in group) for n in group[0]['cost'][phase]} for phase in ['initial','revision','total']},'aggregate costs')
            else:require(value==sum(r[name] for r in group),'aggregate '+name)
    require(set(summary['totals'])==set(p['arms']),'all arms')
    rejections={}
    for mutation,expected in [('request_gate','request gate binding'),('request_revision','request binding'),('charge_units','measurement charge ledger'),
        ('response_score','provider response binding'),('upper_tick','scalar replay tick mismatch'),('upper_program_bias','fixed program')]:
        key,arm=('clear_A','no_query') if mutation.startswith('upper_') else ('missing_aux_A','primary_uncertainty')
        bad=deepcopy(records[key,arm]);public=next(c['public'] for c in p['cases'] if c['key']==key)
        if mutation=='request_gate':bad['request_gate']['action']='retain'
        elif mutation=='request_revision':bad['request']['revision']+=1
        elif mutation=='charge_units':bad['ledger']['feature_units_charged']=0
        elif mutation=='response_score':bad['response']['observation']['edges'][0]['score']-=.01
        elif mutation=='upper_tick':bad['initial']['kernels'][1]['ticks'][0]['state']['goal']+=.01
        else:bad['initial']['kernels'][1]['program']['groups'][0]['bias']+=.1
        try:probe.audit_execution(bad,public,arm,p,fixtures[key],tolerance)
        except ValueError as error:
            require(str(error)==expected,'mutation rejection cause');rejections[mutation]=str(error)
        else:raise ValueError('mutation accepted '+mutation)
    require(rejections==summary['targeted_rejections'],'server mutation binding')
    requests=sum(r['requests'] for r in rows);settles=sum(r['cost']['total']['native_settle_calls'] for r in rows)
    require(requests<=p['maximum_measurement_requests'] and settles<=p['maximum_native_settle_calls'],'global caps')
    receipt=dict(status='SAVED_RECORD_REPLAY_PASSED',raw_json_digest_count=34,cells=30,recorded_native_settle_calls=settles,
        recorded_world_measure_calls=requests,recorded_native_ticks=sum(r['cost']['total']['kernel_ticks'] for r in rows),
        new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,numeric_replay_absolute_tolerance=tolerance,
        numeric_replay_max_absolute_error=maximum,targeted_rejections=rejections,source_files_verified=78,
        source_manifest_exact_bytes_verified=True,source_postcheck_exact_bytes_verified=True,server_zip_received_locally=False,
        case_child_cpu_seconds={arm:sum(s['child_cpu_seconds'] for s in result['stages'] if s['phase']=='case' and s['item'].endswith('__'+arm)) for arm in p['arms']},
        case_wall_seconds={arm:sum(s['wall_seconds'] for s in result['stages'] if s['phase']=='case' and s['item'].endswith('__'+arm)) for arm in p['arms']},
        all_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),summary_sha256=probe.sha(raw/'summary.json'),replay_wall_seconds=time.perf_counter()-started)
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
