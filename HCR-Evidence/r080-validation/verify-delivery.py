"""Read-only byte/time/catalog verification after the one-click run."""
from datetime import datetime
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r050_review_boundary.common import files, load, require, sha


def verify(out):
    actual=files(out);bundle=load(out/'bundle_manifest.json')['files']
    require({k:v for k,v in actual.items() if k!='bundle_manifest.json'}==bundle,'Sealed bundle coverage')
    with zipfile.ZipFile(out.with_suffix('.zip')) as z:
        require(set(z.namelist())=={out.name+'/'+p for p in actual},'ZIP coverage')
        require(all(sha(z.read(out.name+'/'+p))==d for p,d in actual.items()),'ZIP exact bytes')
    source=load(out/'source_manifest.json')['files'];require(files(out/'source')==source,'Source snapshot')
    require(all(sha((ROOT/n).read_bytes())==d for n,d in source.items() if n!='experiments/INDEX.json'),'Current executable/design source exact')
    old=load(out/'source/experiments/INDEX.json');current=load(ROOT/'experiments/INDEX.json')
    if current!=old:
        require(dict(current,experiments=[e for e in current['experiments'] if e['experiment_id']!='EXP-61'])==old
            and len(current['experiments'])==len(old['experiments'])+1,'Only EXP61 catalog registration')
    plan=load(out/'plan.json')
    require(files(ROOT/plan['parent_run'])==files(out/'parent')==load(out/'input_manifest.json')['files'],'Historical R077 intact')
    repeats=load(out/'repeat_manifest.json')['files']
    require(files(out/'repeat')==repeats and all(sha((ROOT/plan['reproduction_run']/n).read_bytes())==d for n,d in repeats.items()),'Historical R079 selected bytes intact')
    reg=load(out/'validation/core_regression.json')
    require(reg['verified'] and reg['final_core_runs']==1 and reg['tests_run']==602 and reg['passed']==599
        and len(reg['environment_skips'])==3 and not reg['new_skips'],'Regression baseline')
    timing=load(out/'timing.json');freeze=load(ROOT/'HCR-Evidence/r080-validation/design-freeze.json')
    require(freeze['spec_sha256']==sha((out/'source/experiments/exp-61-small-positive/frozen_spec.json').read_bytes()),'Original design freeze hash')
    points=[freeze['recorded_at'],timing['freeze_completed_at'],timing['selftest_completed_at'],timing['native_started_at'],timing['native_finished_at'],timing['run_verified_at']]
    require(all(datetime.fromisoformat(a)<=datetime.fromisoformat(b) for a,b in zip(points,points[1:])),'Stage order with equal UTC permitted')
    stages=['selftest-and-parent-grounding','native-evaluation','independent-analysis','summary-verification','final-core-regression']
    for stage in stages:
        receipt=load(out/'validation'/f'{stage}.receipt.json');clock=load(out/'validation'/f'{stage}.timing.json')
        require(receipt['returncode']==0 and not receipt['automatic_retry'] and clock['monotonic_duration_seconds']>=0,'Stage receipt/monotonic duration')
    summary=load(out/'summary.json');verification=load(out/'verification.json');result=load(out/'result.json')
    require(result['native_evaluation_executions']==7 and summary['reproduction_executions']==2
        and summary['new_score_intervention_executions']==5 and summary['new_independent_samples']==0,'Execution/sample partition')
    require(len(summary['reproduction_checks'])==2 and verification['verified'],'Independent/endpoint replay')
    require(all(r['pool_metrics'] is None and not r['durations']['pending_cost_is_duration'] for r in summary['rows']),'Secondary definitions')
    return dict(verified=True,run=out.relative_to(ROOT).as_posix(),bundle_files=len(actual),source_files=len(source),
        raw_bundle_zip_exact=True,historical_inputs_intact=True,design_before_native=True,core_regression_runs=1,
        independent_raw_replays=7,reproduction_journals=2,
        raw_mutations_rejected=len(verification['rejected_raw_mutations']),
        summary_mutations_rejected=len(load(out/'validation/summary-verification.json')['rejected_summary_mutations']),
        zip_sha256=sha(out.with_suffix('.zip').read_bytes()))


if __name__=='__main__':
    import json
    print(json.dumps(verify(Path(sys.argv[1])),ensure_ascii=False))
