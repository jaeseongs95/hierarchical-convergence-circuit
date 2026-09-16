#!/usr/bin/env python3
"""EXP-09 r2 요약 실패 기록을 새 폴더로 복구한다. 원본 수정·재추론·과거 시간값 생성은 하지 않는다."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from collect import (BaselineError, canonical, examine, inventory, linked, loads, read, require,
                     safe, sha, verify_bundle, write_csv, write_json)
from audit_probe import audit_record_data
from probe_analysis import semantic_decision, summarize, render

RECOVERY_SCHEMA = 'hcr-r02-exp09-recovery-v1'
KNOWN_ERROR = 'BaselineError: 재시도 대조의 memory 불일치'
OLD_TOOLS = {'collect.py','probe.py','probe_analysis.py','audit_probe.py'}
NEW_TOOLS = OLD_TOOLS | {'memory_equivalence.py','measurement_journal.py'}
REPO = Path(__file__).resolve().parents[2]


def real_root(path: Path) -> Path:
    require(all(not linked(p) for p in (path.absolute(), *path.absolute().parents)), '링크/junction 경로 금지')
    return path.resolve()


def hashes(root: Path) -> dict:
    return {n: sha(read(safe(root, n))) for n in sorted(inventory(root))}


def rows_from(root: Path, name: str) -> list[dict]:
    return [loads(line) for line in read(safe(root, name)).splitlines() if line.strip()]


def validate_raw(root: Path) -> tuple[dict, list[dict], list[dict], dict]:
    """이번에 확인된 요약 예외만 복구한다. 일반 실패를 완료로 승격하지 않는다."""
    failure = loads(read(safe(root, 'FAILED.json')))
    require(failure.get('state') == 'failed' and failure.get('error') == KNOWN_ERROR, '지원하는 EXP-09 요약 오류가 아님')
    require(not (root/'manifest.json').exists() and not (root/'status.json').exists(), '완료/부분 수용 기록을 덮어 복구하지 않음')
    plan = loads(read(safe(root, 'plan.json')))
    require(plan['schema']=='hcr-r02-exp09-plan-v2' and plan['protocol']=='exp09-paired-correction-cost-r2', '지원 plan 필요')
    require(plan['config_signature']==sha(canonical(plan['config'])), '설정 서명')
    require(plan['training_counts']==[3,6,9] and plan['correction_controls']==['measured_replay','same_score_control'], '계획 조건 변경')
    require(type(plan['repeats']) is int and 2<=plan['repeats']<=20 and plan['repeats']%2==0, '짝수 반복 계획')
    require(plan['cost_cases']==['same_structure','counterfactual','renamed_reordered','longer_composition','branched_composition'], '고정 비용 사례')
    require(plan['matrix']==dict(memory=['before','after'],measurement=['weak','measured'],circuits=[True,False]), '실험 행렬 변경')
    require(plan['original_labels_not_passed_to_engine'] is True, '평가 경계')
    expected_max=8+2+5*(1+plan['config']['kernel']['max_observation_requests'])+10*plan['repeats']
    require(plan['max_inferences']==expected_max, '최대 추론식 변경')
    tool_names=set(plan['tool_source_hashes'])
    require(tool_names in (OLD_TOOLS,NEW_TOOLS), '알 수 없는 실행 도구 snapshot')
    names=inventory(root)
    required={'FAILED.json','plan.json','events.jsonl','episodes.jsonl','live_after_adaptation.json',
              'original_run_audit.json','original_cost_analysis.json'} | {'tool_source/'+n for n in tool_names}
    optional={'memory_after_error.json'}
    if plan.get('measurement_journal'):
        require(plan['measurement_journal']=='measurements.jsonl','측정 journal 경로')
        required.add('measurements.jsonl')
    require(required<=names and names<=required|optional,'지원 원시 파일 누락/추가')
    for n, h in plan['tool_source_hashes'].items():
        require(sha(read(safe(root, 'tool_source/'+n)))==h,'기존 도구 hash 불일치: '+n)
    rows, events=rows_from(root,'episodes.jsonl'),rows_from(root,'events.jsonl')
    require(type(failure['inferences']) is int and len(rows)==failure['inferences'] and 0<len(rows)<=plan['max_inferences'],'실패 기록/추론 수 차이')
    return plan,rows,events,failure


def contract_from_records(rows: list[dict], events: list[dict]) -> dict:
    """기준 capture가 없을 때의 내부 대조 계약. 원래 baseline과의 동일성 검증으로 부르지 않는다."""
    rowmap={r['decision']['id']:r for r in rows}
    seeds={};memory=None
    for event in events:
        p=event['payload']
        if event['event']=='r02_engine_created': memory=p['memory_document']
        elif event['event']=='r02_memory_updated': memory=p['memory_document']
        elif event['event']=='r02_attempt_started':
            require(p['decision_id'] in rowmap and memory is not None,'출처 없는 attempt')
            r=rowmap[p['decision_id']]
            key=None
            if r['phase']=='adaptation' and r['decision']['attempt']==1:
                key={'measured_replay':'before','training_3':'training_3','training_9':'training_9'}.get(r['arm'])
            elif r['phase']=='factorial' and r['arm']=='after/weak/circuits': key='after'
            if key:
                require(key not in seeds,'초기 memory 중복')
                seeds[key]=deepcopy(memory)
    require(set(seeds)=={'before','after','training_3','training_9'},'기록의 초기 memory 누락')
    def one(phase,arm):
        rs=[r for r in rows if r['phase']==phase and r['arm']==arm]
        require(len(rs)==1,'기준 셀 누락/중복: '+phase+'/'+arm)
        return rs[0]
    weak=deepcopy(one('factorial','before/weak/graph_only')['observation'])
    measured=deepcopy(one('factorial','before/measured/graph_only')['observation'])
    for obs in (weak,measured):obs.update(episode_id='e900001',revision=0)
    cases={'conflict_truth':one('factorial','before/weak/graph_only')['external_truth']}
    for row in rows:
        if row['phase']=='cost_pairs' and row['replicate']==0 and row['arm']=='graph_only':
            require(row['case'] not in cases,'중복 비용 사례')
            cases[row['case']]={k:deepcopy(row[k]) for k in ('observation','external_truth')}
    return dict(seed_docs=seeds,weak=weak,measured=measured,cases=cases)


def contract_from_bundle(bundle: Path, plan: dict) -> dict:
    verify_bundle(bundle)
    require(sha(read(bundle/'bundle_manifest.json'))==plan['baseline_bundle_manifest_sha256'], '다른 baseline capture')
    data=examine(bundle/'run',bundle/'source')
    require(sha(data['run_bytes']['plan.json'])==plan['original_plan_sha256'], '원 실행 plan 불일치')
    require(plan['source_hashes']==data['plan']['source_hashes'] and plan['config']==data['plan']['config'], '실행 기준 변경')
    names=dict(before='memory_after_training.json',after='memory_after_adaptation.json',
               training_3='memory_training_3.json',training_9='memory_training_9.json')
    docs={}
    for key,name in names.items():
        packet=loads(data['run_bytes'][name])
        require(sha(canonical(packet['document']))==packet['sha256'],'baseline memory packet')
        docs[key]=packet['document']
    conflict=sorted((r for r in data['rows'] if r['phase']=='misconvergence' and r['arm']=='full'),key=lambda r:r['decision']['attempt'])
    require(len(conflict)>=2,'원 수정 관측 누락')
    weak,measured=deepcopy(conflict[0]['observation']),deepcopy(conflict[-1]['observation'])
    for obs in (weak,measured):obs.update(episode_id='e900001',revision=0)
    cases={'conflict_truth':conflict[0]['external_truth']}
    for case in plan['cost_cases']:
        rs=[r for r in data['rows'] if r['case']==case and r['arm'] in ('cold','graph_only')]
        require(len(rs)==1,'원 비용 사례 누락/중복')
        cases[case]={k:rs[0][k] for k in ('observation','external_truth')}
    return dict(seed_docs=docs,weak=weak,measured=measured,cases=cases)


def source_files(source: Path, plan: dict) -> dict[str, bytes]:
    expected={p.relative_to(source).as_posix() for p in (source/'src/hcr').rglob('*.py')}
    expected|={'hcr.py','configs/r01.toml','configs/r02.toml'}
    require(expected==set(plan['source_hashes']), '당시 실행 소스 집합과 다름; 해당 capture/source를 지정할 것')
    result={}
    for n,h in plan['source_hashes'].items():
        raw=read(safe(source,n))
        require(sha(raw)==h,'당시 소스와 다름: '+n+'; 과거 hash를 수정하지 말 것')
        result[n]=raw
    return result


def rebuild(source: Path, raw_root: Path, contract: dict) -> tuple[dict, dict]:
    plan,rows,events,_=validate_raw(raw_root)
    audit,persistence=audit_record_data(source,raw_root,plan,rows,events,**contract)
    persistence.update(save_seconds=None,load_seconds=None,
        timing_status='not_recorded_before_original_failure',
        note='direct/reload 전체 memory hash 검사 유지. 별도 arm의 ID 대응과 혼용하지 않는다.')
    init=None;seconds=None
    if plan.get('measurement_journal'):
        from measurement_journal import validate_measurements
        journal=rows_from(raw_root,'measurements.jsonl')
        for x in journal:
            if x['event']=='memory_saved':persistence['save_seconds']=x['payload']['elapsed_seconds']
            if x['event']=='memory_loaded':persistence['load_seconds']=x['payload']['elapsed_seconds']
        measures=validate_measurements(journal,events,persistence)
        init=measures['initializations'];seconds=measures['finished']['elapsed_seconds']
        persistence['timing_status']='recorded_before_original_failure'
    summary=summarize(rows,events,persistence)
    summary.update(original_run_state='failed',reanalysis_complete=True,
        records_complete_for_plan=True,new_inferences=0,new_independent_task_samples=0,
        initializations=init,measured_probe_seconds=seconds,
        measurement_gaps=[] if init is not None else ['engine initialization time','save/load time','probe end-to-end time'])
    audit.update(original_run_state='failed',audit_context='recovered_raw_records',
        original_completion_manifest_verified=False,event_tail_anchor='observed_raw_tail_not_original_completion_manifest')
    return summary,audit


def output_files(root: Path) -> dict:
    return {n:sha(read(safe(root,n))) for n in sorted(inventory(root,{'recovery_manifest.json'}))}


def verify_recovery(root: Path, bundle: Path | None = None) -> dict:
    root=real_root(root)
    manifest=loads(read(root/'recovery_manifest.json'))
    require(manifest['schema']==RECOVERY_SCHEMA and manifest['state']=='complete', '복구 manifest 필요')
    require(output_files(root)==manifest['files'],'복구 산출물 hash/목록 불일치')
    receipt=loads(read(root/'receipt.json'))
    require(receipt['original_run_state']=='failed' and receipt['new_inferences']==0,'복구 범위 변경')
    require(hashes(root/'original')==receipt['original_file_hashes'],'원본 snapshot 파일 차이')
    plan,_,_,_=validate_raw(root/'original')
    source_files(root/'source',plan)
    contract=loads(read(root/'baseline_contract.json'))
    if bundle is not None:
        bundle=real_root(bundle)
        require(contract==contract_from_bundle(bundle,plan),'복구된 baseline 입력 계약 차이')
    summary,audit=rebuild(root/'source',root/'original',contract)
    require(loads(read(root/'summary.json'))==summary,'복구 summary 재집계 불일치')
    stored=loads(read(root/'audit.json'))
    require(all(stored[k]==v for k,v in audit.items()),'복구 audit 재계산 불일치')
    require(loads(read(root/'candidate_trace.json'))==summary['details']['candidates'],'후보 집계 차이')
    require(loads(read(root/'feedback_changes.json'))==summary['details']['feedback'],'학습 집계 차이')
    require(output_files(root)==manifest['files'],'검산 중 복구 산출물 변경')
    return dict(schema='hcr-exp09-recovery-verification-v1',state='complete',verified=True,
                records=audit['records'],events=audit['events'],scalar_ticks_replayed=audit['scalar_ticks_replayed'],
                memory_updates_checked=audit['memory_updates_checked'],proofs_reassessed=audit['proofs_reassessed'],
                cost_pairs=audit['cost_pairs'],original_run_state='failed',new_inferences=0,
                baseline_capture_reverified=bundle is not None,full_runtime_graph_audit=False)


def recover(run: Path, out: Path, source: Path | None = None, bundle: Path | None = None) -> dict:
    run,out=real_root(run),real_root(out)
    bundle=real_root(bundle) if bundle is not None else None
    source=real_root(source if source is not None else bundle/'source' if bundle else REPO)
    protected=[run,source,REPO]+([bundle] if bundle is not None else [])
    require(not out.exists() and all(not out.is_relative_to(p) and not p.is_relative_to(out) for p in protected),
            '출력은 원본/소스/저장소/capture와 분리된 새 폴더여야 함')
    original_hashes=hashes(run)
    plan,rows,events,failure=validate_raw(run)
    sources=source_files(source,plan)
    contract=contract_from_bundle(bundle,plan) if bundle is not None else contract_from_records(rows,events)
    raw={n:read(safe(run,n)) for n in original_hashes}
    require({n:sha(b) for n,b in raw.items()}==original_hashes,'수집 중 원본 변경')
    out.mkdir(parents=True,exist_ok=False)
    try:
        for folder,files in (('original',raw),('source',sources)):
            for name,data in files.items():
                dest=safe(out,folder+'/'+name);dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:f.write(data)
        write_json(out/'baseline_contract.json',contract)
        summary,audit=rebuild(out/'source',out/'original',contract)
        audit['baseline_capture_verified_at_recovery']=bundle is not None
        write_json(out/'summary.json',summary)
        write_json(out/'audit.json',audit)
        write_json(out/'candidate_trace.json',summary['details']['candidates'])
        write_json(out/'feedback_changes.json',summary['details']['feedback'])
        write_csv(out/'costs.csv',summary['details']['costs'])
        heading=('# EXP-09 요약 오류 복구 보고서\n\n'
                 '원본은 실패 상태로 보존했다. 다음은 이미 기록된 추론의 재집계·검산이며 새 추론이 아니다.\n\n'
                 f"기준 capture 재검사: {bundle is not None}. "
                 'False인 경우 초기 조건은 원시 기록 내부의 대응만 검사했다.\n'
                 '과거 초기화·save/load 시간이 남지 않았으면 null로 두며 0으로 대체하지 않는다.\n\n')
        with (out/'summary.ko.md').open('x',encoding='utf-8',newline='\n') as f:f.write(heading+render(summary))
        tools={}
        for name in ('recover_probe.py','audit_probe.py','probe_analysis.py','memory_equivalence.py','collect.py','measurement_journal.py'):
            data=read(Path(__file__).with_name(name));tools[name]=sha(data)
            dest=out/'recovery_tool_source'/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
        receipt=dict(schema=RECOVERY_SCHEMA,state='complete',original_run_state='failed',original_failure=failure,
            recovered_at_utc=datetime.now(timezone.utc).isoformat(),original_file_hashes=original_hashes,
            original_run_modified=False,new_inferences=0,source_plan_sha256=sha(raw['plan.json']),
            original_completion_manifest_verified=False,baseline_capture_verified=bundle is not None,
            baseline_contract_basis='verified_capture' if bundle else 'record_internal_consistency',
            recovery_tool_hashes=tools,missing_times_recreated=False)
        require(hashes(run)==original_hashes,'복구 중 원본 변경')
        source_files(source,plan)
        write_json(out/'receipt.json',receipt)
        write_json(out/'recovery_manifest.json',dict(schema=RECOVERY_SCHEMA,state='complete',files=output_files(out)))
        verified=verify_recovery(out,bundle)
        require(hashes(run)==original_hashes,'최종 검사 중 원본 변경')
        return dict(output=str(out),**verified)
    except BaseException as error:
        if not (out/'RECOVERY_FAILED.json').exists():
            write_json(out/'RECOVERY_FAILED.json',dict(state='failed',error=type(error).__name__+': '+str(error)))
        raise


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--run',type=Path,help='원본 실패 폴더; 읽기만 한다')
    mode.add_argument('--verify',type=Path,help='생성한 복구 폴더 재검산')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--source-root',type=Path,help='당시 실행 source. 생략 시 --bundle/source 또는 현재 저장소')
    parser.add_argument('--bundle',type=Path,help='기존 baseline capture. 지정 시 원본 입력·seed도 다시 검사')
    args=parser.parse_args(argv)
    try:
        if args.verify:
            require(args.out is None and args.source_root is None,'verify 인수 혼용')
            result=verify_recovery(args.verify,args.bundle)
        else:
            require(args.out is not None,'--out 필요')
            result=recover(args.run,args.out,args.source_root,args.bundle)
        print(canonical(result).decode('utf-8'));return 0
    except (BaselineError,OSError,ValueError,TypeError,KeyError,IndexError) as e:
        print(canonical(dict(state='failed',error=type(e).__name__+': '+str(e))).decode('utf-8'),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
