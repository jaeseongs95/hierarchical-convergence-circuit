"""Read-only evidence checks, with a new exclusive verification receipt."""
from pathlib import Path
import json
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'HCR-Evidence/exp43/r062-20260920T011305Z-1a61ac35ea'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


manifest = load(RUN/'bundle_manifest.json')['files']
actual = {p.relative_to(RUN).as_posix():digest(p) for p in RUN.rglob('*') if p.is_file()
          and p != RUN/'bundle_manifest.json'}
assert manifest == actual
with zipfile.ZipFile(RUN.with_suffix('.zip')) as z:
    assert z.testzip() is None
    expected = dict(manifest, **{'bundle_manifest.json':digest(RUN/'bundle_manifest.json')})
    assert len(z.namelist()) == len(expected)
    assert {p[len(RUN.name)+1:]:hashlib.sha256(z.read(p)).hexdigest() for p in z.namelist()} == expected
for folder, name in [('source','source_manifest.json'),('variants/drop_P_prefix','variant_manifest.json')]:
    wanted = load(RUN/name)['files']
    assert {p.relative_to(RUN/folder).as_posix():digest(p) for p in (RUN/folder).rglob('*') if p.is_file()} == wanted
assert load(RUN/'result.json')['core_regression_runs'] == 1
core = load(RUN/'validation/core_regression.json')
summary = load(RUN/'summary.json')
assert summary['verified'] is True and len(summary['rows']) == 4
raw = list((RUN/'raw').glob('*/*/execution.json'))
assert len(raw) == 4
rows = []
for p in raw:
    r = load(p); e = r['execution']; c = e['candidate']; pending = e['packet']['document']['engine']['pending']
    row = next(x for x in summary['rows'] if x['case']==r['case_id'] and x['arm']==r['arm'])
    m = row['measures']
    assert m['numeric_state'] == dict(pending['state'])
    assert m['raw_decision'] == c['decision']['value']
    assert m['proof_valid'] == c['decision']['proof']['under_assumptions_valid']
    assert m['support_gap_count'] == len(c['diagnostic']['support_gap_edges'])
    assert m['accepted'] == c['readout']['accepted']
    assert m['adopted_value'] == (c['decision']['value'] if c['readout']['accepted'] else None)
    assert row['r054_full_trajectory_matches'] is True
    assert pending['cost']['kernel_ticks'] == len([x for x in e['packet']['document']['events'] if x['event']=='r02_tick'])
    rows.append(dict(case=r['case_id'],arm=r['arm'],goal=m['numeric_state']['goal'],raw=m['raw_decision'],
        support_gaps=m['support_gap_count'],adopted=m['adopted_value'],ticks=pending['cost']['kernel_ticks']))
smoke = load(RUN/'validation/native-smoke/summary.json')
assert len(smoke['rows']) == 4
assert all(len(r['rejected_mutations']) == 8 for r in smoke['rows'])
first = ROOT/'HCR-Evidence/exp43/r062-20260920T011242Z-6ad9516312'
assert load(first/'failure.json')['stage'] == 'synthetic_smoke_and_mutation_checks'
assert not (first/'raw').exists()
report = dict(verified=True,run=RUN.relative_to(ROOT).as_posix(),bundle_files=len(manifest),
    bundle_sha256=digest(RUN/'bundle_manifest.json'),zip_sha256=digest(RUN.with_suffix('.zip')),
    core_regression=core,rows=rows,synthetic_executions=4,rejected_mutations=32,
    prior_pre_research_failure_preserved=True,prior_failure_research_execution_count=0)
with (Path(__file__).parent/'delivery-verification.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
