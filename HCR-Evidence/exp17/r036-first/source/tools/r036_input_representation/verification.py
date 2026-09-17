"""raw 전량 독립 검산과 summary 재계산. 기존 결과를 덮어쓰지 않는다."""
from __future__ import annotations
from datetime import datetime, timezone
import traceback
from r035_frozen_selection import storage as io
from r035_frozen_selection.audit import demand, sha
from . import sources, spec
from .audit import check_transform, check_seed, check_native, check_readouts
from .reporting import summarize, render, csv_text


def verify_raw(run):
    from .protocol import validate_plan
    root=io.safe(run);plan=io.load(root/'plan.json');validate_plan(plan,check_upstream=False)
    manifest=io.load(root/'manifest.json')
    demand(set(manifest)=={'schema','state','independent_audit_pending','files'} and
        manifest['schema']=='hcr-exp17-raw-manifest-v1' and manifest['state']=='raw_complete' and
        manifest['independent_audit_pending'] is True,'EXP-17 incomplete raw manifest')
    all_sources=plan['dependency_source_hashes']|plan['addon_source_hashes']
    expected={'plan.json','environment.json','attempts.jsonl'}
    expected|={'source/'+n for n in all_sources}
    expected|={'upstream/'+n for n in sources.UPSTREAM_FILES}
    expected|={'raw/'+t['id']+'.json' for t in plan['trials']}
    demand(set(manifest['files'])==expected,'raw population/inventory')
    actual={n for n in io.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    demand(actual==expected|{'manifest.json'},'raw 파일 누락 또는 미등록 파일')
    for name,h in manifest['files'].items():demand(io.file_hash(io.child(root,name))==h,'raw checksum: '+name)
    for name,h in all_sources.items():demand(io.text_hash(io.child(root,'source/'+name))==h,'source snapshot: '+name)
    for name,h in plan['upstream_file_hashes'].items():demand(io.file_hash(io.child(root,'upstream/'+name))==h,'upstream copy: '+name)
    old_manifest=io.load(root/'upstream/manifest.json')
    demand(old_manifest['schema']=='hcr-exp15-raw-manifest-v1' and old_manifest['state']=='raw_complete','upstream raw state')
    for n in ('plan.json','seed/6.json','training.json'):
        demand(old_manifest['files'][n]==plan['upstream_file_hashes'][n],'EXP-15 upstream binding')
    seed,old,seed_audit=check_seed(root,plan)
    cases={c['name']:c for c in old['conditions']['cases']}
    # 원 입력 population은 실행 결과가 아닌 과거 동결 계획에서 검산한다.
    wanted=[dict(name=c['name'],family=c['family'],observation=c['observation']) for c in old['conditions']['cases']]
    demand(wanted==plan['cases'],'결과에 따라 입력 population 변경')
    logs=[io.loads(line) for line in io.read(root/'attempts.jsonl').decode('utf-8').splitlines()]
    pos=0;rows=[];reports={};records={}
    def take(expected_row):
        nonlocal pos
        demand(pos<len(logs) and sha(logs[pos])==sha(expected_row),'first-attempt stream 불일치 at '+str(pos));pos+=1
    for trial in plan['trials']:
        tid=trial['id'];raw=io.load(root/'raw'/f'{tid}.json')
        demand(set(raw)=={'schema','trial','transformed','memory_sha256','native','readouts'} and
            raw['schema']=='hcr-exp17-trial-v1' and raw['trial']==trial,'trial schema/identity')
        demand(raw['memory_sha256']==plan['memory_sha256'],'trial memory binding')
        case=cases[trial['case']]
        obs=check_transform(case['observation'],raw['transformed'],trial['variant'])
        native_report,views,actions=check_native(raw['native'],obs,seed,trial['scope'],plan['conditions'])
        selected_rows,selected_audits=check_readouts(raw,views,case)
        for out in raw['readouts']:
            demand(all(x['limits']==plan['conditions']['selection_limits'] for x in out['results'].values()),'선택 예산 변조')
        take(dict(event='trial_started',trial_id=tid))
        take(dict(event='input_prepared',trial_id=tid,input_sha256=sha(obs)))
        for row in actions:take(dict(event='native_action',trial_id=tid,record=row))
        take(dict(event='native_completed',trial_id=tid,native_sha256=sha(raw['native'])))
        for i,(view,output) in enumerate(zip(views,raw['readouts'])):
            for policy in spec.POLICIES:
                take(dict(event='selection_started',trial_id=tid,ordinal=i,policy=policy,input_sha256=sha(view)))
                take(dict(event='selection_completed',trial_id=tid,ordinal=i,policy=policy,result_sha256=sha(output['results'][policy])))
        take(dict(event='trial_completed',trial_id=tid,raw_sha256=sha(raw)))
        rows.extend(selected_rows);reports[tid]=native_report
        records[tid]=dict(raw_sha256=sha(raw),native_audit=native_report,selection_audits=selected_audits,rows=selected_rows)
    demand(pos==len(logs),'미등록 tail action')
    summary=summarize(rows,reports,plan['trials'],seed_audit)
    audit=dict(schema='hcr-exp17-audit-v1',verified=True,raw_manifest_sha256=io.file_hash(root/'manifest.json'),
        native_trials=len(reports),native_readouts=len(rows),streamed_actions=len(logs),
        native_sessions_independently_replayed=True,seed_training_independently_replayed=True,
        input_transforms_independently_checked=True,first_decisions_preserved=True,
        selectors_compared_on_same_native_state=True,proof_DAGs_independently_checked=True,
        correctness_or_invariance_required=False)
    return summary,audit,records


def write_analysis(run,*,check_only=False):
    root=io.safe(run)
    try:
        summary,audit,records=verify_raw(root);target=root/'analysis'
        contents={'summary.json':summary,'audit.json':audit}|{'records/'+k+'.json':v for k,v in records.items()}
        texts={'summary.ko.md':render(summary),'conditions.csv':csv_text(summary['rows'])}
        if check_only:
            manifest=io.load(target/'manifest.json')
            demand(manifest['schema']=='hcr-exp17-analysis-manifest-v1' and
                manifest['raw_manifest_sha256']==audit['raw_manifest_sha256'],'analysis 출처')
            demand(io.inventory(target)==set(contents)|set(texts)|{'manifest.json'} and
                   set(manifest['files'])==set(contents)|set(texts),'analysis inventory')
            for n,v in contents.items():demand(io.load(io.child(target,n))==v,'독립 재계산 불일치: '+n)
            for n,v in texts.items():demand(io.read(io.child(target,n)).decode('utf-8')==v,'보고서 불일치: '+n)
            for n,h in manifest['files'].items():demand(io.file_hash(io.child(target,n))==h,'analysis checksum: '+n)
        else:
            target.mkdir(parents=True,exist_ok=False)
            for n,v in contents.items():io.put(io.child(target,n),v)
            for n,v in texts.items():io.put_bytes(io.child(target,n),v.encode('utf-8'))
            names=io.inventory(target)
            io.put(target/'manifest.json',dict(schema='hcr-exp17-analysis-manifest-v1',raw_manifest_sha256=audit['raw_manifest_sha256'],
                files={n:io.file_hash(target/n) for n in sorted(names)}))
        return audit
    except BaseException as exc:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        io.put(root/'audit_failures'/f'{stamp}.json',dict(status='audit_failure',error_type=type(exc).__name__,
            error=str(exc),traceback=traceback.format_exc(),automatic_retry=False))
        raise
