"""Byte verification and independent raw summary recount; no runtime imports."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'HCR-Evidence/exp45/r064-20260920T024825Z-d995fcc733'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {f.relative_to(p).as_posix():digest(f) for f in p.rglob('*') if f.is_file()}

bundle=load(RUN/'bundle_manifest.json')['files'];actual=inventory(RUN)
assert actual.pop('bundle_manifest.json')==digest(RUN/'bundle_manifest.json') and actual==bundle
with zipfile.ZipFile(RUN.with_suffix('.zip')) as z:
    expected=dict(bundle,**{'bundle_manifest.json':digest(RUN/'bundle_manifest.json')})
    assert z.testzip() is None and len(z.namelist())==len(expected)
    assert {n[len(RUN.name)+1:]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}==expected
assert inventory(RUN/'source')==load(RUN/'source_manifest.json')['files']
assert all(inventory(RUN/key)==value for key,value in load(RUN/'raw_manifest.json').items())
plan=load(RUN/'plan.json');summary=load(RUN/'summary.json')
assert inventory(RUN/'parent')==plan['spec']['parent_files']
assert all(digest(ROOT/plan['spec']['parent_run']/name)==h for name,h in plan['spec']['parent_files'].items())
assert summary['verified'] and len(summary['rows'])==12
world=load(RUN/'source/experiments/exp-45-error-retention/reference_worlds.json')['research']

def recount(e,row):
    if e is None:
        assert row['cost'] is None and row['measures']['raw_decision'] is None
        return dict(executed=False)
    c=e['candidate'];p=e['packet']['document']['engine']['pending'];events=e['packet']['document']['events']
    starts=[i for i,ev in enumerate(events) if ev['event']=='r02_attempt_started']
    events=events[starts[-1]:]
    kinds={ev['payload']['network_id']:ev['payload']['kind'] for ev in events if ev['event']=='r02_network'}
    ticks={kind:sum(ev['event']=='r02_tick' and kinds[ev['payload']['network_id']]==kind for ev in events if ev['event']=='r02_tick') for kind in ('pool','decision')}
    reuses=sum(ev['event']=='r02_expansion' and ev['payload']['candidate']['source']=='circuit' for ev in events)
    expansions=sum(ev['event'] in ('r02_expansion','r02_dead_end') for ev in events)
    assert sum(ticks.values())==row['cost']['kernel_ticks']==p['cost']['kernel_ticks']
    assert reuses==row['cost']['circuit_reuses'] and expansions==row['cost']['expansions']
    obs=p['observation'];seen={obs['start']}
    while True:
        updated=seen|{edge['target'] for edge in obs['edges'] if edge['source'] in seen and world[edge['id']]}
        if updated==seen:break
        seen=updated
    truth=obs['goal'] in seen
    m=row['measures'];assert m['numeric_state']==(dict(p['state']) or None)
    if c is not None:
        raw=c['decision']['value'];adopted=raw if c['readout']['accepted'] else None
        assert m['raw_decision']==raw and m['adopted_value']==adopted
        assert m['raw_correct']==(None if raw is None else raw==truth)
        assert m['adopted_correct']==(None if not c['readout']['accepted'] else adopted==truth)
        assert m['support_gap_count']==len(c['diagnostic']['support_gap_edges'])
        assert m['proof_valid']==c['decision']['proof']['under_assumptions_valid']
    return dict(executed=True,actual_truth=truth,raw=m['raw_decision'],adopted=m['adopted_value'],correct=m['adopted_correct'],
        support_gaps=m['support_gap_count'],D_DAG=m['D_DAG'],reuses=reuses,expansions=expansions,**ticks,kernel_ticks=sum(ticks.values()))

initial=recount(load(RUN/'initial/inference.json')['execution'],summary['initial'])
arms={arm:recount(load(RUN/'revision'/arm/'inference.json')['execution'],row) for arm,row in summary['revision'].items()}
rows=[]
for row in summary['rows']:
    e=load(RUN/'evaluation'/row['identity']/'inference.json')['execution'];core=e['packet']['document']['engine']
    assert core['pending']['observation']==next(c['observation'] for c in plan['cases'] if c['id']==row['case'])
    assert core['memory']==load(RUN/'memory'/f"{row['snapshot']}.json")
    assert core['switches']['use_circuits'] is row['use_circuits']
    rows.append(dict(identity=row['identity'],**recount(e,row)))
assert len(list((RUN/'evaluation').glob('*/inference.json')))==12
memory=[]
for snapshot in plan['spec']['memory_snapshots']:
    m=load(RUN/'memory'/f'{snapshot}.json')
    assert m['circuits']==summary['circuit_snapshots'][snapshot]
    memory.append(dict(snapshot=snapshot,version=m['version'],circuits=m['circuits']))
assert load(RUN/'memory/before.json')==load(RUN/'parent/memory/3.json')
assert load(RUN/'initial/learning.json')['memory_after']==load(RUN/'memory/after_feedback.json')
assert load(RUN/'revision/corrected_observation/learning.json')['memory_after']==load(RUN/'memory/after_correction.json')
core=load(RUN/'validation/core_regression.json')
assert core['verified'] and core['tests_run']==602 and core['passed']==599 and len(core['environment_skips'])==3 and not core['new_skips']
assert load(RUN/'result.json')['core_regression_runs']==1
smokes=[]
for name in ('smoke_request','smoke_no_request'):
    s=load(RUN/'validation'/name/'summary.json')
    assert s['verified'] and not s['research'] and len(s['rows'])==6
    assert (s['request'] is not None)==(name=='smoke_request')
    assert all(len(row['rejected_mutations'])==7 for row in s['rows'])
    smokes.append(dict(name=name,adapt=s['adapt_executions'],frozen=s['frozen_executions'],rejected_mutations=42+len(s['synthetic_rejected_mutations'])))
assert not list(RUN.rglob('failure.json'))
report=dict(verified=True,run=RUN.relative_to(ROOT).as_posix(),bundle_files=len(bundle),zip_sha256=digest(RUN.with_suffix('.zip')),
    source_manifest_sha256=digest(RUN/'source_manifest.json'),initial=initial,revision=arms,rows=rows,memory=memory,predictions=summary['predictions'],
    research_adapt=1+sum(a['executed'] for a in arms.values()),research_frozen=12,synthetic=smokes,core_tests=602,core_passes=599,preexisting_skips=3,core_regression_runs=1)
with (Path(__file__).parent/'delivery-verification.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='memory'},ensure_ascii=False,indent=2))
