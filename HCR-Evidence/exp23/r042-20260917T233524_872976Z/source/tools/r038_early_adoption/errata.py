"""선택 사항: EXP18 원문을 보존하는 가정 수 정정 sidecar. 원본을 덮어쓰지 않는다."""
from __future__ import annotations
from r037_online_selection import io
from .contracts import demand,digest
from .audit import candidate_view
from .metrics import assumption_counts


def write_errata(source_run,out) -> dict:
    from r037_online_selection.audit import verify_raw
    root,target = io.safe(source_run),io.safe(out)
    io.disjoint(root,target)
    demand(not target.exists(),'기존 정정 파일 덮어쓰기 금지')
    _,audit,records = verify_raw(root)
    rows = []
    plan = io.load(root/'plan.json')
    for trial in plan['trials']:
        raw = io.load(root/'raw'/f"{trial['id']}.json")
        for ordinal,(candidate,selection) in enumerate(zip(raw['run']['candidates'],raw['run']['selections'])):
            counts = assumption_counts(candidate_view(candidate),selection['proof'])
            old = records[trial['id']]['audit']['selections'][ordinal]['supported_assumptions']
            rows.append(dict(trial_id=trial['id'],ordinal=ordinal,raw_sha256=digest(raw),
                old_supported_assumptions=old,**counts,
                corrected=old != counts['supported_assumptions'],
                accepted_preserved=selection['accepted'],value_preserved=selection['value']))
    result = dict(schema='hcr-exp18-assumption-count-errata-r038-v1',
        source_manifest_sha256=audit['raw_manifest_sha256'],source_independently_reverified=True,
        original_files_modified=False,acceptance_algorithm_changed=False,rows=rows,
        changed_readouts=sum(r['corrected'] for r in rows))
    io.put(target,result)
    return dict(out=str(target),changed_readouts=result['changed_readouts'],original_files_modified=False)
