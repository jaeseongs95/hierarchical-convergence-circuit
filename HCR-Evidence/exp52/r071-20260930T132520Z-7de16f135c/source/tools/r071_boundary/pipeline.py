"""Freeze once, execute native recipe, audit separately, regress once and seal."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r070_pool.pipeline import inventory as previous_inventory
from tools.r065_information.pipeline import input_inventory
from tools.r066_facts.pipeline import stage

SPEC='experiments/exp-52-native-selection-boundary/frozen_spec.json'


def inventory(root):
    result=previous_inventory(root)
    for name,digest in load(root/'R071_MANIFEST.json')['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R071 source drift: '+name)
        result[name]=sha(raw)
    result['R071_MANIFEST.json']=sha((root/'R071_MANIFEST.json').read_bytes())
    return result


def main():
    root=Path(__file__).resolve().parents[2];require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp52'/('r071-'+identity);out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir();phase='freeze'
    try:
        source=inventory(root);spec=load(root/SPEC);parent=relative(root,spec['parent_run'])
        input_report=input_inventory(root,spec)
        dump(out/'plan.json',spec)
        for name in spec['input_files']:publish(relative(out/'parent',name),relative(parent,name).read_bytes())
        dump(out/'input_manifest.json',dict(files=files(out/'parent'),parent_integrity=input_report))
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        dump(out/'source_manifest.json',dict(files=source,checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        phase='preflight-selftest';stage(root,out,phase,'tools.r071_boundary.audit',['--out',out,'--phase','selftest'])
        for arm in spec['configs']:
            phase=arm+'-init';stage(root,out,phase,'tools.r071_boundary.worker',['--out',out,'--arm',arm,'--phase','init'])
            for step in range(1,len(spec['recipe'])+1):
                for operation,module in [('infer','worker'),('reference','audit'),('learn','worker')]:
                    phase=f'{arm}-{step}-{operation}'
                    stage(root,out,phase,'tools.r071_boundary.'+module,['--out',out,'--arm',arm,'--step',step,'--phase',operation])
            phase=arm+'-eval';stage(root,out,phase,'tools.r071_boundary.worker',['--out',out,'--arm',arm,'--phase','eval'])
        dump(out/'raw_manifest.json',dict(files=files(out/'arms')))
        dump(out/'evaluation_manifest.json',dict(files=files(out/'evaluation')))
        phase='independent-analysis';stage(root,out,phase,'tools.r071_boundary.audit',['--out',out,'--phase','final'])
        phase='independent-verification';stage(root,out,phase,'tools.r071_boundary.verify',['--out',out])
        phase='final-core-regression';stage(root,out,phase,'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity';require(inventory(root)==source,'Source changed after freeze')
        require(files(out/'source')==source,'Frozen source coverage')
        require(input_inventory(root,spec)==input_report,'Original parent integrity')
        require(files(out/'parent')==load(out/'input_manifest.json')['files'],'Copied parent integrity')
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',native_preparation_executions=10,
            native_evaluation_executions=4,feedback_applications=10,independent_discovery_samples=0,
            synthetic_native_executions=0,core_regression_runs=1,hypothesis_success_required=False,
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
