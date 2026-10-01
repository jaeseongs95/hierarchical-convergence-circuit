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
from tools.r062_native.pipeline import source_inventory as previous_inventory
from tools.r061_linear.pipeline import git, now

SPEC='experiments/exp-44-circuit-formation/frozen_spec.json'
SPEC_FINGERPRINT='21a5ab149c43db7461e24ad59fae2a793217a09795071881a0ae31c29f4ea6c2'
PARENT='c59dbf1766df2226cc0085ef5c643f8aad2386e0'


def inventory(root):
    result=previous_inventory(root)
    manifest=load(root/'R063_MANIFEST.json')
    require(manifest['schema']=='hcc-r063-manifest-v1','Manifest schema')
    for name,digest in manifest['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'Source drift: '+name)
        result[name]=sha(raw)
    result['R063_MANIFEST.json']=sha((root/'R063_MANIFEST.json').read_bytes())
    return dict(sorted(result.items()))


def freeze(root,out,purpose):
    hashes=inventory(root)
    for name,digest in hashes.items():
        raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
        publish(out/'source'/name,raw)
    dump(out/'source_manifest.json',dict(schema='hcc-r063-source-v1',files=hashes,parent_commit=PARENT,checkout_commit=git(root,'rev-parse','HEAD')))
    spec=load(out/'source'/SPEC);require(fingerprint(spec)==SPEC_FINGERPRINT,'Exact frozen spec')
    from hcr.circuits import AdaptiveMemory
    from hcr import codec
    cfg=codec.adaptive_config_from(spec['config'])
    dump(out/'memory/0.json',AdaptiveMemory.empty(cfg).document())
    matrix=spec['research' if purpose=='research' else 'smoke']
    dump(out/'plan.json',seal(dict(schema='hcc-r063-plan-v1',purpose=purpose,spec=spec,**matrix,
        config=spec['config'],limits=spec['limits'],source_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),
        created_at_utc=now(),automatic_retry=False)))


def stage(root,out,name,module,arguments,source=None):
    source=source or out/'source'
    command=[sys.executable,'-X','utf8','-B',str(out/'source/tools/r063_formation/bootstrap.py'),
        '--source',str(source),'--module',module,'--',*map(str,arguments)]
    log=out/'validation'/(name+'.log');log.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(source/'src'),str(source)]))
    print('STAGE:',name,flush=True);start=now()
    with log.open('xb') as f:result=subprocess.run(command,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
    dump(out/'validation'/(name+'.receipt.json'),dict(command=command,returncode=result.returncode,started_at=start,finished_at=now(),automatic_retry=False))
    require(result.returncode==0,f'{name} failed; first failure retained: {log}')


def study(root,out):
    plan=load(out/'plan.json')
    for i in range(1,len(plan['training'])+1):
        for phase,module in [('train','worker'),('reference','audit'),('feedback','worker')]:
            arguments=['--run',out,'--episode',i]+([] if module=='audit' else ['--phase',phase])
            stage(root,out,f'{i:02d}-{phase}','tools.r063_formation.'+module,arguments)
    stage(root,out,'04-evaluation','tools.r063_formation.worker',['--run',out,'--phase','eval'])
    dump(out/'raw_manifest.json',dict(training=files(out/'training'),memory=files(out/'memory'),evaluation=files(out/'evaluation')))
    stage(root,out,'05-independent-audit','tools.r063_formation.audit',['--run',out])


def execute(root,validate_only=False):
    require(sys.version_info>=(3,12),'Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    purpose='implementation_validation' if validate_only else 'research'
    out=safe(root/'HCR-Evidence'/('r063-validation' if validate_only else 'exp44')/('r063-'+identity))
    out.mkdir(parents=True,exist_ok=False);phase='freeze'
    try:
        freeze(root,out,purpose)
        phase='synthetic_integration_and_mutation_checks'
        smoke=out if validate_only else out/'validation/native-smoke'
        if not validate_only:
            smoke.mkdir(parents=True);freeze(root,smoke,'implementation_validation')
        study(root,smoke)
        if not validate_only:
            phase='final_core_regression'
            stage(root,out,'core-regression','tools.r050_review_boundary.regression',['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
            require(inventory(root)==load(out/'source_manifest.json')['files'],'Source changed after freeze')
            phase='research_and_audit';study(root,out)
        dump(out/'result.json',dict(status='SYNTHETIC_VALIDATED' if validate_only else 'EXECUTED_AND_INDEPENDENTLY_VERIFIED',
            purpose=purpose,research_experiment_executed=not validate_only,core_regression_runs=0 if validate_only else 1,
            hypothesis_success_required=False,completed_at=now()))
        phase='bundle';dump(out/'bundle_manifest.json',dict(schema='hcc-r063-bundle-v1',files=files(out)))
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
