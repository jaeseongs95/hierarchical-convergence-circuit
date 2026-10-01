"""Freeze, self-test, execute twenty cells once, independently audit and seal."""
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r078_binding_order.pipeline import inventory as previous_inventory
from tools.r066_facts.pipeline import stage

SPEC = 'experiments/exp-60-score-readout/frozen_spec.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def inventory(root):
    result = previous_inventory(root)
    for name,digest in load(root/'R079_MANIFEST.json')['files'].items():
        raw = relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R079 source drift: '+name)
        result[name]=sha(raw)
    result['R079_MANIFEST.json']=sha((root/'R079_MANIFEST.json').read_bytes())
    return result


def main():
    root=Path(__file__).resolve().parents[2]
    require(sys.version_info >= (3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp60'/('r079-'+identity)
    out.mkdir(parents=True,exist_ok=False);(out/'validation').mkdir();phase='freeze'
    timing=dict(run_started_at=now(),native_started_at=None,native_finished_at=None)
    try:
        source=inventory(root);plan=load(root/SPEC)
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,
            env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).strip()
        dump(out/'source_manifest.json',dict(files=source,checkout_commit=commit,recorded_at=now()))
        parent=relative(root,plan['parent_run']);parent_files=dict(load(parent/'bundle_manifest.json')['files'])
        require(sha((parent/'bundle_manifest.json').read_bytes())==plan['parent_bundle_manifest_sha256'],'R077 seal')
        parent_files['bundle_manifest.json']=plan['parent_bundle_manifest_sha256']
        require(files(parent)==parent_files,'R077 sealed coverage')
        for name,digest in parent_files.items():
            raw=relative(parent,name).read_bytes();require(sha(raw)==digest,'R077 input drift')
            publish(relative(out/'parent',name),raw)
        dump(out/'input_manifest.json',dict(files=parent_files,parent_run=plan['parent_run']))
        repeat=relative(root,plan['reproduction_run']);seal=load(repeat/'bundle_manifest.json')['files']
        require(sha((repeat/'bundle_manifest.json').read_bytes())==plan['reproduction_bundle_manifest_sha256'],'R078 seal')
        repeat_files={name:seal[name] for name in ['plan.json',*['evaluation/'+c['id']+'/inference.json' for c in plan['cells'] if c['evidence_role']=='reproduction']]}
        repeat_files['bundle_manifest.json']=plan['reproduction_bundle_manifest_sha256']
        for name,digest in repeat_files.items():
            raw=relative(repeat,name).read_bytes();require(sha(raw)==digest,'R078 selected input drift')
            publish(relative(out/'repeat',name),raw)
        dump(out/'repeat_manifest.json',dict(files=repeat_files,parent_run=plan['reproduction_run'],selection='sealed plan and eight raw journals; historical bundle not rewritten'))
        dump(out/'plan.json',plan);timing['freeze_completed_at']=now()
        phase='selftest-and-parent-grounding'
        stage(root,out,phase,'tools.r079_score_readout.audit',['--out',out,'--phase','selftest'])
        timing['selftest_completed_at']=now();phase='native-evaluation';timing['native_started_at']=now()
        stage(root,out,phase,'tools.r079_score_readout.worker',['--out',out])
        timing['native_finished_at']=now();dump(out/'raw_manifest.json',dict(files=files(out/'evaluation')))
        phase='independent-analysis'
        stage(root,out,phase,'tools.r079_score_readout.audit',['--out',out,'--phase','final'])
        phase='summary-verification'
        stage(root,out,phase,'tools.r079_score_readout.verify',['--out',out])
        phase='final-core-regression'
        stage(root,out,phase,'tools.r050_review_boundary.regression',['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity'
        require(inventory(root)==source and files(out/'source')==source,'Frozen source changed')
        require(files(parent)==parent_files and files(out/'parent')==parent_files,'R077 original/copied evidence changed')
        require(files(out/'repeat')==repeat_files and all(sha(relative(repeat,n).read_bytes())==d for n,d in repeat_files.items()),'R078 original/copied evidence changed')
        require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw changed')
        timing['run_verified_at']=now();dump(out/'timing.json',timing)
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',native_training_executions=0,
            native_evaluation_executions=20,reproduction_executions=8,new_score_intervention_executions=12,
            feedback_applications=0,new_independent_samples=0,synthetic_native_executions=0,
            core_regression_runs=1,hypothesis_success_required=False,automatic_retry=False,
            actual_energy_joules=None,peak_memory_bytes=None))
        dump(out/'bundle_manifest.json',dict(files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(out.rglob('*')):
                if path.is_file():z.write(path,out.name+'/'+path.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
    except BaseException:
        failure=out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure,dict(stage=phase,traceback=traceback.format_exc(),timing=timing,automatic_retry=False))
        print('FAILED EVIDENCE:',out,flush=True);raise


if __name__=='__main__':main()
