"""Post-run transport/replay check. Reads saved data; forbids native execution."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from tools.r20_evidence_feedback import probe


def main():
    a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    started=time.perf_counter();evidence=args.evidence;raw=evidence/'raw';p=probe.spec()
    package=probe.read(evidence/'package.json');sources=probe.read(evidence/'source-manifest.expected.json')
    probe.require(probe.sha(evidence/'source-manifest.expected.json')==package['source_manifest_sha256'],'frozen source manifest digest')
    probe.require(all(probe.sha(ROOT/name)==digest for name,digest in sources.items()),'local frozen source changed')
    manifest=probe.read(raw/'manifest.json');jsons=[path for path in raw.glob('*.json') if path.name!='manifest.json']
    probe.require(len(jsons)==36 and all(probe.sha(path)==manifest[path.name] for path in jsons),'raw36 digest')
    result=probe.read(raw/'result.json');completion=probe.read(evidence/'completion.actual.json')
    post=probe.read(evidence/'source-postcheck.redacted.json')
    probe.require(result['status']=='COMPLETED' and len(result['stages'])==35 and all(s['returncode']==0 for s in result['stages']),'remote35 stages')
    probe.require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'server completion')
    probe.require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source report')
    probe.require(post['unchanged'] and len(post['files'])==74 and all(post['files'].values()),'redacted source postcheck report')
    summary=probe.read(raw/'summary.json');truth=probe.read(probe.SPEC.with_name('reference.json'))
    def forbidden(*args,**kwargs):raise AssertionError('native tick/settle forbidden')
    dynamics.tick=dynamics.settle=forbidden
    maximum=0.0;cells=0;ticks=0;settles=0
    for cell in p['cases']:
        key,case=cell['key'],cell['public']
        for arm in p['arms']:
            path=raw/(key+'__'+arm+'.json');record=probe.read(path)
            maximum=max(maximum,probe.audit_execution(record,case,arm,p,p['numeric_replay_absolute_tolerance_portable']))
            row=next(row for row in summary['rows'] if row['key']==key and row['arm']==arm)
            for name in ['category','relation','gate','gate_wall_seconds']:
                probe.require(row[name]==record[name],'summary field '+name)
            for name in ['kernel_ticks','group_updates','signal_transmissions']:
                probe.require(row[name]==sum(k['cost'][name] for k in record['kernels']),'summary cost '+name)
            for name in ['category','relation']:
                value=record[name]
                probe.require(row[name+'_correct']==(value is not None and value==truth[key][name]),'summary correctness')
                probe.require(row[name+'_wrong']==(value is not None and value!=truth[key][name]),'summary wrong')
                probe.require(row[name+'_abstained']==(value is None),'summary abstention')
            probe.require(row['execution_bytes']==path.stat().st_size,'summary bytes')
            cells+=1;settles+=len(record['kernels']);ticks+=sum(len(k['ticks']) for k in record['kernels'])
    for arm,total in summary['totals'].items():
        for name,value in total.items():
            probe.require(value==sum(row[name] for row in summary['rows'] if row['arm']==arm),'summary aggregate '+name)
    # PRE gate hashes the lower trace first. Test the deeper validators without a gate.
    case=next(c['public'] for c in p['cases'] if c['key']=='clear_A')
    original=probe.read(raw/'clear_A__bottom_up.json');rejections={}
    for mutation,expected in [('tick_state','scalar replay tick mismatch'),('program_bias','fixed program')]:
        bad=deepcopy(original)
        if mutation=='tick_state':bad['kernels'][0]['ticks'][0]['state']['goal']+=.01
        else:bad['kernels'][0]['program']['groups'][0]['bias']+=.1
        try:probe.audit_execution(bad,case,'bottom_up',p,p['numeric_replay_absolute_tolerance_portable'])
        except ValueError as error:
            probe.require(str(error)==expected,'unexpected rejection cause');rejections[mutation]=str(error)
        else:raise ValueError('targeted mutation accepted')
    receipt=dict(status='SAVED_AVAILABLE_RECORD_REPLAY_PASSED',raw_json_digest_count=36,cells=cells,recorded_settle_calls=settles,
        recorded_native_ticks=ticks,native_tick_calls=0,native_settle_calls=0,numeric_replay_max_absolute_error=maximum,
        numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_portable'],targeted_rejections=rejections,
        local_frozen_source_files_verified=74,server_source_unchanged_reported=True,
        remote_source_postcheck_exact_bytes_received=False,remote_source_manifest_exact_bytes_received=False,
        source_postcheck_redacted_key_count=sum('[REDACTED' in key for key in post['files']),
        summary_sha256=probe.sha(raw/'summary.json'),replay_wall_seconds=time.perf_counter()-started)
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
