"""8713f17 코드와 지정 EXP19 raw manifest를 고정한다. 이전 evidence는 읽기 전용이다."""
from copy import deepcopy
from pathlib import Path
from r037_online_selection import io
from r038_early_adoption import sources as previous
from . import spec, input_audit
from .contracts import (BASE_COMMIT, R038_MANIFEST_BLOB, PARENT_RAW_SHA256,
    CANONICAL_CASE, require, digest)
PARENT_FILES = ('manifest.json','plan.json','analysis/manifest.json','analysis/audit.json') + tuple(
    name if name.startswith('upstream/') else 'basis/exp18/'+name for name in previous.PARENT_FILES)


def repo_root(): return Path(__file__).resolve().parents[2]


def capsule_name(name):
    return name if name.startswith('upstream/') else 'basis/exp19/'+name


def dependencies():
    root=repo_root()
    previous.check_manifest(root,'R038_MANIFEST.json',R038_MANIFEST_BLOB)
    return previous.dependencies() | previous.addon_hashes()


def addon_hashes():
    root=repo_root();m=previous.check_manifest(root,'R039_MANIFEST.json')
    require(m['schema']=='hcr-r039-additive-release-v1' and m['basis_commit']==BASE_COMMIT,'R039 manifest schema/basis')
    require({p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}<=set(m['files']),
        '등록되지 않은 R039 Python source')
    return m['files'] | {'R039_MANIFEST.json':io.text_hash(root/'R039_MANIFEST.json')}


def validate_parent_documents(documents, hashes):
    from r038_early_adoption.protocol import validate_plan as previous_validate
    require(set(documents)==set(hashes)==set(PARENT_FILES),'EXP19 capsule inventory')
    require(hashes['manifest.json']==PARENT_RAW_SHA256,'지정 EXP19 원자료 manifest와 다릅니다.')
    raw,plan=documents['manifest.json'],documents['plan.json']
    require(raw['schema']=='hcr-exp19-raw-manifest-v1' and raw['state']=='raw_complete','완료 EXP19 raw 필요')
    previous_validate(plan,check_parent=False)
    for name in PARENT_FILES:
        if name not in ('manifest.json','analysis/manifest.json','analysis/audit.json'):
            require(raw['files'][name]==hashes[name],'EXP19 입력 checksum: '+name)
    am,au=documents['analysis/manifest.json'],documents['analysis/audit.json']
    require(am['schema']=='hcr-exp19-analysis-manifest-v1' and
        am['raw_manifest_sha256']==hashes['manifest.json'] and
        am['files']['audit.json']==hashes['analysis/audit.json'],'EXP19 분석 출처')
    require(au['verified'] is True and au['native_trials']==84 and
        au['raw_manifest_sha256']==hashes['manifest.json'],'EXP19 audit 상태/계보')
    olddocs={};oldhashes={}
    for n in previous.PARENT_FILES:
        key=n if n.startswith('upstream/') else 'basis/exp18/'+n
        olddocs[n]=documents[key];oldhashes[n]=hashes[key]
    require(oldhashes==plan['parent_file_hashes'],'EXP19의 원 EXP18 capsule hash 불일치')
    _,core=previous.validate_parent_documents(olddocs,oldhashes)
    wanted=[c for c in plan['cases'] if c['name']==CANONICAL_CASE]
    require(len(wanted)==1,'canonical parent case 누락/중복')
    base=deepcopy(wanted[0]);base['worlds']=deepcopy(plan['evaluation_worlds'][CANONICAL_CASE])
    input_audit.check_canonical(base)
    require(digest(core['memory'])==plan['memory_sha256'] and digest(core['config'])==plan['config_sha256'],
        'EXP19 memory/config 불일치')
    return spec.make_cases(base),deepcopy(core),base


def read_parent(path):
    root=io.safe(path)
    hashes={n:io.file_hash(io.child(root,n)) for n in PARENT_FILES}
    docs={n:io.load(io.child(root,n)) for n in PARENT_FILES}
    cases,core,base=validate_parent_documents(docs,hashes)
    return root,cases,core,hashes,base
