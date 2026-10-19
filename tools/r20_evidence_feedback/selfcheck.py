"""Pure gate, JSON roundtrip and saved-trace checks; no native experiment."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import dynamics
from hcr.codec import plain
from hcr.model import Config
from tools.r19_cross_level import probe as common
from tools.r20_evidence_feedback import probe
from tools.r20_evidence_feedback.policy import decide,require,validate


def check(portable):
    p=probe.spec();count=0
    def assertion(ok,message):
        nonlocal count
        require(ok,message);count+=1
    expected={
        'clear_A':'lower_already_decided','clear_B':'lower_already_decided',
        'revision_0':'missing_aux','derived_aux':'shared_measurement_lineage',
        'independent_A':'fresh_disjoint_compatible_aux','independent_B':'fresh_disjoint_compatible_aux',
        'conflicting_aux':'aux_context_disagreement','stale_aux':'stale_aux_revision',
        'independent_wrong':'fresh_disjoint_compatible_aux','strong_conflict':'lower_already_decided',
        'revision_1':'lower_already_decided'}
    assertion(len(p['cases'])==11 and len({c['key'] for c in p['cases']})==11,'matrix')
    for cell in p['cases']:
        c=cell['public'];validate(c)
        lower=dict(convergence=dict(status='stable_decision' if any(c['measurements']) else 'stable_ambiguous'))
        got=decide(c,lower,p)
        assertion(got['reason']==expected[cell['key']],'gate branch '+cell['key'])
        renamed=dict(c,id='renamed')
        assertion({k:v for k,v in decide(renamed,lower,p).items() if k!='public_sha256'}==
            {k:v for k,v in got.items() if k!='public_sha256'},'identity must not choose answer')
    base=deepcopy(next(c['public'] for c in p['cases'] if c['key']=='independent_A'))
    low=dict(convergence=dict(status='stable_ambiguous'))
    for score,action in [(0.8,'feedback'),(0.799,'abstain'),(0.0,'abstain')]:
        c=deepcopy(base);c['aux']['score']=score
        assertion(decide(c,low,p)['action']==action,'fixed magnitude boundary')
    for field,value,reason in [('source_id','unregistered','unregistered_source'),('parents',['f0'],'shared_measurement_lineage'),
            ('measurement_ids',['f1'],'shared_measurement_lineage'),('revision',1,'stale_aux_revision')]:
        c=deepcopy(base);c['aux'][field]=value
        assertion(decide(c,low,p)['reason']==reason,'public lineage boundary')
    assertion(decide(base,dict(convergence=dict(status='budget_exhausted')),p)['reason']=='lower_unsettled','unsettled cannot use feedback')
    polluted=dict(base,hidden_truth=True)
    try:validate(polluted)
    except ValueError:count+=1
    else:raise ValueError('hidden field accepted')
    original_tick,original_settle,original_one=dynamics.tick,dynamics.settle,common.settle_one
    def forbidden(*args,**kwargs):raise AssertionError('native calculation during selfcheck')
    dynamics.tick=dynamics.settle=forbidden
    try:
        golden=common.read(ROOT/'evidence/substitution-cross-level-20261019-r19/raw/clear_A_match__coupled.json')
        tolerance=p['numeric_replay_absolute_tolerance_portable'] if portable else p['numeric_replay_absolute_tolerance_server']
        error=common.audit_execution(golden,golden['public'],golden['arm'],p,tolerance)
        assertion(error<=tolerance,'saved Linux/portable scalar replay')
        ambiguous=common.read(ROOT/'evidence/substitution-cross-level-20261019-r19/raw/ambiguous_A__coupled.json')
        # Adapt already saved traces to test the new auditor; never call a kernel.
        for key,arm,source,length in [('clear_A','bottom_up',golden,2),('clear_A','gated',golden,2),
                ('independent_A','gated',ambiguous,4),('revision_0','gated',ambiguous,1)]:
            c=next(x['public'] for x in p['cases'] if x['key']==key)
            kernels=deepcopy(source['kernels'][:length]);g=decide(c,probe.unpack(kernels[0]),p) if arm=='gated' else None
            low=kernels[-2] if length%2==0 else kernels[-1];withheld=arm=='gated' and low['adopted'] is None
            saved=dict(public=c,arm=arm,gate=g,gate_wall_seconds=0.0,kernels=kernels,
                promotions=[probe.promotion(c,probe.unpack(kernels[2*j]),j,g) for j in range(length//2)],
                feedback=source['feedback'] if length==4 else 0.0,category=low['adopted'],
                relation=None if length==1 or withheld else kernels[-1]['adopted'],relation_withheld_due_to_lower=withheld,
                native_settle_calls=length,training_calls=0,adapter_vectors=dict(lower=(length+1)//2,upper=length//2,feedback=1 if length==4 else 0),
                native_adaptive_session=False,native_route_proof=False)
            assertion(probe.audit_execution(saved,c,arm,p,tolerance)<=tolerance,'saved trace auditor branch '+key+'/'+arm)
        lo,hi=common.programs(Config(**p['kernel']))
        assertion(plain(lo)['groups'][0]['id']=='f0' and plain(hi)['groups'][0]['id']=='promoted','program JSON normalization')
        def fake_one(program,drives,cfg):
            upper='match_A' in {g.id for g in program.groups}
            score=drives['context'] if upper else sum(drives.values())
            state={g.id:.5 for g in program.groups};state['goal']=.5 if score==0 else (.9 if score>0 else .1)
            if upper:
                state['goal']=.9;state['match_A']=.9 if score>0 else .1;state['match_B']=1-state['match_A']
            status='stable_ambiguous' if state['goal']==.5 else 'stable_decision'
            return dict(state=state,convergence=dict(status=status),adopted=None if status=='stable_ambiguous' else state['goal']>.5)
        common.settle_one=fake_one
        for cell in p['cases']:
            for arm in p['arms']:
                e=probe.execute(cell['public'],arm,p)
                action=e['gate']['action'] if e['gate'] else None
                expected_calls=1 if action=='abstain' else (4 if arm=='unconditional' or action=='feedback' else 2)
                assertion(e['native_settle_calls']==expected_calls,'stub orchestration shape')
                assertion(not (arm=='gated' and e['category'] is None and e['relation'] is not None),'stub lower uncertainty contract')
    finally:
        dynamics.tick,dynamics.settle,common.settle_one=original_tick,original_settle,original_one
    return dict(status='PURE_PREPARATION_PASSED',assertions=count,stub_cells=33,native_tick_calls=0,native_settle_calls=0,
        saved_record_max_absolute_error=error,numeric_tolerance=tolerance,
        notice='Stub cells are orchestration checks, not experimental observations.')


if __name__=='__main__':
    import json
    print(json.dumps(check(portable=True),sort_keys=True))
