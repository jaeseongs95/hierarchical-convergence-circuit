"""Read-only delivery, source, raw, archive and preexisting-file checks."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'HCR-Evidence/exp48/r067-20260920T063020Z-db2c8e7392'
VALIDATION=ROOT/'HCR-Evidence/r067-validation'


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest=load(RUN/'bundle_manifest.json')['files']
    assert {p.relative_to(RUN).as_posix():digest(p) for p in RUN.rglob('*')
        if p.is_file() and p!=RUN/'bundle_manifest.json'}==manifest
    with zipfile.ZipFile(RUN.with_suffix('.zip')) as z:
        expected={RUN.name+'/'+n for n in [*manifest,'bundle_manifest.json']}
        assert set(z.namelist())==expected and len(z.namelist())==len(expected)
        for name in z.namelist():assert z.read(name)==(RUN/name.split('/',1)[1]).read_bytes()
    source=load(RUN/'source_manifest.json')['files']
    for name,h in source.items():
        assert digest(RUN/'source'/name)==h
        assert (ROOT/name).read_bytes().replace(b'\r\n',b'\n')==(RUN/'source'/name).read_bytes().replace(b'\r\n',b'\n')
    plan=load(RUN/'plan.json')
    for name,h in plan['parent_files'].items():assert digest(ROOT/plan['parent_run']/name)==digest(RUN/'parent'/name)==h
    for folder,manifest_name in [('evaluation','raw_manifest.json'),('measurements','measurement_manifest.json')]:
        assert {p.relative_to(RUN/folder).as_posix():digest(p) for p in (RUN/folder).rglob('*') if p.is_file()}==load(RUN/manifest_name)['files']
    v=load(RUN/'verification.json');assert v['verified'] and v['native_formula_replays']==24 and len(v['rejected_mutations'])==16
    assert len(load(RUN/'validation/selftest.json')['passed'])==11
    summary=load(RUN/'summary.json');assert len(summary['rows'])==12
    assert all(x[phase]['measures']['accepted'] for x in summary['rows'] for phase in ('before','after'))
    assert all(x[phase]['native_cost']['observation_requests']==0 for x in summary['rows'] for phase in ('before','after'))
    report=load(RUN/'validation/core_regression.json')
    assert report['verified'] and report['tests_run']==602 and report['passed']==599
    assert len(report['environment_skips'])==3 and not report['new_skips'] and report['final_core_runs']==1
    assert not (RUN/'failure.json').exists()
    for p in (RUN/'validation').glob('*.receipt.json'):assert load(p)['returncode']==0
    raw=gzip.decompress((VALIDATION/'baseline.json.gz').read_bytes());baseline=json.loads(raw);artifact=load(VALIDATION/'baseline-artifact.json')
    assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and baseline['manifestSha256']==artifact['manifestSha256']
    included=load(VALIDATION/'task-contract.json')['report']['taskEnvelope']['scope']['included']
    def allowed(name):return any(name==p or (p.endswith('/') and name.startswith(p)) for p in included)
    unchanged=0;preparation=0
    for entry in baseline['entries']:
        if entry['path'] in ('experiments/INDEX.json','experiments/INDEX.ko.md'):continue
        assert entry['kind']=='file',entry
        assert digest(ROOT/entry['path'])==entry['sha256'],entry['path']
        if allowed(entry['path']):preparation+=1
        else:unchanged+=1
    staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    assert all(allowed(name) and not name.endswith('.zip') for name in staged if name)
    p=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/run_indexed_experiment.py'),'--check-index'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    assert p.returncode==0,p.stderr
    assert load(RUN/'result.json')['status']=='EXECUTED_AND_VERIFIED'
    return dict(verified=True,bundle_files=len(manifest),source_files=len(source),zip_exact=True,
        pinned_parent_files=len(plan['parent_files']),native_evaluations=24,paired_conditions=12,
        synthetic_checks=11,rejected_mutations=16,core_passed=599,existing_skips=3,final_core_runs=1,
        baseline_out_of_scope_files_unchanged=unchanged,baseline_preparation_files_unchanged=preparation,
        staged_paths_in_scope=True,index_stdout=p.stdout.strip(),predictions=summary['predictions'],
        autonomous_native_observation_requests=0,independent_researcher=False)


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
