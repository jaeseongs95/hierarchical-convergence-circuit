"""Small Git fixtures; not a complete HCC repository or research population."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
from unittest.mock import patch

PKG = Path(__file__).resolve().parents[1]
UPSTREAM = Path(__file__).resolve().parent / 'upstream'
sys.path.insert(0, str(PKG))
import layout
from fsops import encode, write_new, digest

HEADER = '''from pathlib import Path
import importlib.util
import unittest
import io
import tempfile
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
ROOT=Path(__file__).resolve().parents[1]
'''

def put(root, rel, data=b'fixture\n'):
    p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    return p

def repository(base: Path) -> tuple[Path, Path]:
    root = base / '한글 공백 repo'; root.mkdir()
    package = root / 'scripts/maintenance/layout_v3'
    shutil.copytree(PKG, package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in layout.LEGACY:
        put(root, name, (UPSTREAM / name).read_bytes())
    # Three exact upstream launcher-test excerpts; other model tests are NOT emulated.
    for r in ('031','032','033'):
        filename = layout.LEGACY['Run-HCR-R'+r+'.py']
        put(root, filename, (HEADER + (UPSTREAM / ('r'+r+'_tests.txt')).read_text()).encode())
    # Parser references are inert AST examples; real Windows parser tests are not claimed here.
    for name in ('Run-HCR-R02.ps1','Run-HCR-R021.ps1','Run-HCR-R03.ps1'):
        put(root, layout.LEGACY[name], (f"from pathlib import Path\nREF=Path(__file__).resolve().parents[1]/'{name}'\n").encode())
    idx_bytes = (UPSTREAM / 'INDEX.json').read_bytes()
    put(root, 'experiments/INDEX.json', idx_bytes)
    idx = json.loads(idx_bytes)
    for row in idx['experiments']:
        for field in ('directory','evidence_directory','implementation_validation_directory'):
            rel = row.get(field)
            if rel:
                put(root, rel + '/README.fixture.txt')
        for field in ('design','frozen_design'):
            rel = row.get(field)
            if rel:
                put(root, rel)
    for r in range(34,48):
        put(root, f'archive/releases/r{r:03d}/Run-HCR-R{r:03d}.py')
        put(root, f'archive/releases/r{r:03d}/R{r:03d}_MANIFEST.json', b'{"fixture":true}\n')
    for r in ('048','049'):
        fs = {}
        for path in (f'R{r}_README.ko.md', f'Run-HCR-R{r}.py', f'Run-HCR-R{r}.cmd', f'tools/r{r}/untouched.py'):
            p = put(root, path); fs[path] = digest(p.read_bytes())
        put(root, f'R{r}_MANIFEST.json', encode({'schema':f'hcr-r{r}-release-v1','files':fs,'base_commit':'fixture'}))
    for name in ('README.md','README.ko.md','START_HERE.ko.md','Run-HCR.cmd',
                 'experiments/INDEX.ko.md','docs/current/REPOSITORY_GUIDE.ko.md',
                 'scripts/run_indexed_experiment.py','archive/releases/INDEX.json',
                 'evidence/claims.yaml','theory/core-hypothesis.md','configs/r02.toml'):
        put(root, name)
    put(root, 'src/hcr/__init__.py', b'# Isolated import stub, no engine. Used ONLY by the six extracted launcher tests.\n')
    put(root, 'HCR-Evidence/old-raw/query.bin', b'untouched evidence\x00\r\n')
    baseline={'tests_run':6,'failures':0,'errors':0,'returncode':0,'skipped':[]}
    put(root, layout.PREVIOUS_RUN + '/regression.json', encode(baseline))
    env=dict(__import__('os').environ, GIT_CONFIG_NOSYSTEM='1')
    def git(*args):
        subprocess.run(['git','-C',str(root),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    git('init'); git('config','user.name','Fixture'); git('config','user.email','fixture@example.invalid')
    git('config','commit.gpgsign','false'); git('config','core.autocrlf','false'); git('add','.')
    git('commit','-m','Synthetic layout harness with verified upstream excerpts')
    return root,package

def fixture_preflight(root, package):
    return {'head':'fixture', 'baseline_regression':{'tests_run':6,'failures':0,'errors':0,'returncode':0,'skipped':[]},
            'baseline_receipt_sha256':digest((root/layout.PREVIOUS_RUN/'regression.json').read_bytes())}
