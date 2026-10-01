"""Freeze exact parent inputs, self-test, evaluate, audit, regress once and seal."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r065_information.pipeline import input_inventory
from tools.r066_facts.pipeline import stage
from tools.r071_boundary.pipeline import inventory as previous_inventory

SPEC='experiments/exp-53-selection-input-range/frozen_spec.json'


def inventory(root):
    result=previous_inventory(root)
    for name,digest in load(root/'R072_MANIFEST.json')['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R072 source drift: '+name)
        result[name]=sha(raw)
    result['R072_MANIFEST.json']=sha((root/'R072_MANIFEST.json').read_bytes())
    return result


def main():
    root=Path(__file__).resolve().parents[2];require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp53'/('r072-'+identity);out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir();phase='freeze'
    try:
        source=inventory(root);spec=load(root/SPEC);parent=relative(root,spec['parent_run'])
        input_report=input_inventory(root,spec)
        dump(out/'plan.json',spec)
        for name,digest in spec['parent_files'].items():
            raw=relative(parent,name).read_bytes();require(sha(raw)==digest,'Pinned parent input: '+name)
            publish(relative(out/'parent',name),raw)
        dump(out/'input_manifest.json',dict(files=files(out/'parent'),parent_integrity=input_report))
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        dump(out/'source_manifest.json',dict(files=source,checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        phase='selftest';stage(root,out,phase,'tools.r072_range.audit',['--out',out,'--phase','selftest','--parent',parent])
        phase='native-evaluation';stage(root,out,phase,'tools.r072_range.worker',['--out',out])
        dump(out/'raw_manifest.json',dict(files=files(out/'evaluation')))
        phase='independent-analysis';stage(root,out,phase,'tools.r072_range.audit',['--out',out,'--phase','final'])
        phase='independent-verification';stage(root,out,phase,'tools.r072_range.verify',['--out',out])
        phase='final-core-regression';stage(root,out,phase,'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity';require(inventory(root)==source,'Source changed after freeze')
        require(files(out/'source')==source,'Frozen source coverage')
        require(input_inventory(root,spec)==input_report,'Original parent integrity')
        require(files(out/'parent')==spec['parent_files'],'Copied parent bytes changed')
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',new_native_evaluation_executions=12,
            repeat_native_evaluations=4,new_score_native_evaluations=8,new_training_executions=0,
            new_feedback_applications=0,independent_discovery_samples=0,synthetic_native_executions=0,
            core_regression_runs=1,hypothesis_success_required=False,actual_energy_joules=None,peak_memory_bytes=None))
        dump(out/'bundle_manifest.json',dict(files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(out.rglob('*')):
                if path.is_file():z.write(path,out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
    except BaseException:
        failure=out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure,dict(stage=phase,traceback=traceback.format_exc(),automatic_retry=False))
        print('FAILED EVIDENCE:',out,flush=True);raise


if __name__=='__main__':main()
