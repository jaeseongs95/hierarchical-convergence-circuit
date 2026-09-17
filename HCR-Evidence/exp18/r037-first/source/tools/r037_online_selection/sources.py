"""b6b57589의 native/R035/R036 소스와 EXP-17 출처를 고정한다."""
from __future__ import annotations
from copy import deepcopy
import hashlib
from pathlib import Path
from . import io, spec
from .contracts import require, digest, validate_public_observation

UPSTREAM_FILES = ('manifest.json', 'plan.json', 'seed/6.json', 'training.json')
PARENT_FILES = ('manifest.json', 'plan.json') + tuple('upstream/'+n for n in UPSTREAM_FILES)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def dependencies() -> dict:
    root = repo_root(); manifest_bytes = io.read(root/'R036_MANIFEST.json').replace(b'\r\n', b'\n')
    git_hash = hashlib.sha1(b'blob '+str(len(manifest_bytes)).encode('ascii')+b'\0'+manifest_bytes).hexdigest()
    require(git_hash == spec.R036_MANIFEST_BLOB, 'b6b57589 R036 manifest 기준선과 다릅니다.')
    manifest = io.loads(manifest_bytes.decode('utf-8'))
    for name, expected in manifest['files'].items():
        require(io.text_hash(io.child(root, name)) == expected, 'R036 소스 변경: '+name)
    from r036_input_representation.sources import check_dependencies
    registry = check_dependencies(root)
    return registry['files'] | manifest['files'] | {'R036_MANIFEST.json': io.text_hash(root/'R036_MANIFEST.json')}


def code_hashes() -> dict:
    root = repo_root()
    names = {p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}
    names |= {'Run-HCR-R037.py', 'scripts/r037_cli.py', 'scripts/verify_r037.py', 'R037_MANIFEST.json'}
    return {name: io.text_hash(io.child(root, name)) for name in sorted(names)}


def read_parent(source_run) -> tuple:
    root = io.safe(source_run); manifest = io.load(root/'manifest.json'); plan = io.load(root/'plan.json')
    require(manifest['schema'] == 'hcr-exp17-raw-manifest-v1' and manifest['state'] == 'raw_complete',
            'EXP-17 raw 완료 폴더가 필요합니다.')
    require(plan['schema'] == 'hcr-exp17-plan-v1', 'EXP-17 plan schema')
    for name in PARENT_FILES[1:]:
        require(io.file_hash(io.child(root, name)) == manifest['files'][name], 'EXP-17 출처 checksum: '+name)
    previous = io.load(root/'upstream/plan.json')
    old_manifest = io.load(root/'upstream/manifest.json')
    require(old_manifest['schema'] == 'hcr-exp15-raw-manifest-v1' and old_manifest['state'] == 'raw_complete',
            'EXP-15 원 학습 출처')
    require(previous['schema'] == 'hcr-exp15-plan-v1' and previous['conditions']['training_count'] == 6,
            'EXP-15 학습 조건')
    for name in UPSTREAM_FILES[1:]:
        require(io.file_hash(root/'upstream'/name) == old_manifest['files'][name], 'EXP-15 원자료 checksum: '+name)
    seed = io.load(root/'upstream/seed/6.json')
    require(seed['sha256'] == digest(seed['document']), '동결 seed packet checksum')
    cases = [dict(name=c['name'], family=c['family'], observation=deepcopy(c['observation']))
             for c in previous['conditions']['cases']]
    require(cases == plan['cases'] and tuple(c['name'] for c in cases) == spec.CASE_NAMES,
            '기존 8개 입력 population/order 변경')
    for case in cases:
        validate_public_observation(case['observation'])
    native = {n: h for n, h in dependencies().items() if n.startswith('src/hcr/')}
    require(previous['source_hashes'] == native and
            {n:h for n,h in plan['dependency_source_hashes'].items() if n.startswith('src/hcr/')} == native,
            'seed/EXP-17/native 소스 기준선 불일치')
    core = seed['document']['engine']
    require(digest(core['memory']) == plan['memory_sha256'] and digest(core['config']) == plan['config_sha256'],
            'EXP-17 memory/config 출처')
    hashes = {n: io.file_hash(io.child(root, n)) for n in PARENT_FILES}
    return root, cases, core, hashes
