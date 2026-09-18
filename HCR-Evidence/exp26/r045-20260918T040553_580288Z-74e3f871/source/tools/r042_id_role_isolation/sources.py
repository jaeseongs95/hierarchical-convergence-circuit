"""EXP22의 필요한 원자료만 고정 capsule로 보존한다. 이전 raw/analysis는 수정하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from . import storage as io
from .contracts import BASE_COMMIT, R041_MANIFEST_BLOB, PARENT_RAW_SHA256, require, digest

PARENT_FIXED_FILES = ('manifest.json', 'plan.json', 'analysis/manifest.json', 'analysis/audit.json',
    'upstream/plan.json', 'upstream/seed/6.json', 'upstream/training.json')


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def merge_hashes(*inventories: dict) -> dict:
    merged = {}
    for inventory in inventories:
        for name, value in inventory.items():
            require(name not in merged or merged[name] == value, '의존 source hash 충돌: ' + name)
            merged[name] = value
    return merged


def dependencies() -> dict:
    from r038_early_adoption.sources import check_manifest
    from r041_scheduler_direction import sources as previous
    check_manifest(repo_root(), 'R041_MANIFEST.json', R041_MANIFEST_BLOB)
    return merge_hashes(previous.dependencies(), previous.addon_hashes())


def addon_hashes() -> dict:
    root = repo_root()
    manifest = io.load(root/'R042_MANIFEST.json')
    require(set(manifest) == {'schema','basis_commit','files'} and
            manifest['schema'] == 'hcr-r042-additive-release-v1' and manifest['basis_commit'] == BASE_COMMIT,
            'R042 release schema/basis')
    inventory = manifest['files']
    require(type(inventory) is dict and inventory, 'R042 release inventory')
    for name, value in inventory.items():
        require(io.text_hash(io.child(root, name)) == value, 'R042 release 파일 변경: ' + name)
    actual = {p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}
    listed = {n for n in inventory if n.startswith('tools/r042_id_role_isolation/') and n.endswith('.py')}
    require(actual == listed, '미등록/누락 R042 Python source')
    return merge_hashes(inventory, {'R042_MANIFEST.json':io.text_hash(root/'R042_MANIFEST.json')})


def parent_regression_trials(plan: dict) -> list[dict]:
    require(plan['schema'] == 'hcr-exp22-plan-v1' and len(plan['trials']) == 108, 'EXP22 plan population')
    selected = [trial for trial in plan['trials'] if trial['scope'] == 'legacy' and
                trial['arm'] == 'online_support' and trial['scheduler'] in ('edge_id_min','edge_id_max')]
    cells = {(t['case'],t['scheduler']) for t in selected}
    expected = {('order_'+o,s) for o in ('SMD','SDM','MSD','MDS','DSM','DMS')
                for s in ('edge_id_min','edge_id_max')}
    require(len(selected) == 12 and cells == expected and len({t['id'] for t in selected}) == 12,
            'EXP22 동일 입력 회귀 12조건 누락/중복')
    for trial in selected:
        require(type(trial['id']) is str and trial['id'].startswith('t') and
                len(trial['id']) == 5 and trial['id'][1:].isdigit(), 'parent trial ID')
    return selected


def parent_files(plan: dict) -> tuple[str, ...]:
    return PARENT_FIXED_FILES + tuple('raw/'+t['id']+'.json' for t in parent_regression_trials(plan))


def capsule_name(name: str) -> str:
    return name if name.startswith('upstream/') else 'basis/exp22/'+name


def validate_parent_documents(documents: dict, hashes: dict):
    from r041_scheduler_direction.protocol import validate_plan as validate_exp22
    plan = documents['plan.json']; names = set(parent_files(plan))
    require(set(documents) == set(hashes) == names, 'EXP22 capsule inventory')
    require(hashes['manifest.json'] == PARENT_RAW_SHA256, '지정된 EXP22 raw manifest와 다릅니다.')
    manifest = documents['manifest.json']
    require(manifest['schema'] == 'hcr-exp22-raw-manifest-v1' and manifest['state'] == 'raw_complete', 'EXP22 raw 미완료')
    validate_exp22(plan, check_parent=False)
    for name in names - {'manifest.json','analysis/manifest.json','analysis/audit.json'}:
        require(manifest['files'][name] == hashes[name], 'EXP22 capsule checksum: '+name)
    analysis, audit = documents['analysis/manifest.json'], documents['analysis/audit.json']
    require(analysis['schema'] == 'hcr-exp22-analysis-manifest-v1' and
            analysis['raw_manifest_sha256'] == PARENT_RAW_SHA256 and
            analysis['files']['audit.json'] == hashes['analysis/audit.json'], 'EXP22 analysis lineage')
    require(audit['schema'] == 'hcr-exp22-audit-v1' and audit['verified'] is True and
            audit['native_trials'] == 108 and audit['raw_manifest_sha256'] == PARENT_RAW_SHA256,
            'EXP22 저장된 audit 상태/계보')
    packet = documents['upstream/seed/6.json']
    require(packet['sha256'] == digest(packet['document']), 'seed packet seal')
    seed = packet['document']['engine']
    require(digest(seed['memory']) == plan['memory_sha256'] and digest(seed['config']) == plan['config_sha256'],
            'EXP22 동결 학습 seed 불일치')
    for trial in parent_regression_trials(plan):
        raw = documents['raw/'+trial['id']+'.json']
        require(set(raw) == {'schema','trial','run'} and raw['schema'] == 'hcr-exp22-raw-trial-v1' and
                raw['trial'] == trial, 'EXP22 raw binding')
    return deepcopy(plan), deepcopy(seed)


def read_parent(path):
    root = io.safe(path)
    require(io.file_hash(root/'manifest.json') == PARENT_RAW_SHA256, 'EXP22 manifest checksum')
    plan = io.load(root/'plan.json')
    names = parent_files(plan)
    hashes, documents = {}, {}
    for name in names:
        data = io.read(io.child(root,name))
        hashes[name] = io.bytes_hash(data)
        documents[name] = io.loads(data)
    parent, seed = validate_parent_documents(documents, hashes)
    return root, parent, seed, hashes, documents
