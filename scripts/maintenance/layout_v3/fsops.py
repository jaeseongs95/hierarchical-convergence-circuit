"""Journaled local file transaction. No network, Git writes, or test execution."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import uuid

class LayoutError(RuntimeError):
    pass

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def encode(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')

def loads(data):
    def pairs(xs):
        result = {}
        for k, v in xs:
            if k in result:
                raise LayoutError('Duplicate JSON key: ' + k)
            result[k] = v
        return result
    return json.loads(data, object_pairs_hook=pairs)

def relpath(name: str) -> str:
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or name != p.as_posix()
            or any(c in name for c in ('\\', ':', '\0', '\n', '\r'))
            or any(x in ('', '.', '..', '.git') for x in name.split('/'))):
        raise LayoutError('Unsafe relative path: ' + repr(name))
    return name

def safe(root: Path, name: str) -> Path:
    p = root / relpath(name)
    for q in (p, *p.parents):
        if q.is_symlink() or (hasattr(q, 'is_junction') and q.is_junction()):
            raise LayoutError('Refusing linked path: ' + str(q))
        if q == root:
            break
    return p

def current_hash(p: Path) -> str | None:
    if not p.exists():
        if p.is_symlink():
            raise LayoutError('Broken symlink: ' + str(p))
        return None
    if p.is_symlink() or not p.is_file():
        raise LayoutError('Not a regular file: ' + str(p))
    h = hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()

def append(path: Path, value) -> None:
    with path.open('ab') as f:
        f.write((json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8'))
        f.flush()
        os.fsync(f.fileno())

def write_new(p: Path, data: bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def git(root: Path, *args: str) -> bytes:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    r = subprocess.run(['git', '-c', 'core.quotepath=false', '-C', str(root), *args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if r.returncode:
        raise LayoutError('Git read failed: ' + ' '.join(args) + '\n' + r.stderr.decode('utf-8', 'replace'))
    return r.stdout

def snapshot(root: Path, toolkit: str, evidence_rel: str) -> dict:
    """Inventory ALL regular working files, excluding only this tool, this run and Git/cache directories.

    Existing runs and existing evidence are included. Reparse points are never followed.
    """
    result = {}
    excluded = (toolkit.rstrip('/') + '/', evidence_rel.rstrip('/') + '/')
    def visit(folder):
        for item in sorted(os.scandir(folder), key=lambda x: x.name):
            p = Path(item.path)
            n = p.relative_to(root).as_posix()
            if n in (toolkit, evidence_rel) or n.startswith(excluded):
                continue
            if n == '.git' or (item.name in ('__pycache__', '.venv', 'venv')
                    and not n.startswith(('HCR-Evidence/', 'archive/', 'evidence/', 'validation/'))
                    and item.is_dir(follow_symlinks=False)):
                continue
            # Lock contains only orchestration state, not research evidence.
            if n == 'HCR-Evidence/repository-layout/layout-v3.lock':
                continue
            if p.is_symlink():
                result[n] = {'kind': 'symlink', 'target': os.readlink(p)}
            elif hasattr(p, 'is_junction') and p.is_junction():
                result[n] = {'kind': 'junction', 'target': os.readlink(p)}
            elif item.is_dir(follow_symlinks=False):
                visit(p)
            elif item.is_file(follow_symlinks=False):
                result[n] = {'kind': 'file', 'sha256': current_hash(p), 'size': p.stat().st_size}
            else:
                raise LayoutError('Special filesystem object: ' + n)
    visit(root)
    ensure_case_unique(result)
    return result

def ensure_case_unique(names):
    folded = {}
    for name in names:
        key = name.casefold()
        if key in folded:
            raise LayoutError('Case-colliding Windows paths: ' + folded[key] + ' / ' + name)
        folded[key] = name

class Transaction:
    def __init__(self, root: Path, evidence: Path, plan: dict):
        self.root, self.evidence, self.plan = root, evidence, plan
        self.journal = evidence / 'operations.jsonl'

    def mkdirs(self, folder: Path):
        todo = []
        p = folder
        while p != self.root and not p.exists():
            todo.append(p)
            p = p.parent
        for p in reversed(todo):
            n = p.relative_to(self.root).as_posix()
            append(self.journal, {'event': 'mkdir_intent', 'path': n})
            p.mkdir(exist_ok=False)
            append(self.journal, {'event': 'mkdir_done', 'path': n})

    def change(self, op: dict, after: bool, prefix: str):
        p = safe(self.root, op['path'])
        expected = op['before_sha256'] if after else op['after_sha256']
        target = op['after_sha256'] if after else op['before_sha256']
        side = 'after' if after else 'before'
        actual = current_hash(p)
        if actual != expected:
            raise LayoutError('File changed outside this transaction: ' + op['path'])
        append(self.journal, {'event': prefix + '_intent', 'path': op['path'], 'expected': expected, 'target': target})
        if target is None:
            p.unlink()
        else:
            data = safe(self.evidence, op[side + '_file']).read_bytes()
            if digest(data) != target:
                raise LayoutError('Staged bytes changed: ' + op['path'])
            self.mkdirs(p.parent)
            # Exclusive temporary file, then recheck immediately before atomic replacement.
            temp = p.with_name('.hcc-layout-' + uuid.uuid4().hex + '.tmp')
            append(self.journal, {'event': 'temp_intent', 'path': temp.relative_to(self.root).as_posix(), 'sha256': target})
            write_new(temp, data)
            if current_hash(p) != expected:
                raise LayoutError('File changed before publication: ' + op['path'])
            os.replace(temp, p)
        if current_hash(p) != target:
            raise LayoutError('Publication byte mismatch: ' + op['path'])
        append(self.journal, {'event': prefix + '_done', 'path': op['path'], 'sha256': target})

    def apply(self):
        # Each intention is durable before its write; no lost local "moved" list on exception.
        for op in self.plan['operations']:
            self.change(op, True, 'apply')

    def recover(self) -> dict:
        restored, untouched, conflicts = [], [], []
        events = []
        if self.journal.exists():
            for line in self.journal.read_bytes().splitlines():
                try:
                    events.append(loads(line))
                except ValueError:
                    # A torn final journal row is not authority to overwrite any file.
                    conflicts.append({'path': 'operations.jsonl', 'reason': 'incomplete journal row'})
        touched = {x['path'] for x in events if x.get('event') == 'apply_intent'}
        for op in reversed(self.plan['operations']):
            if op['path'] not in touched:
                continue
            try:
                p = safe(self.root, op['path'])
                actual = current_hash(p)
                if actual == op['before_sha256']:
                    untouched.append(op['path'])
                elif actual == op['after_sha256']:
                    self.change(op, False, 'rollback')
                    restored.append(op['path'])
                else:
                    conflicts.append({'path': op['path'], 'reason': 'external bytes; not overwritten'})
            except Exception as exc:
                conflicts.append({'path': op['path'], 'reason': str(exc)})
        for item in reversed(events):
            if item.get('event') == 'temp_intent':
                try:
                    p = safe(self.root, item['path'])
                    if p.exists():
                        if current_hash(p) == item['sha256']:
                            p.unlink()
                        else:
                            conflicts.append({'path': item['path'], 'reason': 'partial/external temporary bytes preserved'})
                except Exception as exc:
                    conflicts.append({'path': item['path'], 'reason': str(exc)})
            if item.get('event') == 'mkdir_done':
                p = safe(self.root, item['path'])
                try:
                    p.rmdir()
                except OSError:
                    pass  # Never delete a non-empty directory.
        return {'complete': not conflicts, 'restored': restored, 'unchanged': untouched, 'conflicts': conflicts}
