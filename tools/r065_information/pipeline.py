"""Freeze, validate, reanalyze, independently verify and bundle without native research."""
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha

SPEC = 'experiments/exp-46-information-boundary/frozen_spec.json'


def source_inventory(root):
    manifest = load(root/'R065_MANIFEST.json'); result = {}
    for name, digest in manifest['files'].items():
        raw = relative(root, name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n')) == digest, 'R065 source drift: '+name)
        result[name] = sha(raw)
    result['R065_MANIFEST.json'] = sha((root/'R065_MANIFEST.json').read_bytes())
    return result


def input_inventory(root, spec):
    parent = relative(root, spec['parent_run'])
    for name, digest in spec['parent_manifests'].items():
        require(sha(relative(parent,name).read_bytes()) == digest, 'Pinned parent manifest: '+name)
    bundle = load(parent/'bundle_manifest.json')['files']
    actual = files(parent); actual.pop('bundle_manifest.json')
    require(actual == bundle, 'Parent bundle exact coverage and hashes')
    source = load(parent/'source_manifest.json')['files']
    require(files(parent/'source') == source, 'Parent source inventory')
    # Replay imports current src and upstream audit helpers. Bind all of them to the sealed parent source.
    dependencies = {n:d for n,d in source.items() if n.startswith(('src/','tools/'))}
    for name in dependencies:
        require(relative(root,name).read_bytes().replace(b'\r\n',b'\n') == relative(parent/'source',name).read_bytes().replace(b'\r\n',b'\n'), 'Replay dependency drift: '+name)
    return dict(parent_run=spec['parent_run'], parent_manifests=spec['parent_manifests'],
                verified_parent_files=len(bundle), replay_dependency_files=len(dependencies),
                new_native_research_executions=0, new_independent_samples=0)


def stage(root, out, name, script, args=()):
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join([str(root/'src'),str(root)]))
    command = [sys.executable,'-X','utf8','-B',str(script),*map(str,args)]
    print('STAGE:',name,flush=True)
    with (out/'validation'/f'{name}.log').open('xb') as f:
        result = subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
    dump(out/'validation'/f'{name}.receipt.json', dict(command=command,returncode=result.returncode,automatic_retry=False))
    require(result.returncode == 0, 'Stage failed; evidence preserved: '+name)


def main():
    root = Path(__file__).resolve().parents[2]
    require(sys.version_info >= (3,12), 'Existing Python 3.12+ required')
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out = root/'HCR-Evidence/exp46'/('r065-'+identity); out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir(); phase = 'freeze'
    try:
        inventory = source_inventory(root); spec = load(root/SPEC)
        dump(out/'spec.json',spec)
        for name in inventory: publish(relative(out/'source',name),relative(root,name).read_bytes())
        dump(out/'source_manifest.json',dict(files=inventory,checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        dump(out/'input_manifest.json',input_inventory(root,spec))
        args = ['--repo',root,'--out',out]
        phase = 'selftest'; stage(root,out,'selftest',out/'source/tools/r065_information/analyze.py',[*args,'--selftest'])
        phase = 'reanalyze'; stage(root,out,'reanalyze',out/'source/tools/r065_information/analyze.py',args)
        phase = 'independent-verification'; stage(root,out,'independent-verification',out/'source/tools/r065_information/verify.py',args)
        phase = 'final-core-regression'
        # Module execution retains the existing suite and its three environment skips.
        stage(root,out,'core-regression',root/'Run-HCR-R065.py',['--core-regression',out/'validation/core_regression.json'])
        phase = 'final-integrity'
        require(source_inventory(root) == inventory, 'Source changed during analysis')
        require(input_inventory(root,spec) == load(out/'input_manifest.json'), 'Input changed during analysis')
        dump(out/'result.json',dict(status='REANALYZED_AND_VERIFIED',reanalysis=True,new_native_research_executions=0,
            new_independent_samples=0,core_regression_runs=1,actual_energy_joules=None,peak_memory_bytes=None))
        dump(out/'bundle_manifest.json',dict(files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(out.rglob('*')):
                if path.is_file(): z.write(path,out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
    except BaseException:
        dump(out/'failure.json',dict(stage=phase,traceback=traceback.format_exc(),automatic_retry=False))
        print('FAILED EVIDENCE:',out,flush=True); raise


if __name__ == '__main__': main()
