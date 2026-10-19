"""Verify received R27 results without native calls or new timing experiments."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r27_finite_stop_envelope import probe

def main():
    a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args();e=args.evidence;raw=e/'raw';require=probe.require
    probe.prohibit_native();package=probe.read(e/'package.json');sources=probe.read(e/'source_manifest.pre-frozen.json')
    require(probe.sha(e/'source_manifest.pre-frozen.json')==package['source_manifest_sha256'] and len(sources)==package['source_files']==121,'sender manifest')
    require(all(probe.sha(ROOT/n)==h for n,h in sources.items()),'local source121')
    p,p26,cfg,program=probe.inputs();names=[s['key']+'.json' for s in p26['streams']]+['preparation.json','result.json','summary.json'];manifest=probe.read(raw/'manifest.json')
    require(len(names)==7 and all(probe.sha(raw/n)==manifest[n] for n in names),'seven raw JSON digests')
    result=probe.read(raw/'result.json');prep=probe.read(raw/'preparation.json');completion=probe.read(e/'completion.json');saved=probe.read(raw/'summary.json')
    require(result['status']=='COMPLETED' and len(result['stages'])==6 and all(s['returncode']==0 for s in result['stages']),'six server stages')
    require(result['source_unchanged'] and result['source_manifest_sha256']==package['source_manifest_sha256'],'server source report')
    require(completion['completed'] and completion['within_600_seconds'] and completion['seconds_including_seal']<600,'completion')
    require(prep['status']=='PURE_FINITE_ENVELOPE_CHECKS_PASSED' and prep['assertions']==23 and prep['prior_boundary_assertions']==35 and prep['new_native_calls']==prep['new_timing_runs']==prep['archived_research_certificates_generated']==0,'server preparation')
    for seen,prefix in [(result['parent_limits'],'parent'),(prep['child_limits'],'child')]:require(seen==dict(address_space=[p['limits'][prefix+'_address_space_bytes']]*2,file_size=[p['limits'][prefix+'_file_bytes']]*2),'resource limits')
    require(all(s['raw_bytes']<p['limits']['raw_bytes'] and s['wall_seconds']<60 for s in result['stages']),'stage bounds')
    data={s['key']:probe.read(raw/(s['key']+'.json')) for s in p26['streams']};cost=probe.ledger(p26);rebuilt=probe.aggregate(data,p,p26,cfg,program,cost);rebuilt['targeted_rejections']=probe.targeted_checks(data,cost,p26,cfg,program)
    require(rebuilt==saved,'exact saved aggregate and eight mutation rejections')
    receipt=dict(status='SAVED_FINITE_ENVELOPE_REPLAY_PASSED',exact_raw_json_digest_count=7,local_frozen_source_files_verified=121,totals=saved['totals'],point_status_counts=saved['point_status_counts'],saved_records=72,saved_pairs=48,targeted_rejections=saved['targeted_rejections'],new_local_native_calls=0,new_local_timing_runs=0,retrospective_only=True,independent_audit=False,production_adoption=False,all_server_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in result['stages']),stage_raw_peak_bytes=max(s['raw_bytes'] for s in result['stages']),summary_sha256=probe.sha(raw/'summary.json'),source_verification_scope='Local sender source121 plus server unchanged report, not a downloaded full remote source list or independent attestation')
    probe.put(args.out,receipt);print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
