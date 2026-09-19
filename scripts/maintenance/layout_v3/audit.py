"""Read-only evaluator for a persisted migration plan; never imports the plan builder or mutator."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(p: Path) -> str:
    result = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def confined(root: Path, name: str) -> Path:
    parts = name.split('/')
    if (not name or name != PurePosixPath(name).as_posix() or name.startswith('/')
            or any(x in ('', '.', '..', '.git') for x in parts)
            or any(x in name for x in ('\\', ':', '\0', '\n', '\r'))):
        raise ValueError('Audit path is unsafe: ' + repr(name))
    p = root / name
    for parent in (p, *p.parents):
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Audit refuses reparse path: ' + name)
        if parent == root:
            break
    return p


def inventory(root: Path, toolkit: str, run: str) -> dict:
    out = {}
    for folder, directories, files in os.walk(root, topdown=True, followlinks=False):
        allowed = []
        for name in directories:
            p = Path(folder) / name
            rel = p.relative_to(root).as_posix()
            if (rel == '.git' or rel in (toolkit, run)
                    or (name in ('__pycache__', '.venv', 'venv')
                        and not rel.startswith(('HCR-Evidence/', 'archive/', 'evidence/', 'validation/')))):
                continue
            if p.is_symlink():
                out[rel] = {'kind': 'symlink', 'target': os.readlink(p)}
            elif hasattr(p, 'is_junction') and p.is_junction():
                out[rel] = {'kind': 'junction', 'target': os.readlink(p)}
            else:
                allowed.append(name)
        directories[:] = allowed
        for name in files:
            p = Path(folder) / name
            rel = p.relative_to(root).as_posix()
            if rel in ('.git', 'HCR-Evidence/repository-layout/layout-v3.lock'):
                continue
            if p.is_symlink():
                out[rel] = {'kind': 'symlink', 'target': os.readlink(p)}
            else:
                out[rel] = {'kind': 'file', 'sha256': file_hash(p), 'size': p.stat().st_size}
    return out


def release(root: Path, rev: str) -> dict:
    p = confined(root, rev + '_MANIFEST.json')
    record = json.loads(p.read_bytes())
    if record['schema'] != 'hcr-' + rev.lower() + '-release-v1':
        raise ValueError('Unexpected release schema: ' + rev)
    checked = 0
    for name, expected in record['files'].items():
        data = confined(root, name).read_bytes()
        if h(data.replace(b'\r\n', b'\n')) != expected:
            raise ValueError('Release hash mismatch: ' + rev + ':' + name)
        checked += 1
    return {'revision': rev, 'verified': True, 'files': checked, 'manifest_sha256': file_hash(p)}


def transform_checks(root: Path, plan: dict, stage: Path) -> dict:
    checks = []
    op_by_path = {op['path']: op for op in plan['operations']}
    if len(op_by_path) != len(plan['operations']):
        raise ValueError('Duplicate operation in plan')
    for item in plan['layout']['transformations']:
        old, new, test = item['source'], item['destination'], item['test']
        before = confined(stage, op_by_path[old]['before_file']).read_bytes()
        after = confined(root, new).read_bytes()
        if old.endswith('.py'):
            expected = before.replace(b'Path(__file__).resolve().parent', b'Path(__file__).resolve().parents[2]')
            if before.count(b'Path(__file__).resolve().parent') != 2:
                raise ValueError('Unexpected historical bootstrap')
        else:
            expected = before.replace(b'= $PSScriptRoot', b'= Split-Path -Parent (Split-Path -Parent $PSScriptRoot)')
            if before.count(b'= $PSScriptRoot') != 1:
                raise ValueError('Unexpected PowerShell bootstrap')
        if expected != after:
            raise ValueError('Launcher changes extend beyond bootstrap relocation: ' + old)
        before_test = confined(stage, op_by_path[test]['before_file']).read_bytes()
        after_test = confined(root, test).read_bytes()
        if after_test.replace(new.encode(), old.encode()) != before_test:
            raise ValueError('Test changes extend beyond path substitution: ' + test)
        # Independently assert the entire test syntax/assertion graph is identical after path reversal.
        if ast.dump(ast.parse(before_test.decode('utf-8-sig'))) != ast.dump(ast.parse(after_test.decode('utf-8-sig').replace(new, old))):
            raise ValueError('Test AST changed: ' + test)
        if confined(root, old).exists():
            raise ValueError('Root compatibility clutter remains: ' + old)
        checks.append({'launcher': new, 'test': test, 'assertions_preserved': True})
    return {'checked': len(checks), 'items': checks}


def catalog_checks(root: Path, plan: dict, stage: Path) -> dict:
    idx = json.loads(confined(root, 'experiments/INDEX.json').read_bytes())
    old_op = next(x for x in plan['operations'] if x['path'] == 'experiments/INDEX.json')
    old = json.loads(confined(stage, old_op['before_file']).read_bytes())
    if idx['default_experiment'] != old['default_experiment'] or idx['default_experiment'] != 'EXP-30':
        raise ValueError('Default experiment was changed')
    rows = idx['experiments']; old_by_id = {r['experiment_id']: r for r in old['experiments']}
    if len(rows) != len(old_by_id) or len({r['experiment_id'] for r in rows}) != len(rows):
        raise ValueError('Experiment identities changed')
    allowed_changes = {'legacy_python_entrypoint', 'release_manifest', 'current_python_entrypoint', 'execution_status'}
    path_fields = ('directory', 'design', 'frozen_design', 'evidence_directory', 'implementation_validation_directory',
                   'legacy_python_entrypoint', 'release_manifest', 'current_python_entrypoint')
    refs = 0
    for row in rows:
        previous = old_by_id[row['experiment_id']]
        for key in (set(row) | set(previous)) - allowed_changes:
            if row.get(key) != previous.get(key):
                raise ValueError('Research metadata changed: ' + row['experiment_id'] + ':' + key)
        for field in path_fields:
            val = row.get(field)
            if val is not None:
                if not confined(root, val).exists():
                    raise ValueError('Dangling catalog path: ' + val)
                refs += 1
        expected = {'EXP-29': 'Run-HCR-R048.py', 'EXP-30': 'Run-HCR-R049.py'}.get(row['experiment_id'])
        if row['current_python_entrypoint'] != expected:
            raise ValueError('Historical/current execution boundary violated')
    return {'verified': True, 'experiments': len(rows), 'resolved_paths': refs, 'research_metadata_unchanged': True}


def evaluate(root: Path, stage: Path, *, rolled_back: bool = False) -> dict:
    plan_bytes = (stage / 'plan.json').read_bytes()
    if h(plan_bytes) != (stage / 'plan.sha256').read_text().strip():
        raise ValueError('Frozen plan has changed')
    plan = json.loads(plan_bytes)
    if file_hash(stage / 'before_inventory.json') != plan['before_inventory_sha256']:
        raise ValueError('Before inventory has changed')
    expected = json.loads((stage / 'before_inventory.json').read_bytes())
    if not rolled_back:
        for op in plan['operations']:
            if op['after_sha256'] is None:
                expected.pop(op['path'], None)
            else:
                data = confined(stage, op['after_file']).read_bytes()
                if h(data) != op['after_sha256']:
                    raise ValueError('Planned output changed: ' + op['path'])
                expected[op['path']] = {'kind': 'file', 'sha256': h(data), 'size': len(data)}
    actual = inventory(root, plan['toolkit'], stage.relative_to(root).as_posix())
    differences = [p for p in sorted(set(expected) | set(actual)) if actual.get(p) != expected.get(p)]
    if differences:
        raise ValueError('Working files differ from frozen plan: ' + repr(differences[:30]))
    result = {'verified': True, 'files_checked': len(expected), 'scope': 'all working files except explicit tool/run/Git/cache exclusions',
              'unplanned_file_differences': [], 'rolled_back': rolled_back}
    if not rolled_back:
        result['transformations'] = transform_checks(root, plan, stage)
        result['catalog'] = catalog_checks(root, plan, stage)
        result['current_releases'] = [release(root, 'R048'), release(root, 'R049')]
    return result
