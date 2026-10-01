"""One frozen refresh experiment; preserve all first failures without retry."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r066_facts.pipeline import inventory as previous_inventory, stage

SPEC='experiments/exp-48-observation-refresh/frozen_spec.json'


def inventory(root):
    result=previous_inventory(root)
    for name,digest in load(root/'R067_MANIFEST.json')['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R067 source drift: '+name)
        result[name]=sha(raw)
    result['R067_MANIFEST.json']=sha((root/'R067_MANIFEST.json').read_bytes())
    return result


def main():
    root=Path(__file__).resolve().parents[2]
    require(sys.version_info >= (3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp48'/('r067-'+identity);out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir();phase='freeze'
    try:
        source=inventory(root);spec=load(root/SPEC)
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        dump(out/'source_manifest.json',dict(files=source,checkout_commit=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        parent=relative(root,spec['parent_run'])
        for name,digest in spec['parent_files'].items():
            raw=relative(parent,name).read_bytes();require(sha(raw)==digest,'Parent drift: '+name)
            publish(relative(out/'parent',name),raw)
        dump(out/'input_manifest.json',dict(files=files(out/'parent'),parent_run=spec['parent_run']))
        dump(out/'plan.json',spec)
        phase='selftest';stage(root,out,phase,'tools.r067_refresh.selftest',['--out',out])
        phase='measurement-service';stage(root,out,phase,'tools.r067_refresh.measure',['--out',out])
        dump(out/'measurement_manifest.json',dict(files=files(out/'measurements')))
        phase='native-evaluation';stage(root,out,phase,'tools.r067_refresh.worker',['--out',out])
        dump(out/'raw_manifest.json',dict(files=files(out/'evaluation')))
        phase='independent-verification';stage(root,out,phase,'tools.r067_refresh.verify',['--out',out])
        phase='final-core-regression';stage(root,out,phase,'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity';require(inventory(root)==source,'Source changed after freeze')
        require(files(out/'parent')==spec['parent_files'],'Copied parent changed')
        for name,digest in spec['parent_files'].items():
            require(sha(relative(parent,name).read_bytes())==digest,'Original parent changed')
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',native_evaluations=24,new_learning_executions=0,
            independent_samples=False,core_regression_runs=1,hypothesis_success_required=False,
            actual_energy_joules=None,peak_memory_bytes=None))
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
