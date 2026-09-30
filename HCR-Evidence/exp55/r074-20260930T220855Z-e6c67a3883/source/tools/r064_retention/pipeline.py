"""One frozen research pass with separate native/reference processes."""
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
from tools.r063_formation.pipeline import inventory as previous_inventory
from tools.r061_linear.pipeline import git, now

SPEC='experiments/exp-45-error-retention/frozen_spec.json'
from .contract import SPEC_FINGERPRINT
PARENT='04a9f9d834647fc025bebc83adb086fe67108b25'


def inventory(root):
    result=previous_inventory(root)
    manifest=load(root/'R064_MANIFEST.json')
    require(manifest['schema']=='hcc-r064-manifest-v1','Manifest schema')
    for name,digest in manifest['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'Source drift: '+name)
        result[name]=sha(raw)
    result['R064_MANIFEST.json']=sha((root/'R064_MANIFEST.json').read_bytes())
    return dict(sorted(result.items()))


def freeze(root,out,purpose):
    hashes=inventory(root)
    for name,digest in hashes.items():
        raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
        publish(out/'source'/name,raw)
    dump(out/'source_manifest.json',dict(schema='hcc-r064-source-v1',files=hashes,parent_commit=PARENT,checkout_commit=git(root,'rev-parse','HEAD')))
    spec=load(out/'source'/SPEC);require(fingerprint(spec)==SPEC_FINGERPRINT,'Exact frozen spec')
    for name,digest in spec['parent_files'].items():
        raw=relative(root/spec['parent_run'],name).read_bytes();require(sha(raw)==digest,'Pinned parent drift')
        publish(out/'parent'/name,raw)
    dump(out/'memory/before.json',load(out/'parent/memory/3.json'))
    matrix=spec[purpose]
    dump(out/'plan.json',seal(dict(schema='hcc-r064-plan-v1',purpose='research' if purpose=='research' else 'implementation_validation',
        matrix=purpose,spec=spec,**matrix,config=spec['config'],limits=spec['limits'],
        source_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),created_at_utc=now(),automatic_retry=False)))



def stage(root,out,name,module,arguments,source=None):
    source=source or out/'source'
    command=[sys.executable,'-X','utf8','-B',str(out/'source/tools/r064_retention/bootstrap.py'),
        '--source',str(source),'--module',module,'--',*map(str,arguments)]
    log=out/'validation'/(name+'.log');log.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(source/'src'),str(source)]))
    print('STAGE:',name,flush=True);start=now()
    with log.open('xb') as f:result=subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
    dump(out/'validation'/(name+'.receipt.json'),dict(command=command,returncode=result.returncode,started_at=start,finished_at=now(),automatic_retry=False))
    require(result.returncode==0,f'{name} failed; first failure retained: {log}')


def study(root,out):
    phases=[('initial','worker'),('initial','audit'),('feedback','worker'),('measurements','audit'),
            ('revision','worker'),('revision','audit'),('final-feedback','worker'),('eval','worker')]
    for i,(phase,module) in enumerate(phases):
        stage(root,out,f'{i:02d}-{module}-{phase}','tools.r064_retention.'+module,['--run',out,'--phase',phase])
    dump(out/'raw_manifest.json',{name:files(out/name) for name in ('initial','revision','memory','evaluation','parent')})
    stage(root,out,'08-independent-audit','tools.r064_retention.audit',['--run',out])



def execute(root,validate_only=False):
    require(sys.version_info>=(3,12),'Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    purpose='implementation_validation' if validate_only else 'research'
    out=safe(root/'HCR-Evidence'/('r064-validation' if validate_only else 'exp45')/('r064-'+identity))
    out.mkdir(parents=True,exist_ok=False);phase='freeze'
    try:
        freeze(root,out,'smoke_request' if validate_only else 'research')
        phase='synthetic_integration_and_mutation_checks'
        if validate_only:
            study(root,out)
        else:
            for matrix in ('smoke_request','smoke_no_request'):
                smoke=out/'validation'/matrix;smoke.mkdir(parents=True)
                freeze(root,smoke,matrix);study(root,smoke)
        if not validate_only:
            phase='final_core_regression'
            stage(root,out,'core-regression','tools.r050_review_boundary.regression',['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
            require(inventory(root)==load(out/'source_manifest.json')['files'],'Source changed after freeze')
            phase='research_and_audit';study(root,out)
        dump(out/'result.json',dict(status='SYNTHETIC_VALIDATED' if validate_only else 'EXECUTED_AND_INDEPENDENTLY_VERIFIED',
            purpose=purpose,research_experiment_executed=not validate_only,core_regression_runs=0 if validate_only else 1,
            hypothesis_success_required=False,completed_at=now()))
        phase='bundle';dump(out/'bundle_manifest.json',dict(schema='hcc-r064-bundle-v1',files=files(out)))
        with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob('*')):
                if p.is_file():z.write(p,arcname=out.name+'/'+p.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True);return out
    except BaseException as exc:
        path=out/'failure.json' if not (out/'bundle_manifest.json').exists() else out.with_suffix('.failure.json')
        dump(path,dict(stage=phase,exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),automatic_retry=False,partial_evidence_retained=True))
        print('FAILED EVIDENCE:',out,file=sys.stderr,flush=True);raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--validate-only',action='store_true');args=parser.parse_args();execute(safe(args.repo),args.validate_only)


if __name__=='__main__':main()
