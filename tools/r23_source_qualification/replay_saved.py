"""Post-run byte verification and scalar replay; no new inference or measurement."""
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
from tools.r23_source_qualification import probe

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    started=time.perf_counter();e=args.evidence;raw=e/'raw';p=probe.spec();require=probe.require
    package=probe.read(e/'package.json');sources=probe.read(e/'source_manifest.json')
    require(probe.sha(e/'source_manifest.json')==package['source_manifest_sha256'],'source manifest digest')
    require(len(sources)==package['source_files']==87 and all(probe.sha(ROOT/n)==h for n,h in sources.items()),'frozen source87')
    manifest=probe.read(raw/'manifest.json');files=[f for f in raw.glob('*.json') if f.name!='manifest.json']
    require({f.name for f in files}=={n for n in manifest if n.endswith('.json')},'received JSON set')
    require(len(files)==45 and all(probe.sha(f)==manifest[f.name] for f in files),'raw45 digests')
    result=probe.read(raw/'result.json');completion=probe.read(e/'completion.json');post=probe.read(raw/'source-postcheck.json');prep=probe.read(raw/'preparation.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==42 and all(s['returncode']==0 for s in result['stages']),'server42 stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source binding')
    require(post['unchanged'] and set(post['files'])==set(sources) and all(post['files'].values()),'source postcheck')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'completion')
    limits=p['limits']
    for observed,prefix in [(result['parent_limits'],'parent'),(prep['child_limits'],'child')]:
        require(observed==dict(address_space=[limits[prefix+'_address_space_bytes']]*2,file_size=[limits[prefix+'_file_bytes']]*2),'observed resource limits')
    require(all(0<=s['raw_bytes']<limits['raw_bytes'] and s['wall_seconds']<limits['stage_seconds'] for s in result['stages']),'observed stage limits')
    summary=probe.read(raw/'summary.json');regenerated=[];tolerance=p['numeric_replay_absolute_tolerance_portable']
    def forbidden(*args,**kwargs):raise AssertionError('new native work forbidden in saved replay')
    original=(dynamics.tick,dynamics.settle,World.measure,probe.base.execute,probe.base.common.settle_one,probe.put,probe.spec)
    dynamics.tick=dynamics.settle=World.measure=probe.base.execute=probe.base.common.settle_one=forbidden
    def collect(path,obj):
        require(path==raw/'summary.json','only summary capture permitted');regenerated.append(obj)
    portable=deepcopy(p);portable['numeric_replay_absolute_tolerance_server']=tolerance
    probe.spec=lambda:portable;probe.put=collect
    try:probe.audit(raw)
    finally:dynamics.tick,dynamics.settle,World.measure,probe.base.execute,probe.base.common.settle_one,probe.put,probe.spec=original
    require(len(regenerated)==1,'one regenerated summary');replayed=regenerated[0]
    maximum=max(r['numeric_replay_max_absolute_error'] for r in replayed['rows'])
    for r in replayed['rows']:
        saved=next(s for s in summary['rows'] if (s['key'],s['arm'])==(r['key'],r['arm']))
        require(saved['numeric_replay_max_absolute_error']==0.,'server exact replay')
        require({k:v for k,v in r.items() if k!='numeric_replay_max_absolute_error'}=={k:v for k,v in saved.items() if k!='numeric_replay_max_absolute_error'},'replayed row binding')
    require({k:v for k,v in replayed.items() if k!='rows'}=={k:v for k,v in summary.items() if k!='rows'},'replayed aggregate and qualification binding')
    receipts=dict(status='SAVED_RECORD_REPLAY_PASSED',raw_json_digest_count=45,cells=40,source_files_verified=87,
        numeric_replay_max_absolute_error=maximum,numeric_replay_absolute_tolerance=tolerance,
        recorded_native_settle_calls=sum(t['cost']['total']['native_settle_calls'] for t in summary['totals'].values()),
        recorded_world_measure_calls=summary['calibration_requests']+sum(t['requests'] for t in summary['totals'].values()),
        recorded_native_ticks=sum(t['cost']['total']['kernel_ticks'] for t in summary['totals'].values()),
        new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,targeted_rejections=summary['targeted_rejections'],
        observed_parent_limits=result['parent_limits'],observed_preparation_worker_limits=prep['child_limits'],observed_stage_raw_max_bytes=max(s['raw_bytes'] for s in result['stages']),
        case_child_cpu_seconds={arm:sum(s['child_cpu_seconds'] for s in result['stages'] if s['phase']=='case' and s['item'].endswith('__'+arm)) for arm in p['arms']},
        case_wall_seconds={arm:sum(s['wall_seconds'] for s in result['stages'] if s['phase']=='case' and s['item'].endswith('__'+arm)) for arm in p['arms']},
        all_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),source_manifest_exact_bytes_verified=True,source_postcheck_exact_bytes_verified=True,
        server_zip_received_locally=False,stdout_stderr_files_received=0,stdout_stderr_files_in_manifest=sum(n.endswith(('.stdout','.stderr')) for n in manifest),
        summary_sha256=probe.sha(raw/'summary.json'),replay_wall_seconds=time.perf_counter()-started)
    probe.put(args.out,receipts);print(json.dumps(receipts,sort_keys=True))

if __name__=='__main__':main()
