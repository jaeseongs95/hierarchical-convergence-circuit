"""Same core cold computations as EXP26 OFF; regression is not new research evidence."""
import csv,io as textio
from . import sources,storage as io
from .runtime import run_query
from .evaluator import audit_record


def native_regression(parent,out):
    basis=sources.read_basis(parent);root=io.safe(out);root.mkdir(parents=True,exist_ok=False)
    old_plan=io.loads(basis['data']['plan.json']);lookup={c['name']:c for c in old_plan['cases']}
    signatures={r['trial_id']:r for r in csv.DictReader(textio.StringIO(basis['data']['analysis/decision_networks.csv'].decode('utf-8')))}
    trials=list(csv.DictReader(textio.StringIO(basis['data']['analysis/trials.csv'].decode('utf-8'))))
    completed=0
    for trial in trials:
        if trial['use_circuits']!='False':continue
        name=trial['family']+'__'+trial['id_variant'];obs=lookup[name]['observation'];tid=trial['trial_id']
        with (root/(tid+'.events.jsonl')).open('x',encoding='utf-8',newline='\n') as f:
            def emit(e):f.write(io.canonical(e).decode()+'\n');f.flush()
            result=run_query(obs,basis['config'],event_sink=emit)
        io.put(root/(tid+'.json'),dict(mode='native_core_regression_not_EXP27',record=result))
        a=audit_record(result);old=signatures[tid]
        io.require(a['dynamics_sha256']==old['dynamics_sha256'],'EXP26 cold dynamics regression: '+tid)
        io.require(result['native_cost']['kernel_ticks']==int(trial['native_kernel_ticks']),'EXP26 cold tick regression')
        io.require(str(result['raw_value'])==trial['value'] and str(result['accepted'])==trial['accepted'],'EXP26 cold adoption regression')
        io.put(root/(tid+'.audit.json'),a);completed+=1
    io.require(completed==6,'EXP26 OFF regression population')
    report=dict(verified=True,completed=completed,mode='native_core_regression_not_research',
        full_AdaptiveSession_rerun=False,independent_scalar_and_proof_audit=True)
    io.put(root/'regression.json',report);return report
