"""Pinned source and complete parent-artifact checks. Never changes parent evidence."""
from __future__ import annotations
import hashlib
import subprocess
import sys
from pathlib import Path
from . import storage as io
from .spec import BASE_COMMIT, NATIVE_BLOBS, PARENT_PLAN_BYTES, PARENT_MANIFEST_BYTES, CONFIG


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def native_check(root):
    root = io.safe(root); report = {}
    for name, wanted in NATIVE_BLOBS.items():
        data = io.child(root, name).read_bytes().replace(b'\r\n', b'\n')
        actual = git_blob(data)
        io.require(actual == wanted, 'native baseline changed: '+name)
        report[name] = dict(git_blob=actual, text_sha256=io.sha(data))
    return report


def repository_check(root):
    root = io.safe(root)
    def git(*args):
        p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True,
                           encoding='utf-8', errors='strict', timeout=15)
        io.require(p.returncode == 0, 'git baseline check: '+p.stderr.strip())
        return p.stdout.strip()
    io.require(Path(git('rev-parse', '--show-toplevel')).resolve() == root.resolve(), 'not repository root')
    head = git('rev-parse', 'HEAD')
    git('merge-base', '--is-ancestor', BASE_COMMIT, head)
    # No fetch, checkout, git add, commit, or push. Later unrelated commits are allowed,
    # but all actually used core and frozen parent-source bytes remain pinned below.
    return dict(repository_head=head, required_ancestor=BASE_COMMIT, native=native_check(root))


def package_check(root):
    root = io.safe(root); manifest = io.load(root/'R047_MANIFEST.json')
    io.require(manifest['schema'] == 'hcr-r047-release-v1' and manifest['base_commit'] == BASE_COMMIT,
               'R047 release identity')
    for name, h in manifest['files'].items():
        io.require(io.text_hash(io.child(root, name)) == h, 'R047 source changed: '+name)
    return manifest


def check_inventory(root, expected, *, omit_prefixes=()):
    """Report all absent or altered bytes together; omissions do not count as successes."""
    root = io.safe(root); actual = set(io.inventory(root))
    missing = sorted(set(expected)-actual)
    bad = [n for n in sorted(set(expected)&actual) if io.file_hash(io.child(root,n)) != expected[n]]
    io.require(not missing and not bad, 'artifact integrity: '+str(dict(missing=missing, hash_mismatch=bad)))
    return dict(files=len(expected), missing=[], hash_mismatch=[])


def parent_files_check(parent):
    parent = io.safe(parent)
    io.require(io.file_hash(parent/'plan.json') == PARENT_PLAN_BYTES, 'parent plan is not the pinned EXP27 run')
    io.require(io.file_hash(parent/'manifest.json') == PARENT_MANIFEST_BYTES, 'parent manifest is not the pinned EXP27 run')
    plan = io.load(parent/'plan.json'); m = io.load(parent/'manifest.json')
    io.require(m['schema'] == 'hcr-exp27-raw-manifest-v1' and m['state'] == 'raw_complete', 'incomplete parent raw')
    io.require(plan['kernel_config'] == CONFIG, 'parent kernel config drift')
    check_inventory(parent,m['files'])
    actual = {n for n in io.inventory(parent) if not n.startswith(('analysis/', 'audit_failures/'))}
    io.require(actual == set(m['files'])|{'manifest.json'}, 'parent raw inventory contains missing/extra entries')
    for name,h in plan['source_hashes'].items():
        io.require(io.text_hash(io.child(parent,'source/'+name)) == h, 'parent source snapshot changed: '+name)
    for name,h in plan['parent_hashes'].items():
        io.require(io.file_hash(io.child(parent,'basis/exp26/'+name)) == h, 'parent basis changed: '+name)
    am = io.load(parent/'analysis/manifest.json')
    io.require(am['schema'] == 'hcr-exp27-analysis-manifest-v1', 'parent analysis schema')
    check_inventory(parent/'analysis',am['files'])
    io.require(set(io.inventory(parent/'analysis')) == set(am['files'])|{'manifest.json'}, 'parent analysis inventory')
    # An old audit-failure record is retained, not erased or treated as new research.
    return dict(plan_sha256=io.file_hash(parent/'plan.json'), raw_manifest_sha256=io.file_hash(parent/'manifest.json'),
                raw_files=len(m['files']), source_files=len(plan['source_hashes']),
                preserved_audit_failure_files=[n for n in io.inventory(parent) if n.startswith('audit_failures/')])


def parent_check(parent):
    report = parent_files_check(parent)
    # Fresh process: previously imported installed modules cannot replace the audited snapshot.
    worker = Path(__file__).with_name('legacy_worker.py')
    p = subprocess.run([sys.executable, '-X','utf8','-B',str(worker),'--parent',str(io.safe(parent))],
                       capture_output=True, encoding='utf-8', errors='strict', timeout=180)
    io.require(p.returncode == 0, 'parent independent replay failed:\n'+p.stderr+'\n'+p.stdout)
    result = io.loads(p.stdout)
    io.require(result['verified'] is True, 'parent replay did not verify')
    return dict(report, replay=result)


def source_inventory(root):
    package = package_check(root)
    names = sorted(set(package['files'])|set(NATIVE_BLOBS)|{'R047_MANIFEST.json'})
    return {n: io.file_hash(io.child(root,n)) for n in names}


def parent_addendum(report):
    ids = report['replay']['ID_controls']
    out=['# EXP-27 독립 재검산 및 보고 보완', '',
         '이 문서는 원래 EXP-27의 raw/summary/가설 기준을 수정하지 않는 별도 addendum입니다.',
         f"원자료 {report['raw_files']}개와 선언된 source {report['source_files']}개를 원래 해시로 확인했습니다.",
         f"A {report['replay']['source_queries']}개 / B {report['replay']['followups']}개 및 이벤트 {report['replay']['stream_records']}개를 원래 독립 evaluator로 재생했습니다.", '',
         '## 원래 H_ID 전체 판정', '', '| 상황 | 처리 | 원래 판정 | 연산 수 동일 |', '|---|---|---|---|']
    for row in ids:
        out.append(f"| {row['scenario']} | {row['arm']} | {row['prediction']} | {row['operation_counts_equal']} |")
    out += ['', '원래 H_ID는 전체 연산 수를 포함했습니다. premise_changed의 세 carry 처리에서 실패한 판정을 유지합니다.',
        'ID순 assumed_edges → 같은 순서의 dependency validation → 첫 불일치 즉시 종료로 검사 수가 달라집니다. 이는 native ticks 변화와 별개입니다.',
        '새 EXP-28의 H_ID_native는 사전에 더 좁게 고정한 별도 질문이며, 원래 H_ID를 성공으로 바꾸지 않습니다.',
        '누락된 로그의 재생성, raw 변경, 기존 manifest 축소는 수행하지 않았습니다.', '']
    return '\n'.join(out).encode('utf-8')
