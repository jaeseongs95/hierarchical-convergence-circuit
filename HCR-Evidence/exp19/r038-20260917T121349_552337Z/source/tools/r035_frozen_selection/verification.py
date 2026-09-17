"""별도 프로세스의 EXP-16 전량 검산/보고. 원 EXP-15 소스·raw도 다시 확인한다."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import traceback
from . import storage as io, spec, upstream
from .audit import AuditError, demand, sha, check_transform, audit_result, reachable
from .reporting import summarize, render, csv_text


def independent_sources(root, plan, source_run):
    """생산 projector/인구 선택기를 호출하지 않고 선정/투영을 독립 확인한다."""
    from hcr.evaluation.selection_spec import cells as old_cells
    from hcr.evaluation.selection_audit import source_view
    original = io.safe(source_run or plan['source_run'])
    demand(io.file_hash(original/'manifest.json') == plan['upstream_manifest_sha256'], 'EXP-15 manifest 변경')
    demand(io.file_hash(original/'plan.json') == plan['upstream_plan_sha256'], 'EXP-15 plan 변경')
    old_plan = io.load(root/'upstream/plan.json'); manifest = io.load(root/'upstream/manifest.json')
    demand(io.read(root/'upstream/plan.json') == io.read(original/'plan.json')
        and io.read(root/'upstream/manifest.json') == io.read(original/'manifest.json'), 'upstream 복사본 변경')
    native_audit = upstream.full_native_audit(original)
    demand(native_audit['verified'] is True, 'EXP-15 independent native audit')
    cond = old_plan['conditions']; cases = {c['name']:c for c in cond['cases']}
    wanted = [c for c in old_cells(cond) if c['group'] == 'main' and c['arm'] == 'expand_only'
              and c['world'] == sorted(cases[c['case']]['worlds'])[0]]
    wanted.sort(key=lambda c:(c['case'],c['scope']))
    demand(len(wanted) == len(cases)*len(cond['scopes']), 'source population coverage')
    checked = []; upstream_files = {'upstream/plan.json','upstream/manifest.json'}
    for cell in wanted:
        name = 'raw/'+cell['id']+'.json'; bname = 'baselines/'+cell['baseline_key']+'.json'
        for n in (name,bname):
            demand(io.file_hash(io.child(root,'upstream/'+n)) == manifest['files'][n], 'upstream copied raw checksum: '+n)
            upstream_files.add('upstream/'+n)
        raw = io.load(io.child(root,'upstream/'+name)); base = io.load(io.child(root,'upstream/'+bname))
        demand(raw['cell'] == cell and raw['result']['candidates'][0] == base['first'], 'source cell/initial native preservation')
        for ordinal,candidate in enumerate(raw['result']['candidates']):
            sid = 'n%04d' % len(checked); saved = io.load(root/'snapshots'/f'{sid}.json')
            v = source_view(candidate)
            v = {k:deepcopy(v[k]) for k in ('observation','raw_value','state','completed_paths','graph_complete','original_proof','min_abs_score')} | {'schema':'hcr-frozen-proof-view-r035-v1'}
            expected = dict(id=sid,source_file=name,baseline_path=bname,candidate_ordinal=ordinal,
                candidate_id=candidate['candidate_id'],candidate_sha256=sha(candidate),case=cell['case'],scope=cell['scope'],
                baseline_key=cell['baseline_key'],phase='first' if ordinal==0 else f'expanded_{ordinal}',
                native_readout=candidate['readout'],input=v,source_kernel_ticks=candidate['decision']['cost']['kernel_ticks'])
            demand(saved == expected, 'source candidate snapshot binding: '+sid)
            checked.append(saved)
    expected_meta = [{k:deepcopy(v) for k,v in s.items() if k not in ('input','native_readout')} |
                     {'input_sha256':sha(s['input'])} for s in checked]
    demand(plan['snapshots'] == expected_meta, 'frozen source population differs')
    return checked, cases, native_audit, upstream_files


def verify_raw(run, source_run=None):
    root = io.safe(run); plan = io.load(root/'plan.json'); manifest = io.load(root/'manifest.json')
    # 조건·도구 소스와 native 소스의 현재 기준선만 공유 검사한다. 실행 정책은 공유하지 않는다.
    from .protocol import validate_plan
    source = validate_plan(plan,source_run)
    demand(set(manifest) == {'schema','state','independent_audit_pending','files'}
        and manifest['schema']=='hcr-exp16-raw-manifest-v1' and manifest['state']=='raw_complete'
        and manifest['independent_audit_pending'] is True, 'EXP-16 raw incomplete')
    inventory = {n for n in io.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    demand(inventory == set(manifest['files'])|{'manifest.json'}, 'raw 파일 누락/미등록 파일')
    for name,h in manifest['files'].items(): demand(io.file_hash(io.child(root,name))==h,'raw checksum: '+name)
    for name,h in plan['addon_source_hashes'].items(): demand(io.text_hash(io.child(root,'source/'+name))==h,'EXP-16 source snapshot: '+name)
    saved,cases,native_audit,upfiles = independent_sources(root,plan,source)
    byid={s['id']:s for s in saved}; cells=spec.cells(list(byid))
    expected={'plan.json','environment.json','attempts.jsonl'}|upfiles
    expected|={'source/'+n for n in plan['addon_source_hashes']}
    expected|={'snapshots/'+sid+'.json' for sid in byid}
    expected|={'raw/'+c['id']+'.json' for c in cells}
    demand(set(manifest['files'])==expected,'EXP-16 matrix/file inventory')
    logs=[io.loads(line) for line in io.read(root/'attempts.jsonl').decode('utf-8').splitlines()]
    demand(len(logs)==2*len(cells),'first-attempt log count')
    rows=[];records={}
    for i,cell in enumerate(cells):
        raw=io.load(root/'raw'/f"{cell['id']}.json"); s=byid[cell['snapshot_id']]
        demand(set(raw)=={'cell','snapshot_sha256','transformed','result'} and raw['cell']==cell,'cell contract')
        demand(raw['snapshot_sha256']==sha(s),'paired snapshot hash')
        demand(raw['transformed']['variant']==cell['variant'],'transformation matrix')
        inp=check_transform(s['input'],raw['transformed']); out=raw['result']
        demand(out['policy']==cell['policy'] and out['limits']==cell['limits'],'policy/budget matrix')
        a=audit_result(inp,out)
        if cell['variant']['id']=='v0000' and cell['group']=='main':
            if cell['policy']=='native_saved':
                demand(out['value'] is s['native_readout']['value'] and out['accepted'] is s['native_readout']['accepted'],
                       'native dependency_gate와 EXP-16 공통 gate 불일치')
            if cell['policy']=='native_rebuild':
                demand(out['proof']==s['input']['original_proof'], 'identity native rebuild/source proof 불일치')
        demand(logs[2*i]==dict(event='attempt_started',cell_id=cell['id'],snapshot_id=s['id'],snapshot_sha256=sha(s)), 'attempt-start provenance')
        demand(logs[2*i+1]==dict(event='attempt_completed',cell_id=cell['id'],raw_sha256=sha(raw)), 'attempt-finish provenance')
        world_results={}
        for name,world in cases[s['case']]['worlds'].items():
            truth=reachable(s['input']['observation'],world)
            world_results[name]=dict(expected=truth,external_correct=None if out['value'] is None else out['value'] is truth)
        pi=out['selected_path_index']; source_route=None
        if pi is not None:
            old_pi=raw['transformed']['maps']['path_new_to_old'][pi]
            source_route=[s['input']['observation']['edges'][slot]['id'] for slot in s['input']['completed_paths'][old_pi]]
        row=dict(id=cell['id'],snapshot_id=s['id'],case=s['case'],scope=s['scope'],phase=s['phase'],
            variant=cell['variant']['id'],policy=cell['policy'],group=cell['group'],raw_value=s['input']['raw_value'],
            value=out['value'],accepted=out['accepted'],applicable=out['applicable'],D_DAG=a['D_DAG'],
            source_route=source_route,reason=out['reason'],usage=out['usage'],world_results=world_results)
        rows.append(row);records[cell['id']]=dict(raw_sha256=sha(raw),audit=a,assessment=row)
    summary=summarize(rows,saved,native_audit,plan['upstream_manifest_sha256'])
    audit=dict(schema='hcr-exp16-audit-v1',verified=True,raw_manifest_sha256=io.file_hash(root/'manifest.json'),
        source_native_reaudited=True,snapshots=len(saved),conditions=len(cells),streamed_actions=len(logs),
        original_proof_preserved=True,proof_DAGs_independently_checked=True,transforms_independently_checked=True,
        identity_native_rebuild_parity_checked=True,final_correctness_not_required=True)
    return summary,audit,records


def write_analysis(run,source_run=None,*,check_only=False):
    root=io.safe(run)
    try:
        summary,audit,records=verify_raw(root,source_run)
        target=root/'analysis'; contents={'summary.json':summary,'audit.json':audit}
        contents.update({'records/'+k+'.json':v for k,v in records.items()})
        texts={'summary.ko.md':render(summary),'conditions.csv':csv_text(summary['rows'])}
        if check_only:
            am=io.load(target/'manifest.json')
            demand(am['schema']=='hcr-exp16-analysis-manifest-v1' and am['raw_manifest_sha256']==audit['raw_manifest_sha256'],'analysis source')
            demand(io.inventory(target)==set(contents)|set(texts)|{'manifest.json'},'analysis inventory')
            demand(set(am['files'])==set(contents)|set(texts),'analysis manifest inventory')
            for n,v in contents.items(): demand(io.load(io.child(target,n))==v,'analysis independent recomputation: '+n)
            for n,v in texts.items(): demand(io.read(io.child(target,n)).decode('utf-8')==v,'analysis text differs: '+n)
            for n,h in am['files'].items(): demand(io.file_hash(io.child(target,n))==h,'analysis checksum: '+n)
        else:
            target.mkdir(parents=True,exist_ok=False)
            for n,v in contents.items(): io.put(io.child(target,n),v)
            for n,v in texts.items(): io.put_bytes(io.child(target,n),v.encode('utf-8'))
            names=io.inventory(target)
            io.put(target/'manifest.json',dict(schema='hcr-exp16-analysis-manifest-v1',raw_manifest_sha256=audit['raw_manifest_sha256'],
                files={n:io.file_hash(io.child(target,n)) for n in sorted(names)}))
        return audit
    except BaseException as exc:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        io.put(root/'audit_failures'/f'{stamp}.json',dict(status='evaluator_disagreement' if isinstance(exc,AuditError) else 'audit_runtime_or_contract_failure',
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),check_only=check_only,automatic_retry=False))
        raise
