"""Freeze, validate, execute once, audit and package without automatic retry."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, safe, seal, sha
from tools.r050_review_boundary.pipeline import (git, protected_files,
    verify_current_releases, verify_addon)

PARENT_COMMIT = 'b1d4525039f94c22f8aa2233aa6d6db616d9282c'
PARENT_MANIFEST_SHA256 = 'cbd6f138bc8f2318ae5546c0efffe0ce7b4a17bfaab4a0feebbcf7bd33e6d92a'
R051_MANIFEST_SHA256 = 'e705066ade1d954c936aa582ed44a4b0d9a8d776d76fb06e61bee102788088df'


def now():
    return datetime.now(timezone.utc).isoformat()


def verify_previous_source(root):
    raw = (root/'R051_MANIFEST.json').read_bytes().replace(b'\r\n', b'\n')
    require(sha(raw) == R051_MANIFEST_SHA256, 'Protected R051 manifest differs')
    previous = load(root/'R051_MANIFEST.json')
    for name, digest in previous['files'].items():
        require(sha(relative(root,name).read_bytes().replace(b'\r\n', b'\n')) == digest,
                'Protected R051 source drift: '+name)
    return dict(manifest_sha256=R051_MANIFEST_SHA256, files_verified=len(previous['files']))


def freeze(root, out, purpose):
    native = protected_files(root)
    releases = verify_current_releases(root)
    previous = verify_previous_source(root)
    parent = verify_addon(root)
    require(sha((root/'R050_MANIFEST.json').read_bytes().replace(b'\r\n',b'\n')) ==
            PARENT_MANIFEST_SHA256, 'Pinned R050 dependency manifest differs')
    addon = load(root/'R052_MANIFEST.json')
    require(addon['schema'] == 'hcc-r052-manifest-v1', 'R052 manifest schema')
    for name, digest in addon['files'].items():
        require(sha(relative(root,name).read_bytes().replace(b'\r\n',b'\n')) == digest,
                'R052 source drift: '+name)
    names = set(native) | set(parent['files']) | set(addon['files']) | {
        'R050_MANIFEST.json', 'R051_MANIFEST.json', 'R052_MANIFEST.json', 'experiments/INDEX.json'}
    hashes = {name:sha((root/name).read_bytes()) for name in names}
    for name in sorted(names):
        raw = (root/name).read_bytes()
        require(sha(raw) == hashes[name], 'Concurrent source change')
        publish(out/'source'/name, raw)
    dump(out/'source_manifest.json', dict(schema='hcc-r052-source-manifest-v1',
        files=files(out/'source'), parent_commit=PARENT_COMMIT, checkout_commit=git(root,'rev-parse','HEAD'),
        current_release_verification=releases, r051_preservation=previous))
    spec = load(out/'source/experiments/exp-33-array-roles/frozen_spec.json')
    from .audit import validate_spec
    from hcr import codec
    from hcr.model import AdaptiveConfig
    from hcr.circuits import AdaptiveMemory
    validate_spec(spec)
    require(spec['config'] == codec.plain(AdaptiveConfig()), 'Pinned default config')
    dump(out/'plan.json', seal(dict(schema='hcc-r052-plan-v1', purpose=purpose, spec=spec,
        config=spec['config'], limits=spec['limits'], empty_memory=AdaptiveMemory.empty(AdaptiveConfig()).document(),
        source_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),
        created_at_utc=now(), automatic_retry=False, source_changed_after_freeze=False)))


def stage(root, out, name, module, arguments, source=None):
    source = source or out/'source'
    launcher = out/'source/tools/r052_array_roles/bootstrap.py'
    command = [sys.executable, '-X', 'utf8', '-B', str(launcher), '--source', str(source),
               '--module', module, '--', *map(str, arguments)]
    log = out/'validation'/(name+'.log')
    log.parent.mkdir(parents=True, exist_ok=True)
    print('STAGE:', name, flush=True)
    started = now()
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join([str(source/'src'),str(source)]))
    with log.open('xb') as stream:
        result = subprocess.run(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
    dump(out/'validation'/(name+'.receipt.json'), dict(command=command, returncode=result.returncode,
        started_at=started, finished_at=now(), automatic_retry=False))
    require(result.returncode == 0, f'{name} failed; first failure retained: {log}')


def seal_raw(out, directory):
    dump(out/'raw_manifest.json', dict(schema='hcc-r052-raw-manifest-v1', files=files(out/directory)))


def execute(root, validate_only=False):
    require(sys.version_info >= (3,12), 'Python 3.12+ required')
    purpose = 'implementation_validation' if validate_only else 'research'
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out = safe(root/'HCR-Evidence'/('r052-validation' if validate_only else 'exp33')/('r052-'+identity))
    out.mkdir(parents=True, exist_ok=False)
    phase = 'freeze'
    try:
        freeze(root,out,purpose)
        source = out/'source'
        phase = 'unit_tests'
        stage(root,out,'01-selftest','tools.r052_array_roles.selftest',
              ['--source',source,'--output',out/'validation/selftest.json'])
        # A separate frozen validation run always precedes the research run.
        phase = 'native_smoke'
        if not validate_only:
            smoke = out/'validation/native-smoke'
            smoke.mkdir()
            freeze(root,smoke,'implementation_validation')
            stage(root,smoke,'02-smoke-worker','tools.r052_array_roles.worker',['--run',smoke])
            seal_raw(smoke,'smoke')
            stage(root,smoke,'03-smoke-audit','tools.r052_array_roles.audit',['--run',smoke])
        else:
            stage(root,out,'02-smoke-worker','tools.r052_array_roles.worker',['--run',out])
            seal_raw(out,'smoke')
            stage(root,out,'03-smoke-audit','tools.r052_array_roles.audit',['--run',out])
        phase = 'final_core_regression'
        # Legacy CLI tests also require repository-level hcr.py and configs.
        stage(root,out,'04-core-regression','tools.r050_review_boundary.regression',
              ['--repo',root,'--output',out/'validation/core_regression.json'], source=root)
        protected_files(root)
        verify_current_releases(root)
        verify_addon(root)
        verify_previous_source(root)
        frozen_addon = load(out/'source/R052_MANIFEST.json')
        require(load(root/'R052_MANIFEST.json') == frozen_addon, 'Concurrent R052 manifest change')
        for name, digest in frozen_addon['files'].items():
            require(sha(relative(root,name).read_bytes().replace(b'\r\n',b'\n')) == digest,
                    'Concurrent R052 source change: '+name)
        if not validate_only:
            phase = 'research'
            stage(root,out,'05-worker','tools.r052_array_roles.worker',['--run',out])
            seal_raw(out,'study')
            phase = 'independent_audit'
            stage(root,out,'06-audit','tools.r052_array_roles.audit',['--run',out])
        dump(out/'result.json',dict(status='SOURCE_VALIDATED' if validate_only else 'EXECUTED_AND_INDEPENDENTLY_VERIFIED',
            research_experiment_executed=not validate_only, purpose=purpose,
            core_regression_runs=1, hypothesis_success_required=False, completed_at=now()))
        phase = 'bundle'
        dump(out/'bundle_manifest.json', dict(schema='hcc-r052-bundle-manifest-v1', files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(out.rglob('*')):
                if path.is_file():
                    bundle.write(path,arcname=out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
        return out
    except BaseException as exc:
        failure = out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure,dict(stage=phase, exception=type(exc).__name__, message=str(exc),
            traceback=traceback.format_exc(), automatic_retry=False, partial_evidence_retained=True))
        print('FAILED EVIDENCE:',out,file=sys.stderr,flush=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--validate-only',action='store_true')
    args = parser.parse_args(argv)
    execute(safe(args.repo),args.validate_only)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
