from pathlib import Path
import hashlib,json,zipfile,subprocess,math
root=Path.cwd(); runs=[p for p in (root/'HCR-Evidence/exp41').iterdir() if p.is_dir() and p.name.startswith('r060-')]
assert len(runs)==1
run=runs[0]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(folder):return {p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
result=load(run/'result.json');assert result['status']=='EXECUTED_AND_INDEPENDENTLY_VERIFIED'
bundle=load(run/'bundle_manifest.json')['files']; actual=hashes(run);del actual['bundle_manifest.json'];assert actual==bundle
source=load(run/'source_manifest.json')['files'];assert hashes(run/'source')==source
assert all(sha(root/n)==h for n,h in source.items())
with zipfile.ZipFile(run.with_suffix('.zip')) as z:
 assert z.testzip() is None
 expected={run.name+'/'+n:h for n,h in hashes(run).items()}
 assert len(z.namelist())==len(expected) and set(z.namelist())==set(expected)
 assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in expected.items())
 zip_count=len(expected)
selftest=load(run/'validation/selftest.json');core=load(run/'validation/core_regression.json');smoke=load(run/'validation/kernel-smoke/analysis/audit.json');audit=load(run/'analysis/audit.json')
assert selftest['verified'] and core['verified'] and smoke['verified'] and audit['verified']
assert selftest['tests_run']==18 and core['tests_run']==602 and core['passed']==599 and len(core['environment_skips'])==3
assert len(smoke['rows'])==8 and len(audit['rows'])==66
spec=load(run/'plan.json')['spec']; stats={};costs={k:0 for k in ['kernel_ticks','group_updates','normalization_ops','signal_transmissions']}
raw_hashes=hashes(run/'study');assert raw_hashes==load(run/'raw_manifest.json')['files']
assert set(raw_hashes)=={f"{c}/{a['id']}.json" for c in spec['conditions'] for a in spec['arms']}
for c in spec['conditions']:
 control=load(run/'study'/c/'control.json'); refs=[control['initial_state']]+[t['state'] for t in control['ticks']]
 rows=[]
 for arm in spec['arms']:
  raw=load(run/'study'/c/(arm['id']+'.json'));states=[raw['initial_state']]+[t['state'] for t in raw['ticks']]
  assert raw['initial_state']=={k:v+arm['deltas'][k] for k,v in raw['anchor_state'].items()}
  ds=[max(abs(a[k]-b[k]) for k in a) for a,b in zip(states,refs,strict=True)]
  row=next(r for r in audit['rows'] if r['condition']==c and r['arm']['id']==arm['id'])
  assert row['distance_by_tick']==ds and row['recovery_tail_max_distance']==max(ds[113:])
  assert row['recovered']==(all(d<=1e-8 for d in ds[113:]) if arm['id']!='control' else None)
  first=next((n for n in range(129) if all(d<=1e-8 for d in ds[n:])),None)
  if arm['id']!='control':assert row['first_tick_with_all_remaining_distances_within_tolerance']==first;rows.append(row)
  for k in costs:costs[k]+=raw['cost'][k]
 ticks=[r['first_tick_with_all_remaining_distances_within_tolerance'] for r in rows if r['recovered']]
 stats[c]=dict(perturbations=len(rows),recovered=sum(r['recovered'] for r in rows),bands_preserved=sum(r['band_preserved'] for r in rows),max_final_distance=max(r['final_distance'] for r in rows),max_tail_distance=max(r['recovery_tail_max_distance'] for r in rows),return_ticks=[min(ticks),max(ticks)] if ticks else None,max_amplification=max(r['max_amplification'] for r in rows),control_max_anchor_drift=max(abs(s[k]-control['anchor_state'][k]) for s in refs for k in s))
old=json.loads(subprocess.check_output(['git','show','b3fc168:experiments/INDEX.json']));new=load(root/'experiments/INDEX.json')
assert new['experiments'][:-1]==old['experiments']
assert {k:v for k,v in new.items() if k!='experiments'}=={k:v for k,v in old.items() if k!='experiments'}
report=dict(verified=True,run=run.relative_to(root).as_posix(),research_executions=1,rows=66,selftests=18,smoke_rows=8,anchor_replays=2,core_regression=dict(tests_run=602,passed=599,runs=1,skips=core['environment_skips']),source_files=len(source),bundle_hash_targets=len(bundle),zip_files=zip_count,source_and_bundle_unmodified=True,summary_recomputed_from_raw=True,previous_index_entries_preserved=True,statistics=stats,research_cost=costs)
p=root/'HCR-Evidence/r060-validation/delivery-verification.json'
with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
