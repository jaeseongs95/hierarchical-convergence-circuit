"""One-click layout migration; full core tests run once and only after publication."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import traceback
import uuid
import audit
import layout
from fsops import LayoutError, Transaction, current_hash, digest, encode, git, loads, safe, snapshot, write_new

ROOT_EVIDENCE = 'HCR-Evidence/repository-layout'
LOCK = ROOT_EVIDENCE + '/layout-v3.lock'


def preflight(root: Path, package: Path) -> dict:
    if sys.version_info < (3, 12):
        raise LayoutError('Existing Python 3.12+ is required')
    top = Path(git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
    if top != root or package.resolve() != root / 'scripts/maintenance/layout_v3':
        raise LayoutError('Extract the scripts/ folder directly into the repository root.')
    for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-apply', 'rebase-merge'):
        path = Path(git(root, 'rev-parse', '--git-path', marker).decode('utf-8').strip())
        if not path.is_absolute():
            path = root / path
        if path.exists():
            raise LayoutError('Git operation in progress: ' + marker)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    if head != layout.BASE:
        raise LayoutError('This migration is pinned to ' + layout.BASE + '; current HEAD is ' + head + '. No fetch/pull was performed.')
    dirty = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=no')
    if dirty:
        raise LayoutError('Tracked working/index changes exist; nothing will be overwritten.\n' + dirty.decode('utf-8', 'replace'))
    for name, expected in layout.PINS.items():
        committed = git(root, 'show', layout.BASE + ':' + name)
        actual_blob = hashlib.sha1(b'blob ' + str(len(committed)).encode() + b'\0' + committed).hexdigest()
        if actual_blob != expected:
            raise LayoutError('Pinned source identity differs: ' + name)
        if safe(root, name).read_bytes().replace(b'\r\n', b'\n') != committed.replace(b'\r\n', b'\n'):
            raise LayoutError('Working source differs from pinned commit: ' + name)
    releases = [audit.release(root, 'R048'), audit.release(root, 'R049')]
    receipt_name = layout.PREVIOUS_RUN + '/regression.json'
    receipt = safe(root, receipt_name).read_bytes()
    committed_receipt = git(root, 'show', layout.BASE + ':' + receipt_name)
    if receipt.replace(b'\r\n', b'\n') != committed_receipt.replace(b'\r\n', b'\n'):
        raise LayoutError('The previous regression receipt differs from the pushed baseline')
    baseline = loads(receipt)
    if baseline['tests_run'] != 602 or any(baseline[k] != 0 for k in ('errors', 'failures', 'returncode')):
        raise LayoutError('Previous core regression is not the successful baseline')
    skip_ids = [r['test'] for r in baseline['skipped']]
    if len(skip_ids) != len(set(skip_ids)):
        raise LayoutError('Duplicate baseline skip IDs')
    for path in ('archive/releases/INDEX.json', 'experiments/INDEX.json', 'START_HERE.ko.md', 'Run-HCR.cmd'):
        if not safe(root, path).is_file():
            raise LayoutError('Successful prior layout artifact is missing: ' + path)
    return {'head': head, 'python': sys.version, 'platform': sys.platform,
            'baseline_receipt': receipt_name, 'baseline_receipt_sha256': digest(receipt),
            'baseline_regression': baseline, 'current_releases': releases,
            'pre_cleanup_project_tests_executed': False}


def freeze(root: Path, package: Path, stage: Path, pre: dict) -> dict:
    toolkit = package.relative_to(root).as_posix()
    before = snapshot(root, toolkit, stage.relative_to(root).as_posix())
    write_new(stage / 'before_inventory.json', encode(before))
    meta, changes = layout.build(root, package)
    operations = []
    # Preserve original backups before publishing any edits; remove old launchers last.
    order = sorted(changes, key=lambda p: (0 if p.startswith(layout.ORIGINALS + '/') else 2 if changes[p] is None else 1, p))
    for i, name in enumerate(order):
        p = safe(root, name)
        old = p.read_bytes() if p.is_file() else None
        new = changes[name]
        if old == new:
            continue
        if p.exists() and not p.is_file():
            raise LayoutError('Output collision with non-file: ' + name)
        if old is None and name in before:
            raise LayoutError('Output is not a regular absent path: ' + name)
        # Existing output edits must be committed input, never overwrite an untracked user's file.
        if old is not None:
            git(root, 'ls-files', '--error-unmatch', '--', name)
        op = {'path': name, 'before_sha256': None if old is None else digest(old),
              'after_sha256': None if new is None else digest(new), 'before_file': None, 'after_file': None}
        for kind, data in (('before', old), ('after', new)):
            if data is not None:
                rel = f'staged/{i:04d}-{kind}.bin'
                write_new(stage / rel, data)
                op[kind + '_file'] = rel
        if old is not None and before.get(name, {}).get('sha256') != digest(old):
            raise LayoutError('Input changed during plan freezing: ' + name)
        operations.append(op)
    result = {'schema': 'hcc-layout-v3-plan', 'base_commit': layout.BASE, 'toolkit': toolkit,
              'before_inventory_sha256': current_hash(stage / 'before_inventory.json'),
              'operations': operations, 'layout': meta,
              'baseline_regression': pre['baseline_regression'],
              'baseline_receipt_sha256': pre['baseline_receipt_sha256']}
    write_new(stage / 'plan.json', encode(result))
    write_new(stage / 'plan.sha256', (digest(encode(result)) + '\n').encode())
    return result


def stop_tree(proc):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def final_regression(root: Path, package: Path, stage: Path) -> tuple[int, dict]:
    output = stage / 'regression.json'
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-X', 'utf8', '-B', str(package / 'probe.py'), '--repo', str(root), '--result', str(output)]
    write_new(stage / 'regression.started.json', encode({'command': command, 'cwd': str(root), 'automatic_retry': False}))
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    with (stage / 'regression.txt').open('xb') as log:
        p = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **options)
        pump_errors = []
        def pump():
            try:
                for line in iter(p.stdout.readline, b''):
                    log.write(line); log.flush()
                    sys.stdout.write(line.decode('utf-8', 'replace')); sys.stdout.flush()
            except BaseException as exc:
                pump_errors.append(str(exc))
        t = threading.Thread(target=pump, daemon=True); t.start()
        try:
            p.wait(timeout=1800)
            t.join(timeout=30)
            if t.is_alive() or pump_errors:
                raise LayoutError('Regression log pump did not complete: ' + repr(pump_errors))
        except BaseException:
            stop_tree(p); t.join(timeout=10)
            raise
        finally:
            if p.stdout:
                p.stdout.close()
    if not output.is_file():
        raise LayoutError('Regression ended without its result; see regression.txt')
    return p.returncode, loads(output.read_bytes())


def accept(baseline: dict, result: dict, code: int) -> dict:
    if code != 0 or any(result.get(k, 0) != 0 for k in ('errors', 'failures', 'expected_failures', 'unexpected_successes')):
        raise LayoutError('Core regression failed; see regression.txt and regression.json')
    if result['tests_run'] != baseline['tests_run'] or len(result['collected_ids']) != baseline['tests_run']:
        raise LayoutError('The core test collection count changed')
    if len(set(result['collected_ids'])) != len(result['collected_ids']):
        raise LayoutError('Duplicate core test IDs')
    old = {r['test']: r['reason'] for r in baseline['skipped']}
    now = {r['test']: r['reason'] for r in result['skipped']}
    if len(now) != len(result['skipped']):
        raise LayoutError('Duplicate final skip IDs')
    if any(old.get(k) != v for k, v in now.items()):
        raise LayoutError('New or differently explained skipped test. Skip is not a pass.')
    resolved = sorted(set(old) - set(now))
    if any(result['outcomes'].get(k) != 'pass' for k in resolved):
        raise LayoutError('A previous skip disappeared without an actual pass')
    if any(result['outcomes'].get(k) != ('skip' if k in now else 'pass') for k in result['collected_ids']):
        raise LayoutError('Unaccounted/incomplete core test outcomes')
    return {'verified': True, 'tests_run': result['tests_run'], 'passed': result['tests_run'] - len(now),
            'unchanged_environment_skips': result['skipped'], 'previous_skips_now_passed': resolved,
            'new_skips': [], 'pre_cleanup_tests_executed': False, 'final_core_runs': 1}


def seal(stage: Path):
    files = {p.relative_to(stage).as_posix(): current_hash(p) for p in stage.rglob('*') if p.is_file()}
    write_new(stage / 'bundle_manifest.json', encode({'schema': 'hcc-layout-v3-evidence', 'files': files}))


def find_success(root: Path):
    for p in sorted((root / ROOT_EVIDENCE).glob('layout-v3-*/success.json'), reverse=True):
        if p.is_file() and (p.parent / 'bundle_manifest.json').is_file() and not list(p.parent.glob('failure-*.json')):
            return p.parent
    return None


def verify_installed(root: Path) -> dict:
    stage = find_success(root)
    if stage is None:
        raise LayoutError('A layout state exists without a success receipt. Use RECOVER.cmd, not a reapply.')
    seal_record = loads((stage / 'bundle_manifest.json').read_bytes())
    for name, expected in seal_record['files'].items():
        if current_hash(safe(stage, name)) != expected:
            raise LayoutError('Successful evidence bytes changed: ' + name)
    raw = (stage / 'plan.json').read_bytes()
    if digest(raw) != (stage / 'plan.sha256').read_text().strip():
        raise LayoutError('The successful frozen plan changed')
    plan = loads(raw)
    for op in plan['operations']:
        if current_hash(safe(root, op['path'])) != op['after_sha256']:
            raise LayoutError('Installed layout file drift: ' + op['path'])
    for rev in ('R048', 'R049'):
        audit.release(root, rev)
    audit.catalog_checks(root, plan, stage)
    return {'status': 'ALREADY_APPLIED_AND_VERIFIED', 'success_evidence': str(stage), 'project_tests_rerun': False}



def process_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            # Access denied is not proof of a dead process.
            return ctypes.get_last_error() == 5
        try:
            exit_code = wintypes.DWORD()
            kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == 259
        finally:
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def recover(root: Path):
    lock = safe(root, LOCK)
    if not lock.is_file():
        raise LayoutError('No interrupted layout-v3 transaction is registered. Nothing to recover.')
    info = loads(lock.read_bytes())
    if process_alive(info.get('pid')):
        raise LayoutError('The original migration process is still running; recovery was not started.')
    stage = safe(root, info['stage'])
    if (stage / 'success.json').exists() and (stage / 'bundle_manifest.json').exists() and not list(stage.glob('failure-*.json')):
        verify_installed(root); lock.unlink()
        print('Completed run already verified; stale lock removed. No data rollback.'); return 0
    # Recovery is explicit; original failure/plan/regression files are never overwritten.
    plan_bytes = (stage / 'plan.json').read_bytes()
    if digest(plan_bytes) != (stage / 'plan.sha256').read_text().strip():
        raise LayoutError('Cannot recover a changed frozen plan')
    transaction = Transaction(root, stage, loads(plan_bytes))
    report = transaction.recover()
    try:
        report['independent_before_state_audit'] = audit.evaluate(root, stage, rolled_back=True)
    except Exception as exc:
        report['complete'] = False; report['independent_audit_error'] = str(exc)
    write_new(stage / ('recovery-' + uuid.uuid4().hex[:12] + '.json'), encode(report))
    if report['complete']:
        lock.unlink()
    print('Recovery complete:', report['complete'], '\nEvidence:', stage)
    return 0 if report['complete'] else 2


def apply(root: Path, package: Path) -> int:
    lock = safe(root, LOCK)
    if lock.exists():
        raise LayoutError('A layout transaction is active or interrupted. Check its evidence; use RECOVER.cmd after interruption.')
    if safe(root, layout.STATE).exists():
        print(encode(verify_installed(root)).decode()); return 0
    tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:10]
    stage = safe(root, ROOT_EVIDENCE + '/layout-v3-' + tag)
    stage.mkdir(parents=True, exist_ok=False)
    write_new(stage / '.gitattributes', b'* -text -filter -ident !working-tree-encoding\n')
    write_new(stage / '.gitignore', b'# Preserve migration evidence, including staged bytes and first failures.\n!*\n')
    write_new(lock, encode({'stage': stage.relative_to(root).as_posix(), 'pid': os.getpid(), 'base_commit': layout.BASE}))
    plan = None
    transaction = None
    rollback = None
    try:
        print('[1/6] Read-only preflight (no project tests)', flush=True)
        pre = preflight(root, package); write_new(stage / 'preflight.json', encode(pre))
        print('[2/6] Freeze file inventory, before/after bytes and plan', flush=True)
        plan = freeze(root, package, stage, pre)
        print('[3/6] Relocate six legacy launchers AND their test references; repair the catalog', flush=True)
        transaction = Transaction(root, stage, plan); transaction.apply()
        print('[4/6] Independent structure, assertion-AST, full-file and release-contract audit', flush=True)
        structure = audit.evaluate(root, stage); write_new(stage / 'structure_audit.json', encode(structure))
        print('[5/6] Final core regression ONCE. Live log: ' + str(stage / 'regression.txt'), flush=True)
        code, result = final_regression(root, package, stage)
        accepted = accept(pre['baseline_regression'], result, code)
        write_new(stage / 'regression_acceptance.json', encode(accepted))
        print('[6/6] Final immutable-file audit and evidence seal', flush=True)
        final = audit.evaluate(root, stage); write_new(stage / 'final_audit.json', encode(final))
        success = {'status': 'APPLIED_AND_VERIFIED', 'base_commit': layout.BASE,
                   'legacy_launchers_relocated': len(layout.LEGACY), 'test_paths_updated': len(layout.LEGACY),
                   'core_regression': accepted, 'research_experiment_executed': False,
                   'git_commit_push_performed': False}
        write_new(stage / 'summary.ko.md', ('# 저장소 레이아웃 V3\n\n```json\n' + encode(success).decode() + '```\n').encode('utf-8'))
        write_new(stage / 'success.json', encode(success)); seal(stage)
        try:
            lock.unlink()
        except OSError:
            print('Layout verified, but lock cleanup failed. RECOVER.cmd only clears the completed lock.', file=sys.stderr)
        print('LAYOUT_V3_APPLIED_AND_VERIFIED\nEvidence: ' + str(stage), flush=True)
        return 0
    except BaseException as exc:
        failure = {'error_type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        # A pre-seal failure must preserve provisional receipts without presenting them as success.
        for name in ('summary.ko.md', 'success.json'):
            q = stage / name
            if q.exists():
                q.rename(stage / ('provisional-' + name))
        write_new(stage / ('failure-' + uuid.uuid4().hex[:8] + '.json'), encode(failure))
        if transaction is not None:
            rollback = transaction.recover()
            try:
                rollback['independent_before_state_audit'] = audit.evaluate(root, stage, rolled_back=True)
            except BaseException as problem:
                rollback['complete'] = False; rollback['independent_audit_error'] = str(problem)
            write_new(stage / 'rollback.json', encode(rollback))
        status = {'status': 'FAILED', 'error': str(exc), 'rollback': rollback, 'evidence': str(stage)}
        if not (stage / 'summary.ko.md').exists():
            write_new(stage / 'summary.ko.md', ('# 저장소 레이아웃 V3 — 실패\n\n```json\n' + encode(status).decode() + '```\n').encode())
        if rollback is None or rollback['complete']:
            if lock.exists():
                lock.unlink()
        print('FAILED: ' + str(exc) + '\nEvidence: ' + str(stage), file=sys.stderr, flush=True)
        return 2


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('apply', 'recover', 'verify'), nargs='?', default='apply')
    a = p.parse_args(argv)
    package = Path(__file__).resolve().parent; root = package.parents[2]
    try:
        if a.action == 'apply':
            return apply(root, package)
        if a.action == 'recover':
            return recover(root)
        print(encode(verify_installed(root)).decode()); return 0
    except BaseException as exc:
        print('STOPPED: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
