"""Verify bytes and independently recompute delivered research summaries."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'HCR-Evidence/exp44/r063-20260920T020204Z-07096ed58b'


def load(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {f.relative_to(p).as_posix():digest(f) for f in p.rglob('*') if f.is_file()}


bundle=load(RUN/'bundle_manifest.json')['files'];actual=inventory(RUN)
assert actual.pop('bundle_manifest.json')==digest(RUN/'bundle_manifest.json')
assert actual==bundle
with zipfile.ZipFile(RUN.with_suffix('.zip')) as z:
    expected=dict(bundle,**{'bundle_manifest.json':digest(RUN/'bundle_manifest.json')})
    assert z.testzip() is None and len(z.namelist())==len(expected)
    assert {n[len(RUN.name)+1:]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}==expected
assert inventory(RUN/'source')==load(RUN/'source_manifest.json')['files']
raw=load(RUN/'raw_manifest.json')
assert all(inventory(RUN/key)==value for key,value in raw.items())
plan=load(RUN/'plan.json');summary=load(RUN/'summary.json')
assert summary['verified'] and len(summary['training'])==3 and len(summary['rows'])==12
assert len(list((RUN/'training').glob('*/inference.json')))==3
assert len(list((RUN/'evaluation').glob('*/inference.json')))==12
formation=[]
for i in (1,2,3):
    where=RUN/'training'/f'{i:02d}';record=load(where/'inference.json');ref=load(where/'reference.json');learning=load(where/'learning.json')
    after=load(RUN/'memory'/f'{i}.json')
    assert record['memory_before']==load(RUN/'memory'/f'{i-1}.json')
    assert learning['memory_after']==after
    assert learning['feedback']==ref['feedback']
    if learning['packet'] is not None:
        doc=learning['packet']['document'];finished=record['execution']['candidate']['packet']['document']
        assert doc['transitions'][:-1]==finished['transitions'] and doc['events'][:-2]==finished['events']
        assert doc['engine']['memory']==after and doc['events'][-1]['payload']['patch']==learning['patch']
    observed=dict(episode=i,memory_version=after['version'],circuits=len(after['circuits']),
        pending=[dict(length=len(p['pattern']['relations']),evidence_count=len(p['evidence_episodes'])) for p in after['pending']],
        compiled_lengths=[len(c['pattern']['relations']) for c in after['circuits']],
        strengths=[c['strength'] for c in after['circuits']],
        feedback_correct=None if ref['feedback'] is None else ref['feedback']['correct'])
    formation.append(observed)
rows=[]
for p in sorted((RUN/'evaluation').glob('*/inference.json')):
    r=load(p);e=r['execution'];c=e['candidate'];pending=e['packet']['document']['engine']['pending'];events=e['packet']['document']['events']
    s=next(row for row in summary['rows'] if row['identity']==r['identity'])
    assert pending['observation']==next(case for case in plan['cases'] if case['id']==r['case_id'])['observation']
    assert r['memory_before']==load(RUN/'memory'/f"{r['memory_count']}.json")==e['packet']['document']['engine']['memory']
    assert s['measures']['numeric_state']==(dict(pending['state']) or None)
    if c is not None:
        assert s['measures']['raw_decision']==c['decision']['value']
        assert s['measures']['proof_valid']==c['decision']['proof']['under_assumptions_valid']
        assert s['measures']['support_gap_count']==len(c['diagnostic']['support_gap_edges'])
        assert s['measures']['accepted']==c['readout']['accepted']
        assert s['measures']['adopted_value']==(c['decision']['value'] if c['readout']['accepted'] else None)
    kinds={ev['payload']['network_id']:ev['payload']['kind'] for ev in events if ev['event']=='r02_network'}
    ticks={kind:sum(ev['event']=='r02_tick' and kinds[ev['payload']['network_id']]==kind for ev in events if ev['event']=='r02_tick') for kind in ['pool','decision']}
    reuses=sum(ev['event']=='r02_expansion' and ev['payload']['candidate']['source']=='circuit' for ev in events)
    # Native expansions count both application and frontier retirement.
    expansions=sum(ev['event'] in ('r02_expansion','r02_dead_end') for ev in events)
    assert ticks==s['network_ticks'] and sum(ticks.values())==s['cost']['kernel_ticks']
    assert reuses==s['cost']['circuit_reuses'] and expansions==s['cost']['expansions']
    rows.append(dict(identity=r['identity'],case=r['case_id'],memory=r['memory_count'],gate=r['use_circuits'],
        expansions=expansions,reuses=reuses,**ticks,kernel_ticks=sum(ticks.values()),
        adopted=s['measures']['adopted_value'],accepted=s['measures']['accepted'],raw=s['measures']['raw_decision'],
        gaps=s['measures']['support_gap_count'],D_DAG=s['measures']['D_DAG'],binding_checks=s['cost']['binding_checks']))
core=load(RUN/'validation/core_regression.json')
assert core['verified'] and core['tests_run']==602 and core['passed']==599 and len(core['environment_skips'])==3 and not core['new_skips']
assert load(RUN/'result.json')['core_regression_runs']==1
smoke=load(RUN/'validation/native-smoke/summary.json')
assert len(smoke['training'])==3 and len(smoke['rows'])==8 and all(len(r['rejected_mutations'])==7 for r in smoke['rows'])
assert not list(RUN.rglob('failure.json'))
report=dict(verified=True,run=RUN.relative_to(ROOT).as_posix(),bundle_files=len(bundle),zip_sha256=digest(RUN.with_suffix('.zip')),
    source_manifest_sha256=digest(RUN/'source_manifest.json'),formation=formation,rows=rows,pairs=summary['pairs'],
    research_training=3,research_evaluation=12,synthetic_training=3,synthetic_evaluation=8,rejected_mutations=56,
    core_tests=602,core_passes=599,preexisting_skips=3,core_regression_runs=1)
with (Path(__file__).parent/'delivery-verification.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
