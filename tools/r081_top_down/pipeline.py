"""Freeze, self-test, execute four cells once, independently audit and seal."""
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r080_small_positive.pipeline import inventory as previous_inventory
from tools.r066_facts.pipeline import stage as previous_stage
from time import perf_counter

SPEC = 'experiments/exp-62-top-down/frozen_spec.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def stage(root, out, name, module, args, source=None):
    started_at=now(); started=perf_counter()
    try:
        previous_stage(root,out,name,module,args,source)
    finally:
        dump(out/'validation'/f'{name}.timing.json',dict(started_at=started_at,finished_at=now(),
            monotonic_duration_seconds=perf_counter()-started,clock='perf_counter',automatic_retry=False))


def inventory(root):
    result = previous_inventory(root)
    for name,digest in load(root/'R081_MANIFEST.json')['files'].items():
        raw = relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R081 source drift: '+name)
        result[name]=sha(raw)
    result['R081_MANIFEST.json']=sha((root/'R081_MANIFEST.json').read_bytes())
    return result


def main(resume=None, review_dir=None, writer_id=None, reviewer_id=None):
    root=Path(__file__).resolve().parents[2]
    require(sys.version_info >= (3,12),'Existing Python 3.12+ required')
    from tools.r081_top_down.review_gate import completed, check_source
    require(writer_id and reviewer_id and writer_id != reviewer_id, 'Distinct writer/reviewer IDs required')
    if resume is None:
        identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
        out=root/'HCR-Evidence/exp62'/('r081-'+identity)
        out.mkdir(parents=True,exist_ok=False);(out/'validation').mkdir()
    else:
        out=Path(resume).resolve()
        require(out.parent == (root/'HCR-Evidence/exp62').resolve(), 'Resume must name an R081 run')
        require(not (out/'failure.json').exists() and not (out/'bundle_manifest.json').exists(), 'Failed/sealed run cannot resume')
    phase='freeze'
    timing=dict(invocation_started_at=now(),native_started_at=None,native_finished_at=None)
    try:
        if resume is None:
            freeze(root,out)
            dump(out/'review_policy.json',dict(writer_id=writer_id,reviewer_id=reviewer_id))
        else:
            require(load(out/'review_policy.json') == dict(writer_id=writer_id,reviewer_id=reviewer_id), 'Frozen review identities changed')
        check_source(out)
        source=load(out/'source_manifest.json')['files'];plan=load(out/'plan.json')
        require(inventory(root)==source, 'Checkout source changed; do not resume')
        parent=relative(root,plan['parent_run']);parent_files=load(out/'input_manifest.json')['files']
        repeat=relative(root,plan['reproduction_run']);repeat_files=load(out/'repeat_manifest.json')['files']
        phase='selftest-and-parent-grounding'
        if resume is None:
            stage(root,out,phase,'tools.r081_top_down.audit',['--out',out,'--phase','selftest'])
        phase='native-evaluation'
        attempt=len(list((out/'validation').glob('native-evaluation-*.receipt.json')))
        args=['--out',out,'--writer-id',writer_id,'--reviewer-id',reviewer_id]
        if review_dir is not None: args += ['--review-dir',Path(review_dir).resolve()]
        stage(root,out,phase+'-'+str(attempt),'tools.r081_top_down.worker',args)
        if not completed(out,review_dir,writer_id,reviewer_id):
            print('PAUSED: external review required; resume this same run:',out,flush=True)
            return
        cell_times=[load(out/'evaluation'/c['id']/'native_timing.json') for c in plan['cells']]
        timing.update(run_started_at=load(out/'source_manifest.json')['recorded_at'],
                      native_started_at=cell_times[0]['started_at'],native_finished_at=cell_times[-1]['finished_at'],
                      native_duration_seconds=sum(t['duration_seconds'] for t in cell_times),
                      external_review_wait_excluded_from_native_duration=True)
        dump(out/'raw_manifest.json',dict(files=files(out/'evaluation')))
        phase='independent-analysis'
        stage(root,out,phase,'tools.r081_top_down.audit',['--out',out,'--phase','final'])
        phase='summary-verification'
        stage(root,out,phase,'tools.r081_top_down.verify',['--out',out])
        phase='final-core-regression'
        stage(root,out,phase,'tools.r050_review_boundary.regression',['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity'
        require(inventory(root)==source and files(out/'source')==source,'Frozen source changed')
        require(files(parent)==parent_files and files(out/'parent')==parent_files,'R077 original/copied evidence changed')
        require(files(out/'repeat')==repeat_files and all(sha(relative(repeat,n).read_bytes())==d for n,d in repeat_files.items()),'R080 original/copied evidence changed')
        require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw changed')
        timing['run_verified_at']=now();dump(out/'timing.json',timing)
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',native_training_executions=0,
            native_evaluation_executions=4,reproduction_executions=2,new_signal_intervention_executions=2,
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


def freeze(root,out):
    source=inventory(root);plan=load(root/SPEC)
    subprocess.run(['git','merge-base','--is-ancestor',plan['baseline_commit'],'HEAD'],cwd=root,check=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
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
    require(sha((repeat/'bundle_manifest.json').read_bytes())==plan['reproduction_bundle_manifest_sha256'],'R080 seal')
    repeat_files={name:seal[name] for name in ['plan.json',*['evaluation/'+c['reproduction_id']+'/inference.json' for c in plan['cells'] if c['evidence_role']=='reproduction']]}
    repeat_files['bundle_manifest.json']=plan['reproduction_bundle_manifest_sha256']
    for name,digest in repeat_files.items():
        raw=relative(repeat,name).read_bytes();require(sha(raw)==digest,'R080 selected input drift')
        publish(relative(out/'repeat',name),raw)
    dump(out/'repeat_manifest.json',dict(files=repeat_files,parent_run=plan['reproduction_run'],selection='sealed plan and two raw journals; historical bundle not rewritten'))
    dump(out/'plan.json',plan)


if __name__=='__main__':
    raise SystemExit('Use Run-HCR-R081.py with explicit review identities')
