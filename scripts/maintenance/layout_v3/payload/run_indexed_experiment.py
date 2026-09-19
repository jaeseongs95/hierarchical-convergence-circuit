"""Current research dispatcher. Archived artifacts are catalogued, never silently executed."""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

# Explicit baseline contract: changing the current release is a separate operation.
CURRENT = {'EXP-29': 'Run-HCR-R048.py', 'EXP-30': 'Run-HCR-R049.py'}
PATH_FIELDS = ('directory', 'design', 'frozen_design', 'evidence_directory',
               'implementation_validation_directory', 'release_manifest', 'legacy_python_entrypoint')

def local_path(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or name != path.as_posix()
            or any(x in ('', '.', '..', '.git') for x in name.split('/'))
            or any(c in name for c in ('\\', ':', '\0', '\n', '\r'))):
        raise ValueError('Unsafe catalog path: ' + repr(name))
    p = root / name
    for q in (p, *p.parents):
        if q.is_symlink() or (hasattr(q, 'is_junction') and q.is_junction()):
            raise ValueError('Linked catalog path: ' + name)
        if q == root:
            break
    return p

def read_index(root: Path) -> dict:
    index = json.loads(local_path(root, 'experiments/INDEX.json').read_text(encoding='utf-8'))
    if index.get('layout_schema') != 'hcc-layout-v3-catalog':
        raise ValueError('The experiment index is not the layout-v3 catalog.')
    rows = index['experiments']
    ids = [r['experiment_id'] for r in rows]
    if len(ids) != len(set(ids)) or index['default_experiment'] not in CURRENT:
        raise ValueError('Duplicate experiment or unsupported default.')
    for row in rows:
        for name in PATH_FIELDS:
            rel = row.get(name)
            if rel is not None and not local_path(root, rel).exists():
                raise ValueError('Missing catalog target: ' + rel)
        expected = CURRENT.get(row['experiment_id'])
        entry = row.get('current_python_entrypoint')
        if entry != expected:
            raise ValueError('Unexpected current dispatcher target: ' + row['experiment_id'])
        if entry and (not local_path(root, entry).is_file()
                      or row['execution_status'] != 'installed_current_contract'):
            raise ValueError('Current entrypoint is not an installed regular file.')
    if not set(CURRENT).issubset(ids):
        raise ValueError('Missing current releases in index.')
    return index

def main(argv=None, *, root: Path | None = None) -> int:
    if sys.version_info < (3, 12):
        raise SystemExit('Existing Python 3.12+ is required. Nothing is installed.')
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list', action='store_true', help='List current and historical entries without running a study.')
    p.add_argument('--check-index', action='store_true', help='Check referenced paths without running a study.')
    p.add_argument('--describe', metavar='EXP-ID')
    p.add_argument('--experiment', help='Current installed experiment; default remains EXP-30.')
    a = p.parse_args(argv)
    try:
        index = read_index(root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.error(str(exc))
    if a.check_index:
        print(json.dumps({'verified': True, 'experiments': len(index['experiments']),
                          'study_executed': False}, ensure_ascii=False))
        return 0
    if a.list:
        for row in index['experiments']:
            loc = row.get('current_python_entrypoint') or row.get('legacy_python_entrypoint') or '-'
            print(row['experiment_id'], row['execution_status'], loc)
        return 0
    requested = a.describe or a.experiment or index['default_experiment']
    rows = [r for r in index['experiments'] if r['experiment_id'] == requested]
    if len(rows) != 1:
        p.error('Unknown experiment: ' + requested)
    row = rows[0]
    if a.describe:
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0
    rel = row.get('current_python_entrypoint')
    if not rel:
        p.error(requested + ': historical artifact, not a runnable current-release contract. '
                'Use the original commit/sealed source for reproduction; see docs/current/REPOSITORY_GUIDE.ko.md.')
    # Preserve the installed R048/R049 entrypoint, arguments, working directory and exit status.
    return subprocess.call([sys.executable, '-X', 'utf8', '-B', str(local_path(root, rel))], cwd=root)

if __name__ == '__main__':
    raise SystemExit(main())
