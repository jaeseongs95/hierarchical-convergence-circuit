"""Explicit one-time harness repair validation; never repeat native research."""
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import dump, files, load, publish, require, sha
from tools.r066_facts.pipeline import inventory, stage


def main():
    run=ROOT/'HCR-Evidence/exp47/r066-20260920T060557Z-c4b48b19a6'
    out=ROOT/'HCR-Evidence/r066-validation/regression-recovery'
    out.mkdir(exist_ok=False);(out/'validation').mkdir()
    original=files(run);current=inventory(ROOT);old=load(run/'source_manifest.json')['files']
    changed={n for n in old if (ROOT/n).read_bytes().replace(b'\r\n',b'\n')!=(run/'source'/n).read_bytes().replace(b'\r\n',b'\n')}
    require(changed=={'R066_MANIFEST.json','tools/r066_facts/pipeline.py'},'Only harness and manifest repair allowed')
    require(load(run/'failure.json')['stage']=='final-core-regression','Expected first failure')
    require(load(run/'verification.json')['verified'],'Research was independently verified before harness failure')
    for name in sorted(changed):publish(out/'source'/name,(ROOT/name).read_bytes())
    dump(out/'plan.json',dict(original_run=run.relative_to(ROOT).as_posix(),original_files=original,
        changed_source={n:dict(before=old[n],after=current[n]) for n in sorted(changed)},
        reason='Root hcr.py shadowed src/hcr under module invocation; explicit sys.path bootstrap repairs import precedence.',
        repeat_native_evaluation=False,automatic_retry=False,python=sys.executable))
    stage(ROOT,out,'final-core-regression','tools.r050_review_boundary.regression',
        ['--repo',ROOT,'--output',out/'validation/core_regression.json'],source=ROOT)
    require(inventory(ROOT)==current and files(run)==original,'Source or original evidence changed during repair validation')
    dump(out/'result.json',dict(status='HARNESS_REPAIRED_AND_REGRESSION_VERIFIED',
        native_evaluations_total=60,additional_native_evaluations=0,first_failed_regression_preserved=True,
        regression_attempts_total=2,successful_final_regression_runs=1))
    # Seal the failed attempt exactly as it is, with its failure record retained.
    dump(out/'research_manifest.json',dict(files=original))
    with zipfile.ZipFile(run.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in original:z.write(run/name,run.name+'/'+name)
    dump(out/'bundle_manifest.json',dict(files=files(out)))
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():z.write(path,out.name+'/'+path.relative_to(out).as_posix())
    print('RECOVERY VERIFIED:',out)


if __name__=='__main__':main()
