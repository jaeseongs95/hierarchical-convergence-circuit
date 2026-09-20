"""Freeze explicit source variants; smoke, regression once, research once, audit."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, fingerprint, load, publish, relative, require, safe, seal, sha
from tools.r061_linear.pipeline import source_inventory as historical_inventory, git, now
from tools.r062_native.variants import PATCHES, patched

SPEC = 'experiments/exp-43-native-feedback/frozen_spec.json'
SPEC_FINGERPRINT = 'f316841018e8de5de17aef98d35498a56ccb60b887389543b414ba852598c3b7'
PARENT_COMMIT = '46efbdab1b92b6294d6d8e337beca91bb53b5746'


def source_inventory(root):
    result = historical_inventory(root)
    manifest = load(root/'R062_MANIFEST.json')
    require(manifest['schema'] == 'hcc-r062-manifest-v1', 'R062 manifest schema')
    for name, digest in manifest['files'].items():
        raw = relative(root, name).read_bytes()
        require(sha(raw.replace(b'\r\n', b'\n')) == digest, 'R062 source drift: '+name)
        result[name] = sha(raw)
    result['R062_MANIFEST.json'] = sha((root/'R062_MANIFEST.json').read_bytes())
    return dict(sorted(result.items()))


def freeze(root, out, purpose):
    hashes = source_inventory(root)
    for name, digest in hashes.items():
        raw = relative(root, name).read_bytes()
        require(sha(raw) == digest, 'Concurrent source change')
        publish(out/'source'/name, raw)
    dump(out/'source_manifest.json', dict(schema='hcc-r062-source-manifest-v1',
        files=hashes, parent_commit=PARENT_COMMIT, checkout_commit=git(root, 'rev-parse', 'HEAD')))
    spec = load(out/'source'/SPEC)
    require(fingerprint(spec) == SPEC_FINGERPRINT, 'Exact predeclared spec')
    require(spec['source_patch_preimages'] == {p:hashes[p] for p in PATCHES}, 'Source patch preimage pins')
    changed = {}
    for name, digest in hashes.items():
        raw = (out/'source'/name).read_bytes()
        if name in PATCHES:
            raw = patched(name, raw)
            changed[name] = dict(before=digest, after=sha(raw), before_text=PATCHES[name][0], after_text=PATCHES[name][1])
        publish(out/'variants/drop_P_prefix'/name, raw)
    dump(out/'variant_manifest.json', dict(schema='hcc-r062-variant-v1',
        files=files(out/'variants/drop_P_prefix'), changed=changed,
        base_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),
        authored_before_execution=True, post_state_correction=False))
    require(set(changed) == set(PATCHES), 'Exactly two isolated source edits')
    for folder, prefix in (('parents','parent'),('anchors','anchor')):
        for name, digest in spec[prefix+'_files'].items():
            raw = relative(relative(root, spec[prefix+'_directory']), name).read_bytes()
            require(sha(raw) == digest, 'Parent evidence changed: '+name)
            # Source files retain their original names in spec; map explicit aliases.
            destination = spec[prefix+'_aliases'][name]
            publish(out/folder/destination, raw)
    # Plan uses hashes of the copied aliases, while immutable spec retains original provenance.
    parent = load(out/'parents/plan.json')
    cases = deepcopy(spec['cases'] if purpose == 'research' else spec['smoke_cases'])
    dump(out/'plan.json', seal(dict(schema='hcc-r062-plan-v1', purpose=purpose, spec=spec,
        cases=cases, config=parent['config'], empty_memory=parent['empty_memory'], limits=parent['limits'],
        source_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),
        variant_manifest_sha256=sha((out/'variant_manifest.json').read_bytes()),
        created_at_utc=now(), automatic_retry=False)))


def stage(root, out, name, module, arguments, source=None):
    import os
    import subprocess
    source = source or out/'source'
    command = [sys.executable, '-X','utf8','-B', str(out/'source/tools/r062_native/bootstrap.py'),
        '--source',str(source),'--module',module,'--',*map(str,arguments)]
    log = out/'validation'/(name+'.log')
    log.parent.mkdir(parents=True, exist_ok=True)
    print('STAGE:', name, flush=True)
    start = now()
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join([str(source/'src'),str(source)]))
    with log.open('xb') as stream:
        result = subprocess.run(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT)
    dump(out/'validation'/(name+'.receipt.json'),dict(command=command,returncode=result.returncode,
        started_at=start,finished_at=now(),automatic_retry=False))
    require(result.returncode==0, f'{name} failed; first failure retained: {log}')


def execute_pair(root, out):
    for arm in ('full','drop_P_prefix'):
        source = out/'source' if arm=='full' else out/'variants'/arm
        stage(root,out,arm+'-worker','tools.r062_native.worker',['--run',out,'--arm',arm],source)
        stage(root,out,arm+'-audit','tools.r062_native.audit',['--run',out,'--arm',arm],source)
    dump(out/'raw_manifest.json',dict(files=files(out/'raw')))
    rows = [row for arm in ('full','drop_P_prefix') for row in load(out/'audit'/(arm+'.json'))['rows']]
    dump(out/'summary.json',dict(verified=True,rows=rows,independent_samples=False,
        learned=False,actual_energy_joules=None,adoption_is_existing_candidate_readout=True))


def execute(root, validate_only=False):
    require(sys.version_info >= (3,12), 'Python 3.12+ required')
    purpose = 'implementation_validation' if validate_only else 'research'
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out = safe(root/'HCR-Evidence'/('r062-validation' if validate_only else 'exp43')/('r062-'+identity))
    out.mkdir(parents=True, exist_ok=False)
    phase = 'freeze'
    try:
        freeze(root,out,purpose)
        phase = 'synthetic_smoke_and_mutation_checks'
        smoke = out if validate_only else out/'validation/native-smoke'
        if not validate_only:
            smoke.mkdir(parents=True)
            freeze(root,smoke,'implementation_validation')
        execute_pair(root,smoke)
        if not validate_only:
            phase = 'final_core_regression'
            stage(root,out,'core-regression','tools.r050_review_boundary.regression',
                ['--repo',root,'--output',out/'validation/core_regression.json'],root)
            require(source_inventory(root)==load(out/'source_manifest.json')['files'], 'Source changed after freeze')
            phase = 'research_and_independent_audit'
            execute_pair(root,out)
        dump(out/'result.json',dict(status='SYNTHETIC_VALIDATED' if validate_only else 'EXECUTED_AND_INDEPENDENTLY_VERIFIED',
            purpose=purpose,research_experiment_executed=not validate_only,
            native_outcomes_measured=True,core_regression_runs=0 if validate_only else 1,
            hypothesis_success_required=False,completed_at=now()))
        phase = 'bundle'
        dump(out/'bundle_manifest.json',dict(schema='hcc-r062-bundle-manifest-v1',files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(out.rglob('*')):
                if path.is_file():
                    bundle.write(path,arcname=out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
        return out
    except BaseException as exc:
        failure = out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure,dict(stage=phase,exception=type(exc).__name__,message=str(exc),
            traceback=traceback.format_exc(),automatic_retry=False,partial_evidence_retained=True))
        print('FAILED EVIDENCE:',out,file=sys.stderr,flush=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--validate-only',action='store_true',help='Synthetic validation only; no research or core regression')
    args = parser.parse_args(argv)
    execute(safe(args.repo),args.validate_only)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
