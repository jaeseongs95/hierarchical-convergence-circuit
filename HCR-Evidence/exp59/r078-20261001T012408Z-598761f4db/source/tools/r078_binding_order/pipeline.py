"""Freeze once; reuse sealed R077 memory; evaluate, replay, regress once, seal."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r077_equal_binding.pipeline import inventory as previous_inventory
from tools.r066_facts.pipeline import stage

SPEC = 'experiments/exp-59-binding-order/frozen_spec.json'


def inventory(root):
    result = previous_inventory(root)
    for name, digest in load(root/'R078_MANIFEST.json')['files'].items():
        raw = relative(root, name).read_bytes()
        require(sha(raw.replace(b'\r\n', b'\n')) == digest, 'R078 source drift: '+name)
        result[name] = sha(raw)
    result['R078_MANIFEST.json'] = sha((root/'R078_MANIFEST.json').read_bytes())
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    require(sys.version_info >= (3,12), 'Existing Python 3.12+ required')
    identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out = root/'HCR-Evidence/exp59'/('r078-'+identity)
    out.mkdir(parents=True, exist_ok=False); (out/'validation').mkdir(); phase = 'freeze'
    try:
        source = inventory(root); spec = load(root/SPEC)
        for name, digest in source.items():
            raw = relative(root, name).read_bytes(); require(sha(raw) == digest, 'Concurrent source drift')
            publish(relative(out/'source', name), raw)
        dump(out/'source_manifest.json', dict(files=source,
            checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()))
        parent = relative(root, spec['parent_run'])
        require(sha((parent/'bundle_manifest.json').read_bytes()) == spec['parent_bundle_manifest_sha256'], 'R077 seal drift')
        parent_files = dict(load(parent/'bundle_manifest.json')['files'])
        parent_files['bundle_manifest.json'] = spec['parent_bundle_manifest_sha256']
        require(files(parent) == parent_files, 'R077 complete sealed coverage')
        for name, digest in parent_files.items():
            raw = relative(parent, name).read_bytes(); require(sha(raw) == digest, 'Parent drift: '+name)
            publish(relative(out/'parent', name), raw)
        dump(out/'input_manifest.json', dict(files=parent_files, parent_run=spec['parent_run']))
        dump(out/'plan.json', spec)
        phase = 'selftest-and-parent-grounding'
        stage(root, out, phase, 'tools.r078_binding_order.audit', ['--out',out,'--phase','selftest'])
        phase = 'native-evaluation'
        stage(root, out, phase, 'tools.r078_binding_order.worker', ['--out',out])
        dump(out/'raw_manifest.json', dict(files=files(out/'evaluation')))
        phase = 'independent-analysis'
        stage(root, out, phase, 'tools.r078_binding_order.audit', ['--out',out,'--phase','final'])
        phase = 'summary-verification'
        stage(root, out, phase, 'tools.r078_binding_order.verify', ['--out',out])
        phase = 'final-core-regression'
        stage(root, out, phase, 'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'], source=root)
        phase = 'final-integrity'
        require(inventory(root) == source and files(out/'source') == source, 'Frozen source changed')
        require(files(parent) == parent_files and files(out/'parent') == parent_files, 'R077 evidence changed')
        require(files(out/'evaluation') == load(out/'raw_manifest.json')['files'], 'Raw changed')
        dump(out/'result.json', dict(status='EXECUTED_AND_VERIFIED', native_training_executions=0,
            native_evaluation_executions=len(spec['cells']), feedback_applications=0,
            new_native_research_executions=len(spec['cells']), new_independent_samples=0,
            synthetic_native_executions=0, core_regression_runs=1, hypothesis_success_required=False,
            automatic_retry=False, actual_energy_joules=None, peak_memory_bytes=None))
        dump(out/'bundle_manifest.json', dict(files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'), 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(out.rglob('*')):
                if path.is_file(): z.write(path, out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:', out, flush=True)
    except BaseException:
        failure = out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure, dict(stage=phase, traceback=traceback.format_exc(), automatic_retry=False))
        print('FAILED EVIDENCE:', out, flush=True); raise


if __name__ == '__main__': main()
