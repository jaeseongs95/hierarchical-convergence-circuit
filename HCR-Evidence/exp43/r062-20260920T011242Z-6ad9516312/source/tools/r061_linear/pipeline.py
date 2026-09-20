"""Frozen source, explicit validation, one research pass, isolated audit."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, fingerprint, load, publish, relative, require, safe, seal, sha
from tools.r050_review_boundary.pipeline import git, protected_files, verify_current_releases

SPEC = 'experiments/exp-42-local-linearization/frozen_spec.json'
PARENT_COMMIT = '5fcdbb3f44cfe14628a65971b3fe916b0169536d'
SPEC_FINGERPRINT = 'fe7f830c4322d9d23496ec5f7f254a18ceb2eaaf950a22a8fcdb3240b4a63f01'
PINS = {
    'R060': '18ef5aa87c92f7e1ccbbb41947b4edb6b3e8e763f074b0b2556c4b6367598131',
    'R059': '97787e71999adba7ef6c174e077bac281029ed8eafe9e236615cb89ccccfd45f',
    'R058': '0a6d3e288786495afb8a74dc67a28d4d8940eb44242270eabeee29cde49902cf',
    'R057': 'd9255890b1c931d3ce165c46346ce4214705d0a4ac4db466f6cc7cd8dc3deb6a',
    'R056': 'a8ad2d4764c4d144af3971abe723d48bbf82e362cf8312543fa2b65835d61764',
    'R055': 'f873feb80782eb26ff8adaad01d4a2baf846f4bae8317600ae8d8c61d599befa',
    'R050': 'cbd6f138bc8f2318ae5546c0efffe0ce7b4a17bfaab4a0feebbcf7bd33e6d92a',
    'R051': 'e705066ade1d954c936aa582ed44a4b0d9a8d776d76fb06e61bee102788088df',
    'R052': '7afe672c30263c87c5d5ca10a17016de8a6ecba4f7894a8a8d61b9eb8accbbba',
    'R053': '3247d77ca829d76ea39ff0f210e8a8ad8e7bd50d1636cb717ea739a81ab66aeb',
    'R054': '88e9f9dae6facc64f424e244cdd5e1001dcabb7460fece81f87b520a5c4c39d3',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_spec(spec):
    require(fingerprint(spec) == SPEC_FINGERPRINT, 'Exact predeclared R061 matrix/spec required')


def source_inventory(root):
    names = set(protected_files(root)) | {'experiments/INDEX.json'}
    verify_current_releases(root)
    for version in (*PINS, 'R061'):
        name = version+'_MANIFEST.json'
        raw = relative(root, name).read_bytes()
        if version in PINS:
            require(sha(raw.replace(b'\r\n', b'\n')) == PINS[version], 'Historical manifest changed: '+name)
        manifest = load(root/name)
        expected_schema = ('hcc-r050-candidate-release-v1' if version == 'R050'
                           else 'hcc-'+version.lower()+'-manifest-v1')
        require(manifest['schema'] == expected_schema, 'Manifest schema')
        for path, digest in manifest['files'].items():
            require(sha(relative(root, path).read_bytes().replace(b'\r\n', b'\n')) == digest,
                    'Source drift: '+path)
        names.update(manifest['files'])
        names.add(name)
    return {name: sha(relative(root, name).read_bytes()) for name in sorted(names)}


def freeze(root, out, purpose):
    hashes = source_inventory(root)
    for name, digest in hashes.items():
        raw = relative(root, name).read_bytes()
        require(sha(raw) == digest, 'Concurrent source change')
        publish(out/'source'/name, raw)
    dump(out/'source_manifest.json', dict(schema='hcc-r061-source-manifest-v1',
        files=files(out/'source'), parent_commit=PARENT_COMMIT, checkout_commit=git(root, 'rev-parse', 'HEAD')))
    spec = load(out/'source'/SPEC)
    validate_spec(spec)
    for folder, prefix in (('parents', 'parent'), ('anchors', 'anchor')):
        for name, digest in spec[prefix+'_files'].items():
            raw = relative(relative(root, spec[prefix+'_directory']), name).read_bytes()
            require(sha(raw) == digest, 'Pinned evidence bytes changed: '+name)
            publish(out/folder/name, raw)
    from hcr.codec import plain
    from hcr.model import Config
    parent = load(out/'parents/plan.json')
    config = parent['config']['kernel']
    require(config == plain(Config()), 'Default kernel config')
    dump(out/'plan.json', seal(dict(schema='hcc-r061-plan-v1', purpose=purpose, spec=spec,
        config=config, source_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),
        created_at_utc=now(), automatic_retry=False)))


def stage(root, out, name, module, arguments, source=None):
    source = source or out/'source'
    command = [sys.executable, '-X', 'utf8', '-B', str(out/'source/tools/r061_linear/bootstrap.py'),
               '--source', str(source), '--module', module, '--', *map(str, arguments)]
    log = out/'validation'/(name+'.log')
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join([str(source/'src'), str(source)]))
    print('STAGE:', name, flush=True)
    start = now()
    with log.open('xb') as stream:
        result = subprocess.run(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
    dump(out/'validation'/(name+'.receipt.json'), dict(command=command, returncode=result.returncode,
        started_at=start, finished_at=now(), automatic_retry=False))
    require(result.returncode == 0, f'{name} failed; first failure retained: {log}')


def kernel_and_audit(root, out, prefix):
    spec = load(out/'plan.json')['spec']
    for folder, key in (('parents', 'parent'), ('anchors', 'anchor')):
        require(files(out/folder) == spec[key+'_files'], 'Evidence bytes changed after freeze: '+folder)
    stage(root, out, prefix+'-worker', 'tools.r061_linear.worker', ['--run', out])
    purpose = load(out/'plan.json')['purpose']
    dump(out/'raw_manifest.json', dict(schema='hcc-r061-raw-manifest-v1',
        files=files(out/('study' if purpose == 'research' else 'smoke'))))
    stage(root, out, prefix+'-audit', 'tools.r061_linear.audit', ['--run', out])


def execute(root, validate_only=False):
    require(sys.version_info >= (3, 12), 'Python 3.12+ required')
    purpose = 'implementation_validation' if validate_only else 'research'
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out = safe(root/'HCR-Evidence'/('r061-validation' if validate_only else 'exp42')/('r061-'+identity))
    out.mkdir(parents=True, exist_ok=False)
    phase = 'freeze'
    try:
        freeze(root, out, purpose)
        phase = 'selftest'
        stage(root, out, '01-selftest', 'tools.r061_linear.selftest',
              ['--source', out/'source', '--output', out/'validation/selftest.json'])
        phase = 'kernel_smoke'
        if validate_only:
            kernel_and_audit(root, out, '02-smoke')
        else:
            smoke = out/'validation/kernel-smoke'
            smoke.mkdir()
            freeze(root, smoke, 'implementation_validation')
            kernel_and_audit(root, smoke, '02-smoke')
        phase = 'final_core_regression'
        stage(root, out, '03-core-regression', 'tools.r050_review_boundary.regression',
              ['--repo', root, '--output', out/'validation/core_regression.json'], source=root)
        require(source_inventory(root) == load(out/'source_manifest.json')['files'],
                'Source changed after freeze')
        if not validate_only:
            phase = 'research_and_audit'
            kernel_and_audit(root, out, '04-research')
        dump(out/'result.json', dict(status='SOURCE_VALIDATED' if validate_only else
            'EXECUTED_AND_INDEPENDENTLY_VERIFIED', purpose=purpose,
            research_experiment_executed=not validate_only, native_outcomes_measured=False,
            core_regression_runs=1, hypothesis_success_required=False, completed_at=now()))
        phase = 'bundle'
        dump(out/'bundle_manifest.json', dict(schema='hcc-r061-bundle-manifest-v1', files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'), 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(out.rglob('*')):
                if path.is_file():
                    bundle.write(path, arcname=out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:', out, flush=True)
        return out
    except BaseException as exc:
        failure = out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure, dict(stage=phase, exception=type(exc).__name__, message=str(exc),
            traceback=traceback.format_exc(), automatic_retry=False, partial_evidence_retained=True))
        print('FAILED EVIDENCE:', out, file=sys.stderr, flush=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    execute(safe(args.repo), args.validate_only)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
