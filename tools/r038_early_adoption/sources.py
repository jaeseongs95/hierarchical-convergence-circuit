"""EXP-18 입력·학습 출처와 d25f4bd 기준선을 동결한다. 이전 결과는 수정하지 않는다."""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path
from r037_online_selection import io
from . import spec
from .contracts import digest, require

PARENT_FILES = ('manifest.json','plan.json','analysis/manifest.json','analysis/audit.json',
                'upstream/manifest.json','upstream/plan.json','upstream/seed/6.json','upstream/training.json')


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def capsule_name(name: str) -> str:
    return name if name.startswith('upstream/') else 'basis/exp18/' + name


def check_manifest(root: Path, filename: str, expected_blob: str | None = None) -> dict:
    data = io.read(root/filename).replace(b'\r\n', b'\n')
    if expected_blob is not None:
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
        require(actual == expected_blob, filename + '의 기준 Git blob 불일치')
    document = io.loads(data.decode('utf-8'))
    require(isinstance(document['files'], dict) and document['files'], 'release inventory')
    for name, h in document['files'].items():
        require(io.text_hash(io.child(root, name)) == h, '동결 release 파일 변경: ' + name)
    return document


def dependencies() -> dict:
    from r037_online_selection.sources import dependencies as old_dependencies, code_hashes as old_code
    root = repo_root()
    manifest = check_manifest(root, 'R037_MANIFEST.json', spec.R037_MANIFEST_BLOB)
    return old_dependencies() | manifest['files'] | old_code()


def addon_hashes() -> dict:
    root = repo_root()
    manifest = check_manifest(root, 'R038_MANIFEST.json')
    require(manifest['schema'] == 'hcr-r038-additive-release-v1' and
            manifest['basis_commit'] == spec.BASE_COMMIT, 'R038 release schema/basis')
    require({p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')} <= set(manifest['files']),
            'R038 manifest에 등록되지 않은 소스')
    return manifest['files'] | {'R038_MANIFEST.json':io.text_hash(root/'R038_MANIFEST.json')}


def validate_parent_documents(documents: dict, hashes: dict) -> tuple[list[dict], dict]:
    from r037_online_selection.protocol import validate_plan as old_validate
    require(set(documents) == set(PARENT_FILES) and set(hashes) == set(PARENT_FILES), 'EXP18 출처 inventory')
    manifest, plan = documents['manifest.json'], documents['plan.json']
    require(manifest['schema'] == 'hcr-exp18-raw-manifest-v1' and manifest['state'] == 'raw_complete',
            '완료된 EXP18 raw 폴더가 필요합니다.')
    old_validate(plan, check_parent=False)
    for name in ('plan.json','upstream/manifest.json','upstream/plan.json','upstream/seed/6.json','upstream/training.json'):
        require(manifest['files'][name] == hashes[name], 'EXP18 raw 입력 checksum: ' + name)
    am = documents['analysis/manifest.json']; au = documents['analysis/audit.json']
    require(am['schema'] == 'hcr-exp18-analysis-manifest-v1' and
            am['raw_manifest_sha256'] == hashes['manifest.json'] and
            am['files']['audit.json'] == hashes['analysis/audit.json'], 'EXP18 audit 계보')
    require(au['verified'] is True and au['native_trials'] == 32 and
            au['raw_manifest_sha256'] == hashes['manifest.json'], 'EXP18 저장 audit 상태/출처')
    upstream = documents['upstream/manifest.json']
    for name in ('plan.json','seed/6.json','training.json'):
        require(upstream['files'][name] == hashes['upstream/'+name], '원 학습 raw checksum: '+name)
    old = documents['upstream/plan.json']['conditions']['cases']
    public = [{k:deepcopy(c[k]) for k in ('name','family','observation')} for c in old]
    require(public == plan['cases'], '원 8개 case가 EXP18 공개 입력과 다릅니다.')
    packet = documents['upstream/seed/6.json']
    require(packet['sha256'] == digest(packet['document']), 'seed packet seal')
    core = packet['document']['engine']
    require(digest(core['memory']) == plan['memory_sha256'] and digest(core['config']) == plan['config_sha256'],
            '원 memory/config와 EXP18 출처 불일치')
    return spec.cases_from_parent(old), deepcopy(core)


def read_parent(path) -> tuple:
    root = io.safe(path)
    hashes = {n:io.file_hash(io.child(root,n)) for n in PARENT_FILES}
    documents = {n:io.load(io.child(root,n)) for n in PARENT_FILES}
    cases, core = validate_parent_documents(documents, hashes)
    return root, cases, core, hashes
