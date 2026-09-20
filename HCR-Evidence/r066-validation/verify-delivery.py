"""Read-only artifact, baseline, source and index checks for the completed R066 run."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'HCR-Evidence/exp47/r066-20260920T060557Z-c4b48b19a6'
RECOVERY=ROOT/'HCR-Evidence/r066-validation/regression-recovery'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    bundle=load(RECOVERY/'research_manifest.json')['files']
    actual={p.relative_to(RUN).as_posix():digest(p) for p in RUN.rglob('*') if p.is_file()}
    assert actual==bundle
    with zipfile.ZipFile(RUN.with_suffix('.zip')) as z:
        names=[RUN.name+'/'+n for n in bundle]
        assert set(z.namelist())==set(names) and len(z.namelist())==len(names)
        for name in names:assert z.read(name)==(RUN/name.split('/',1)[1]).read_bytes()
    recovery_bundle=load(RECOVERY/'bundle_manifest.json')['files']
    assert {p.relative_to(RECOVERY).as_posix():digest(p) for p in RECOVERY.rglob('*')
        if p.is_file() and p.name!='bundle_manifest.json'}==recovery_bundle
    with zipfile.ZipFile(RECOVERY.with_suffix('.zip')) as z:
        names=[RECOVERY.name+'/'+n for n in [*recovery_bundle,'bundle_manifest.json']]
        assert set(z.namelist())==set(names) and len(z.namelist())==len(names)
        for name in names:assert z.read(name)==(RECOVERY/name.split('/',1)[1]).read_bytes()
    repair=load(RECOVERY/'plan.json')['changed_source']
    assert set(repair)=={'tools/r066_facts/pipeline.py','R066_MANIFEST.json'}
    source=load(RUN/'source_manifest.json')['files']
    for name,h in source.items():
        assert digest(RUN/'source'/name)==h
        if name in repair:
            assert repair[name]['before']==h and digest(RECOVERY/'source'/name)==repair[name]['after']
            expected=RECOVERY/'source'/name
        else:expected=RUN/'source'/name
        assert (ROOT/name).read_bytes().replace(b'\r\n',b'\n')==expected.read_bytes().replace(b'\r\n',b'\n')
    plan=load(RUN/'plan.json')
    for name,h in plan['parent_files'].items():assert digest(ROOT/plan['parent_run']/name)==h
    first=load(RUN/'validation/core_regression.json')
    assert not first['verified'] and len(first['errors'])==1 and first['tests_run']==579
    assert 'test_contracts_dynamics' in first['errors'][0]['test']
    assert load(RUN/'failure.json')['stage']=='final-core-regression'
    report=load(RECOVERY/'validation/core_regression.json')
    assert report['verified'] and report['tests_run']==602 and report['final_core_runs']==1
    assert report['passed']==599 and len(report['environment_skips'])==3 and not report['new_skips']
    v=load(RUN/'verification.json');assert v['verified'] and v['native_formula_replays']==60 and len(v['rejected_mutations'])==13
    assert len(load(RUN/'validation/selftest.json')['passed'])==10
    summary=load(RUN/'summary.json');assert len(summary['rows'])==60
    assert all(x['recording_only_same_native_measures'] and x['recording_only_same_native_cost'] for x in summary['comparisons'])
    baseline_dir=ROOT/'HCR-Evidence/r066-validation'
    raw=gzip.decompress((baseline_dir/'baseline.json.gz').read_bytes());artifact=load(baseline_dir/'baseline-artifact.json')
    assert hashlib.sha256(raw).hexdigest()==artifact['bytesSha256']
    baseline=json.loads(raw);assert baseline['manifestSha256']==artifact['manifestSha256']
    envelope=load(baseline_dir/'task-contract.json')['report']['taskEnvelope']
    included=envelope['scope']['included'];untouched=0
    def allowed(name):return any(name==p or (p.endswith('/') and name.startswith(p)) for p in included)
    for entry in baseline['entries']:
        if allowed(entry['path']):continue
        assert entry['kind']=='file',entry
        assert digest(ROOT/entry['path'])==entry['sha256'],entry['path'];untouched+=1
    staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    assert all(allowed(name) for name in staged if name)
    result=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/run_indexed_experiment.py'),'--check-index'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stderr
    return dict(verified=True,bundle_files=len(bundle),source_files=len(source),zip_exact=True,
        parent_pinned_files=len(plan['parent_files']),native_evaluations=60,synthetic_checks=10,rejected_mutations=13,
        core_passed=599,existing_skips=3,successful_final_core_runs=1,first_failed_regression_preserved=True,
        regression_attempts_total=2,recovery_bundle_files=len(recovery_bundle),prior_out_of_scope_files_unchanged=untouched,
        staged_paths_in_scope=True,index_stdout=result.stdout.strip(),predictions=summary['predictions'],
        independent_researcher=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
