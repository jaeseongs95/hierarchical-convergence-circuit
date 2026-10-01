"""Freeze once, form memory natively, evaluate, audit, regress once and seal."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r075_factorization.pipeline import inventory as previous_inventory
from tools.r066_facts.pipeline import stage

SPEC='experiments/exp-57-native-competition/frozen_spec.json'


def inventory(root):
    result=previous_inventory(root)
    for name,digest in load(root/'R076_MANIFEST.json')['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R076 source drift: '+name)
        result[name]=sha(raw)
    result['R076_MANIFEST.json']=sha((root/'R076_MANIFEST.json').read_bytes())
    return result


def main():
    root=Path(__file__).resolve().parents[2];require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp57'/('r076-'+identity);out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir();phase='freeze'
    try:
        source=inventory(root);spec=load(root/SPEC);dump(out/'plan.json',spec)
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        dump(out/'source_manifest.json',dict(files=source,
            checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        phase='selftest';stage(root,out,phase,'tools.r076_competition.audit',['--out',out,'--phase','selftest'])
        phase='init';stage(root,out,phase,'tools.r076_competition.worker',['--out',out,'--phase','init'])
        for step in range(1,len(spec['training'])+1):
            for operation,module in [('infer','worker'),('reference','audit'),('learn','worker')]:
                phase=f'train-{step}-{operation}'
                stage(root,out,phase,'tools.r076_competition.'+module,['--out',out,'--phase',operation,'--step',step])
        phase='native-evaluation';stage(root,out,phase,'tools.r076_competition.worker',['--out',out,'--phase','eval'])
        for folder,name in [('memory','memory_manifest.json'),('training','training_manifest.json'),('evaluation','raw_manifest.json')]:
            dump(out/name,dict(files=files(out/folder)))
        phase='independent-analysis';stage(root,out,phase,'tools.r076_competition.audit',['--out',out,'--phase','final'])
        phase='summary-verification';stage(root,out,phase,'tools.r076_competition.verify',['--out',out])
        phase='final-core-regression';stage(root,out,phase,'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity';require(inventory(root)==source and files(out/'source')==source,'Frozen source changed')
        for folder,name in [('memory','memory_manifest.json'),('training','training_manifest.json'),('evaluation','raw_manifest.json')]:
            require(files(out/folder)==load(out/name)['files'],'Raw input changed '+folder)
        dump(out/'result.json',dict(status='EXECUTED_AND_VERIFIED',native_training_executions=3,
            native_evaluation_executions=8,feedback_applications=load(out/'summary.json')['feedback_applications'],
            new_native_research_executions=11,new_independent_samples=0,synthetic_native_executions=0,
            core_regression_runs=1,hypothesis_success_required=False,automatic_retry=False,
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
