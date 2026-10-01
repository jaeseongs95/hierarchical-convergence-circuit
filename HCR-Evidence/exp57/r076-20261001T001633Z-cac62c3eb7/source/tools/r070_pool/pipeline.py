"""Freeze and reanalyze once; preserve failures and historical inputs."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from tools.r050_review_boundary.common import dump, files, load, publish, relative, require, sha
from tools.r069_revision.pipeline import inventory as previous_inventory
from tools.r065_information.pipeline import input_inventory
from tools.r066_facts.pipeline import stage

SPEC='experiments/exp-51-pool-signal-boundary/frozen_spec.json'


def inventory(root):
    result=previous_inventory(root)
    for name,digest in load(root/'R070_MANIFEST.json')['files'].items():
        raw=relative(root,name).read_bytes()
        require(sha(raw.replace(b'\r\n',b'\n'))==digest,'R070 source drift: '+name)
        result[name]=sha(raw)
    result['R070_MANIFEST.json']=sha((root/'R070_MANIFEST.json').read_bytes())
    return result


def main():
    root=Path(__file__).resolve().parents[2]
    require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    out=root/'HCR-Evidence/exp51'/('r070-'+identity);out.mkdir(parents=True,exist_ok=False)
    (out/'validation').mkdir();phase='freeze'
    try:
        source=inventory(root);spec=load(root/SPEC);parent=relative(root,spec['parent_run'])
        dump(out/'plan.json',spec);dump(out/'input_manifest.json',input_inventory(root,spec))
        for name in spec['input_files']:
            publish(relative(out/'parent',name),relative(parent,name).read_bytes())
        for name,digest in source.items():
            raw=relative(root,name).read_bytes();require(sha(raw)==digest,'Concurrent source drift')
            publish(relative(out/'source',name),raw)
        dump(out/'source_manifest.json',dict(files=source,checkout_commit=subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=root,text=True).strip()))
        for name,module,args in [('selftest','tools.r070_pool.analyze',['--selftest']),
            ('formula-reanalysis','tools.r070_pool.analyze',[]),('independent-verification','tools.r070_pool.verify',[])]:
            phase=name;stage(root,out,name,module,['--out',out,*args])
        phase='final-core-regression';stage(root,out,phase,'tools.r050_review_boundary.regression',
            ['--repo',root,'--output',out/'validation/core_regression.json'],source=root)
        phase='final-integrity';require(inventory(root)==source,'Source changed after freeze')
        require(files(out/'source')==source,'Frozen source coverage')
        require(files(out/'parent')=={n:sha(relative(parent,n).read_bytes()) for n in spec['input_files']},'Copied input coverage')
        require(input_inventory(root,spec)==load(out/'input_manifest.json'),'Original parent integrity')
        dump(out/'result.json',dict(status='REANALYZED_AND_VERIFIED',reanalysis=True,
            new_native_research_executions=0,new_independent_samples=0,core_regression_runs=1,
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
