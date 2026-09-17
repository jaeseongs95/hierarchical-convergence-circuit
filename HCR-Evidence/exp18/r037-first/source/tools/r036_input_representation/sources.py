"""기준 소스·동결 memory provenance. Git/원 evidence에 쓰지 않는다."""
from __future__ import annotations
from pathlib import Path
from r035_frozen_selection import storage as io
from r035_frozen_selection.contracts import require, digest
from .spec import BASE_COMMIT

UPSTREAM_FILES=('manifest.json','plan.json','seed/6.json','training.json')


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def check_dependencies(root=None) -> dict:
    root=io.safe(root or repo_root()); registry=io.load(Path(__file__).with_name('dependencies.json'))
    require(registry['schema']=='hcr-r036-dependencies-v1' and registry['basis_commit']==BASE_COMMIT,'R036 dependency registry')
    native={n for n in registry['files'] if n.startswith('src/hcr/')}
    actual={p.relative_to(root).as_posix() for p in (root/'src/hcr').rglob('*.py')}
    require(actual==native,'native 파일 집합이 기준선과 다릅니다.')
    for name,h in registry['files'].items():
        require(io.text_hash(io.child(root,name))==h,'기존 소스 변경: '+name)
    return registry


def code_hashes() -> dict:
    root=repo_root(); names={p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}
    names |= {'tools/r036_input_representation/dependencies.json','Run-HCR-R036.py',
              'scripts/r036_cli.py','scripts/verify_r036.py','R036_MANIFEST.json'}
    return {n:io.text_hash(io.child(root,n)) for n in sorted(names)}


def read_source(source_run) -> tuple:
    root=io.safe(source_run); m=io.load(root/'manifest.json'); p=io.load(root/'plan.json')
    require(m['schema']=='hcr-exp15-raw-manifest-v1' and m['state']=='raw_complete','EXP-15 raw 상태')
    require(p['schema']=='hcr-exp15-plan-v1' and p['conditions']['training_count']==6,'EXP-15 조건/학습량')
    require(p['conditions']['scopes']==['legacy','route_only'],'EXP-15 prior 조건')
    require(p['conditions']['protocol']=='exp15-r034-proof-selection-v1','EXP-15 protocol')
    for name in UPSTREAM_FILES[1:]:
        require(io.file_hash(io.child(root,name))==m['files'][name],'EXP-15 원자료 checksum: '+name)
    seed=io.load(root/'seed/6.json')
    require(seed['sha256']==digest(seed['document']), 'seed checksum')
    return root,m,p,seed


def source_hashes(source_run) -> dict:
    root=io.safe(source_run)
    return {n:io.file_hash(io.child(root,n)) for n in UPSTREAM_FILES}
