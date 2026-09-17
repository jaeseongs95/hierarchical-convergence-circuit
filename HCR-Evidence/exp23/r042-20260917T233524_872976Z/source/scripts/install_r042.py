"""R042 추가 파일만 설치한다. 기존 R041/사용자 수정 파일을 강제 덮어쓰지 않고 Git/네트워크 작업도 하지 않는다."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import traceback
import zipfile

BASIS = '11f43790c0cb1b4732199ae4fb17c5bbbed4cd5b'
R041_BLOB = '71ba1f9f154341c63bb8e466dcc2a95d357f63af'
ROOT_FILES = {'R042_MANIFEST.json','R042_README.ko.md','Run-HCR-R042.py','Run-HCR-R042.bat'}
SCRIPT_FILES = {'scripts/r042_cli.py','scripts/verify_r042.py','scripts/install_r042.py','scripts/bootstrap_r042.ps1'}
PREFIXES = ('tools/r042_id_role_isolation/','experiments/exp-23-id-role-isolation/','validation/r042/')
RESERVED = {'CON','PRN','AUX','NUL'} | {f'{s}{i}' for s in ('COM','LPT') for i in range(1,10)}


def require(test, message):
    if not test:
        raise ValueError(message)


def loads(text):
    def pairs(values):
        out = {}
        for k, v in values:
            require(k not in out, 'JSON duplicate key: ' + k)
            out[k] = v
        return out
    def bad(value):
        raise ValueError('nonfinite JSON: ' + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad)


def text_hash(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def check_path(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name and '\0' not in name,
            'Unsafe archive path')
    p = PurePosixPath(name)
    require(not p.is_absolute() and name == p.as_posix() and all(x not in ('','.','..') for x in name.split('/')),
            'Archive path traversal')
    for part in p.parts:
        require(not part.endswith((' ','.')) and part.split('.')[0].upper() not in RESERVED and
                not any(ord(ch) < 32 or ch in '<>"|?*' for ch in part), 'Invalid Windows archive component')
    return name


def allowed(name):
    return name in ROOT_FILES or name in SCRIPT_FILES or name.startswith(PREFIXES) or (
        name.startswith('docs/R042_') and name.endswith('.md'))


def safe(path):
    p = Path(path).expanduser().absolute()
    require(not any(x.is_symlink() or (hasattr(x, 'is_junction') and x.is_junction()) for x in (p, *p.parents)),
            'Symlink/junction destination rejected')
    return p.resolve()


def read_payload(archive):
    files = {}; seen = set(); total = 0
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            name = check_path(entry.filename)
            require(not entry.is_dir() and allowed(name), 'Non-R042 path in archive: ' + name)
            require(name.casefold() not in seen, 'Duplicate/case-colliding ZIP path')
            seen.add(name.casefold())
            mode = entry.external_attr >> 16
            require(not stat.S_ISLNK(mode) and not entry.flag_bits & 1, 'Link/encrypted ZIP entry rejected')
            total += entry.file_size
            require(entry.file_size <= 10_000_000 and total <= 50_000_000, 'Archive resource limit')
            files[name] = z.read(entry)
    require('R042_MANIFEST.json' in files, 'Missing R042 manifest')
    m = loads(files['R042_MANIFEST.json'].decode('utf-8'))
    require(m['schema'] == 'hcr-r042-additive-release-v1' and m['basis_commit'] == BASIS,
            'Release schema/basis mismatch')
    require(set(files) == set(m['files']) | {'R042_MANIFEST.json'}, 'Unlisted/missing archive payload')
    for name, h in m['files'].items():
        require(text_hash(files[name]) == h, 'ZIP checksum mismatch: ' + name)
    return files


def check_basis(root):
    require((root/'src/hcr').is_dir() and (root/'Run-HCR-R041.py').is_file(),
            'Not an installed HCR R041 repository root')
    b = safe(root/'R041_MANIFEST.json').read_bytes().replace(b'\r\n', b'\n')
    actual = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    require(actual == R041_BLOB, 'R041 baseline manifest mismatch. No files were installed.')
    m = loads(b.decode('utf-8'))
    for name, h in m['files'].items():
        check_path(name)
        p = safe(root/name)
        require(root in p.parents, 'Baseline path traversal')
        require(p.is_file() and text_hash(p.read_bytes()) == h, 'Modified R041 baseline file: ' + name)


def install(repo, archive):
    root = safe(repo); archive = safe(archive)
    require(root.is_dir(), 'Repository folder missing')
    files = read_payload(archive)
    check_basis(root)
    to_write = []; same = []
    # 충돌을 전부 먼저 검사한다. 이미 존재하는 사용자 수정 파일은 덮어쓰지 않는다.
    for name, data in files.items():
        target = safe(root/name)
        require(root in target.parents, 'Destination escape')
        for parent in target.parents:
            if parent == root:
                break
            require(not parent.exists() or parent.is_dir(), 'Destination parent is a file')
        if target.exists():
            require(target.is_file() and text_hash(target.read_bytes()) == text_hash(data),
                    'Modified/existing R042 file conflict: ' + name + ' (not overwritten)')
            same.append(name)
        else:
            to_write.append((name, data))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    log = safe(root/'HCR-Evidence/deployments'/('r042-' + stamp))
    log.mkdir(parents=True, exist_ok=False)
    done = []
    try:
        with (log/'events.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            for name, data in sorted(to_write):
                target = safe(root/name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as f:
                    f.write(data); f.flush(); os.fsync(f.fileno())
                done.append(name)
                stream.write(json.dumps(dict(installed=name, sha256=text_hash(data)), ensure_ascii=False)+'\n')
                stream.flush(); os.fsync(stream.fileno())
        for name, data in files.items():
            require(text_hash(safe(root/name).read_bytes()) == text_hash(data), 'Post-install mismatch')
        report = dict(schema='hcr-r042-installation-v1', verified=True, basis_commit=BASIS,
            archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), created=done,
            already_identical=sorted(same), overwritten=[], git_commands_executed=False, network_used=False)
        (log/'installation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return dict(installed=len(done), already_identical=len(same), installation_record=str(log/'installation.json'))
    except BaseException as exc:
        (log/'failure.json').write_text(json.dumps(dict(error=repr(exc), traceback=traceback.format_exc(),
            created=done, automatic_rollback=False), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description='Install additive R042 sources without overwriting files')
    p.add_argument('--repo', required=True); p.add_argument('--archive', required=True)
    a = p.parse_args(argv)
    require(sys.version_info >= (3,12), 'Python 3.12 or newer required')
    print(json.dumps(install(a.repo, a.archive), ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
