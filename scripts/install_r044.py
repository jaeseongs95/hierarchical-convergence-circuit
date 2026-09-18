"""R044 추가 파일만 설치한다. 기존 R043/사용자 수정 파일을 강제 덮어쓰지 않고 Git/네트워크 작업도 하지 않는다."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import traceback
import zipfile

BASIS = '6b8ff8ab4c4858a3ab8f1a24e82b9033372133fc'
R043_BLOB = '4a7467164dd82518c9193490c81623d6102d815f'
ROOT_FILES = {'R044_MANIFEST.json','R044_README.ko.md','Run-HCR-R044.py','Run-HCR-R044.cmd'}
SCRIPT_FILES = {'scripts/r044_cli.py','scripts/verify_r044.py','scripts/install_r044.py','scripts/bootstrap_r044.ps1'}
PREFIXES = ('tools/r044_reuse_contribution/','experiments/exp-25-reuse-contribution/','validation/r044/')
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
        name.startswith('docs/R044_') and name.endswith('.md'))


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
            require(not entry.is_dir() and allowed(name), 'Non-R044 path in archive: ' + name)
            require(name.casefold() not in seen, 'Duplicate/case-colliding ZIP path')
            seen.add(name.casefold())
            mode = entry.external_attr >> 16
            require(not stat.S_ISLNK(mode) and not entry.flag_bits & 1, 'Link/encrypted ZIP entry rejected')
            total += entry.file_size
            require(entry.file_size <= 10_000_000 and total <= 50_000_000, 'Archive resource limit')
            files[name] = z.read(entry)
    require('R044_MANIFEST.json' in files, 'Missing R044 manifest')
    m = loads(files['R044_MANIFEST.json'].decode('utf-8'))
    require(m['schema'] == 'hcr-r044-additive-release-v1' and m['basis_commit'] == BASIS,
            'Release schema/basis mismatch')
    require(set(files) == set(m['files']) | {'R044_MANIFEST.json'}, 'Unlisted/missing archive payload')
    for name, h in m['files'].items():
        require(text_hash(files[name]) == h, 'ZIP checksum mismatch: ' + name)
    return files


def check_basis(root, log=None):
    require((root/'src/hcr').is_dir() and (root/'Run-HCR-R043.py').is_file(),
            'Not an installed HCR R043 repository root')
    b = safe(root/'R043_MANIFEST.json').read_bytes().replace(b'\r\n', b'\n')
    actual = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    require(actual == R043_BLOB, 'R043 baseline manifest mismatch. No files were installed.')
    m = loads(b.decode('utf-8'))
    for name, h in m['files'].items():
        check_path(name)
        p = safe(root/name)
        require(root in p.parents, 'Baseline path traversal')
        require(p.is_file() and text_hash(p.read_bytes()) == h, 'Modified R043 baseline file: ' + name)


    env = dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.run([sys.executable,'-X','utf8','-B',str(root/'scripts/verify_r043.py')],
                   cwd=root,env=env,capture_output=True,text=True,encoding='utf-8')
    text = proc.stdout + proc.stderr
    print(text,end='',flush=True)
    if log is not None:
        with (log/'baseline_verify.log').open('x',encoding='utf-8') as f: f.write(text)
    require(proc.returncode == 0, 'R043 dependency baseline check failed: '+str(proc.returncode))


def install(repo, archive):
    root = safe(repo); archive = safe(archive)
    require(root.is_dir(), 'Repository folder missing')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    log = safe(root/'HCR-Evidence/deployments'/('r044-' + stamp))
    log.mkdir(parents=True, exist_ok=False)
    try:
        files = read_payload(archive)
        check_basis(root, log)
        to_write = []; same = []
        for name, data in files.items():
            target = safe(root/name)
            require(root in target.parents, 'Destination escape')
            for parent in target.parents:
                if parent == root: break
                require(not parent.exists() or parent.is_dir(), 'Destination parent is a file')
            if target.exists():
                require(target.is_file() and text_hash(target.read_bytes()) == text_hash(data),
                        'Modified/existing R044 file conflict: '+name+' (not overwritten)')
                same.append(name)
            else:
                to_write.append((name,data))
    except BaseException as exc:
        (log/'failure.json').write_text(json.dumps(dict(stage='preflight',error=repr(exc),
            traceback=traceback.format_exc(),created=[],automatic_retry=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise
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
        report = dict(schema='hcr-r044-installation-v1', verified=True, basis_commit=BASIS,
            archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), created=done,
            already_identical=sorted(same), overwritten=[], git_commands_executed=False, network_used=False)
        (log/'installation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return dict(installed=len(done), already_identical=len(same), installation_record=str(log/'installation.json'))
    except BaseException as exc:
        (log/'failure.json').write_text(json.dumps(dict(error=repr(exc), traceback=traceback.format_exc(),
            created=done, automatic_rollback=False), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description='Install additive R044 sources without overwriting files')
    p.add_argument('--repo', required=True); p.add_argument('--archive', required=True)
    a = p.parse_args(argv)
    require(sys.version_info >= (3,12), 'Python 3.12 or newer required')
    print(json.dumps(install(a.repo, a.archive), ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
