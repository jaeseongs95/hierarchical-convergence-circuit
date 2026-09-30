"""Read-only source/parent/bundle/ZIP/index delivery checks; no native rerun."""
from pathlib import Path
import json
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import dump, files, load, relative, require, sha
from tools.r069_revision.pipeline import inventory


def main():
    run=ROOT/'HCR-Evidence/exp50/r069-20260930T120436Z-4ac297ded8'
    source=load(run/'source_manifest.json')['files']
    require(inventory(ROOT)==source,'Current source matches executed frozen source')
    require(files(run/'source')==source,'Frozen source coverage')
    plan=load(run/'plan.json');parent=relative(ROOT,plan['parent_run'])
    require(files(run/'parent')==plan['parent_files'],'Copied parent coverage')
    for name,digest in plan['parent_files'].items():
        require(sha(relative(parent,name).read_bytes())==digest,'Original parent unchanged')
    bundle=load(run/'bundle_manifest.json')['files']
    actual=files(run);del actual['bundle_manifest.json']
    require(actual==bundle,'Sealed bundle coverage')
    with zipfile.ZipFile(run.with_suffix('.zip')) as archive:
        names=[run.name+'/'+name for name in files(run)]
        require(sorted(archive.namelist())==sorted(names),'ZIP exact coverage')
        require(len(archive.namelist())==len(set(archive.namelist())),'No ZIP duplicates')
        for name,digest in files(run).items():
            require(sha(archive.read(run.name+'/'+name))==digest,'ZIP byte match '+name)
    index=load(ROOT/'experiments/INDEX.json')
    row=next(x for x in index['experiments'] if x['experiment_id']=='EXP-50')
    require(index['default_experiment']=='EXP-30' and row['standalone_python_entrypoint']=='Run-HCR-R069.py',
            'Standalone registration preserves default')
    for key in ('standalone_python_entrypoint','design','frozen_design','release_manifest'):
        require(relative(ROOT,row[key]).is_file(),'Index path '+key)
    core=load(run/'validation/core_regression.json')
    require(core['verified'] and core['tests_run']==602 and core['passed']==599 and core['final_core_runs']==1,
            '602 core checks with preserved 3 skips')
    require(load(run/'verification.json')['verified'] and load(run/'result.json')['status']=='EXECUTED_AND_VERIFIED',
            'Executed verification')
    dump(ROOT/'HCR-Evidence/r069-validation/delivery-verification.json',dict(verified=True,
        run=run.relative_to(ROOT).as_posix(),source_files=len(source),bundle_files=len(bundle),
        source_current_matches=True,parent_unchanged=True,zip_byte_match=True,index_paths_verified=True,
        core_tests=602,core_passed=599,environment_skips=3,core_regression_runs=1,
        default_experiment='EXP-30',release_sha256=sha((ROOT/'R069_MANIFEST.json').read_bytes()),
        no_native_rerun=True,no_historical_reseal=True,guarded_mcp_completion=False))
    print('Delivery verified: source, parent, bundle, ZIP, index and one core regression.')


if __name__=='__main__':main()
