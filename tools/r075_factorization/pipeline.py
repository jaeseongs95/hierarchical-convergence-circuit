"""Freeze, evaluate once, verify separately, regress once, and preserve all bytes."""
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
from tools.r074_sensitivity.pipeline import inventory as previous_inventory

SPEC='experiments/exp-56-drive-factorization/frozen_spec.json'


def inventory(root):
    result=previous_inventory(root)
    for name,digest in load(root/'R075_MANIFEST.json')['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R075 source drift: '+name)
        result[name]=sha(raw)
    result['R075_MANIFEST.json']=sha((root/'R075_MANIFEST.json').read_bytes())
    return result


def anchor_integrity(root,spec):
    return input_inventory(root,dict(parent_run=spec['anchor_run'],parent_manifests=spec['anchor_manifests']))


def main():
    root=Path(__file__).resolve().parents[2];require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp56'/('r075-'+identity);out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir();phase='freeze'
    try:
        source=inventory(root);spec=load(root/SPEC);parent=relative(root,spec['parent_run'])
        inputs=dict(parent=input_inventory(root,spec),anchor=anchor_integrity(root,spec));dump(out/'plan.json',spec)
        for key,original in [('parent',parent),('anchor',relative(root,spec['anchor_run']))]:
            for name,digest in spec[key+'_files'].items():
                raw=relative(original,name).read_bytes();require(sha(raw)==digest,'Pinned input: '+name)
                publish(relative(out/key,name),raw)
        dump(out/'input_manifest.json',dict(files={k:files(out/k) for k in ('parent','anchor')},integrity=inputs))
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        dump(out/'source_manifest.json',dict(files=source,checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        phase='selftest';stage(root,out,phase,'tools.r075_factorization.audit',['--out',out,'--phase','selftest'])
        phase='formula-replay';stage(root,out,phase,'tools.r075_factorization.replay',['--out',out])
        dump(out/'raw_manifest.json',dict(files=files(out/'replays')))
        phase='analysis';stage(root,out,phase,'tools.r075_factorization.audit',['--out',out,'--phase','final'])
        phase='independent-verification';stage(root,out,phase,'tools.r075_factorization.verify',['--out',out])
        phase='final-core-regression';stage(root,out,phase,'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity';require(inventory(root)==source and files(out/'source')==source,'Frozen source changed')
        require(dict(parent=input_inventory(root,spec),anchor=anchor_integrity(root,spec))==inputs,'Original input drift')
        for key in ('parent','anchor'):require(files(out/key)==spec[key+'_files'],'Copied input drift')
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',formula_replay_cells=12,prior_replay_correspondences=6,mixed_scale_cells=6,
            new_native_research_executions=0,new_training_executions=0,new_feedback_applications=0,
            new_independent_samples=0,core_regression_runs=1,hypothesis_success_required=False,
            actual_energy_joules=None,peak_memory_bytes=None))
        dump(out/'bundle_manifest.json',dict(files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob('*')):
                if p.is_file():z.write(p,out.name+'/'+p.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
    except BaseException:
        failure=out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(failure,dict(stage=phase,traceback=traceback.format_exc(),automatic_retry=False))
        print('FAILED EVIDENCE:',out,flush=True);raise


if __name__=='__main__':main()
