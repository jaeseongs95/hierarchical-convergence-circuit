"""EXP21의 조건/학습 계보 및 72개 raw를 보존한다. 이전 evidence는 수정하지 않는다."""
from copy import deepcopy
from pathlib import Path
from r037_online_selection import io
from r040_frontier_schedule import sources as previous
from r038_early_adoption.sources import check_manifest
from .contracts import BASE_COMMIT,R040_MANIFEST_BLOB,PARENT_RAW_SHA256,require,digest
from . import spec

PARENT_RAW_FILES=tuple(f'raw/t{i:04d}.json' for i in range(72))
PARENT_FILES=('manifest.json','plan.json','analysis/manifest.json','analysis/audit.json') + tuple(
    name if name.startswith('upstream/') else 'basis/exp20/'+name for name in previous.PARENT_FILES) + PARENT_RAW_FILES


def repo_root(): return Path(__file__).resolve().parents[2]

def capsule_name(name): return name if name.startswith('upstream/') else 'basis/exp21/'+name


def dependencies():
    check_manifest(repo_root(),'R040_MANIFEST.json',R040_MANIFEST_BLOB)
    return previous.dependencies() | previous.addon_hashes()


def addon_hashes():
    root=repo_root();m=check_manifest(root,'R041_MANIFEST.json')
    require(m['schema']=='hcr-r041-additive-release-v1' and m['basis_commit']==BASE_COMMIT,'R041 release schema/basis')
    require({p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}<=set(m['files']),
            '미등록 R041 source')
    return m['files'] | {'R041_MANIFEST.json':io.text_hash(root/'R041_MANIFEST.json')}


def validate_parent_documents(documents,hashes):
    from r040_frontier_schedule.protocol import validate_plan
    from r040_frontier_schedule.input_audit import check_cases,check_trial_schedule
    require(set(documents)==set(hashes)==set(PARENT_FILES),'EXP21 capsule inventory')
    require(hashes['manifest.json']==PARENT_RAW_SHA256,'동결 EXP21 raw manifest와 다릅니다.')
    raw,plan=documents['manifest.json'],documents['plan.json']
    require(raw['schema']=='hcr-exp21-raw-manifest-v1' and raw['state']=='raw_complete','EXP21 raw 완료 필요')
    validate_plan(plan,check_parent=False)
    check_cases(plan['cases'],plan['evaluation_worlds'],plan['canonical_parent_case'])
    check_trial_schedule(plan['trials'])
    for n in PARENT_FILES:
        if n not in ('manifest.json','analysis/manifest.json','analysis/audit.json'):
            require(raw['files'][n]==hashes[n],'EXP21 capsule checksum: '+n)
    am,au=documents['analysis/manifest.json'],documents['analysis/audit.json']
    require(am['schema']=='hcr-exp21-analysis-manifest-v1' and am['raw_manifest_sha256']==hashes['manifest.json']
            and am['files']['audit.json']==hashes['analysis/audit.json'],'EXP21 analysis lineage')
    require(au['verified'] is True and au['native_trials']==72 and au['fixed_identity_input_isolation_checked'] is True
            and au['raw_manifest_sha256']==hashes['manifest.json'],'EXP21 audit scope/lineage')
    olddocs={};oldhashes={}
    for n in previous.PARENT_FILES:
        key=n if n.startswith('upstream/') else 'basis/exp20/'+n
        olddocs[n]=documents[key];oldhashes[n]=hashes[key]
    require(oldhashes==plan['parent_file_hashes'],'EXP21 parent capsule lineage')
    cases,core,base=previous.validate_parent_documents(olddocs,oldhashes)
    require(spec.public_cases(cases)==plan['cases'] and {c['name']:c['worlds'] for c in cases}==plan['evaluation_worlds'],
            'EXP21 입력을 변경했습니다.')
    require(base==plan['canonical_parent_case'] and digest(core['memory'])==plan['memory_sha256']
            and digest(core['config'])==plan['config_sha256'],'EXP21 baseline/seed')
    for trial in plan['trials']:
        r=documents['raw/'+trial['id']+'.json']
        require(r['schema']=='hcr-exp21-raw-trial-v1' and r['trial']==trial,'EXP21 raw trial binding')
    return deepcopy(cases),deepcopy(core),deepcopy(base)


def read_parent(path):
    root=io.safe(path)
    hashes={n:io.file_hash(io.child(root,n)) for n in PARENT_FILES}
    docs={n:io.load(io.child(root,n)) for n in PARENT_FILES}
    cases,seed,base=validate_parent_documents(docs,hashes)
    return root,cases,seed,hashes,base
