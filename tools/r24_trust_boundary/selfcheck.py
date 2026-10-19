"""Synthetic transition contracts only: no archived census or native workload in preparation."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tools.r24_trust_boundary import census,probe

def check():
    probe.forbid_native();p=probe.spec();count=0
    def assertion(ok,message):
        nonlocal count
        census.require(ok,message);count+=1
    def reject(call,reason):
        try:call()
        except ValueError as exc:assertion(str(exc)==reason,'rejection '+str(exc))
        else:raise ValueError('guard not exercised '+reason)
    e=dict(case='a',kernel_index=0,tick=1,program=dict(groups=[dict(id='goal',bias=0.0),dict(id='x',bias=0.0)],links=[]),config=dict(damping=.45),
        current=dict(goal=.5,x=.5),next=dict(goal=.6,x=.4),initial=dict(goal=.5,x=.5),drives=dict(goal=0.0),top_down=True,
        semantics_sha256='a'*64,public_numeric=dict(measurements=[0.,0.],context=1.))
    for field in p['key_fields']:
        changed=deepcopy(e)
        if field=='program':changed[field]['groups'].reverse()
        elif field=='config':changed[field]['damping']=.5
        elif field=='current':changed[field]['x']=.6
        elif field=='drives':changed[field]['goal']=1.
        elif field=='top_down':changed[field]=False
        else:changed[field]='b'*64
        assertion(census.transition_key(e)!=census.transition_key(changed),'complete key '+field)
    assertion(census.exact_bytes(0.)!=census.exact_bytes(-0.),'signed zero')
    assertion(len({census.exact_bytes(v) for v in [True,1,1.]})==3,'numeric type separation')
    assertion(census.exact_bytes(.5)!=census.exact_bytes(.5+1e-16),'near values not merged')
    assertion(census.exact_bytes({'a':1,'b':2})==census.exact_bytes({'b':2,'a':1}),'mapping order normalization')
    reject(lambda:census.exact_bytes(float('nan')),'finite key number')
    # Later transitions have identical numeric input solely to exercise reuse contracts.
    events=[e,dict(deepcopy(e),tick=2),dict(deepcopy(e),kernel_index=1),dict(deepcopy(e),case='b')]
    local=census.analyze(events,'case_local',p);stream=census.analyze(events,'arm_stream',p)
    census.audit(local,events,'case_local',p);census.audit(stream,events,'arm_stream',p);count+=2
    assertion([r['hit'] for r in local['rows']]==[False,True,True,False],'case cold reset')
    assertion([r['locality'] for r in stream['rows']]==[None,'same_settle','same_case_other_settle','cross_case'],'locality split')
    assertion(local['summary']['hits']==2 and stream['summary']['hits']==3,'separate lifetimes not summed')
    assertion(local['rows'][2]['repeated_kernel_invocation'] and not local['rows'][1]['repeated_kernel_invocation'],'whole invocation vs same settle')
    other=census.analyze(events,'arm_stream',p)
    assertion(other['rows'][0]['hit'] is False,'new call cold; no arm sharing')
    bad=deepcopy(events);bad[1]['next']['goal']=.7
    reject(lambda:census.analyze(bad,'arm_stream',p),'same key different saved next-state')
    for name,reason in census.MUTATIONS.items():reject(lambda n=name:census.audit(census.mutated(stream,n),events,'arm_stream',p),reason)
    reject(lambda:census.caps(p['maximum_cache_entries']+1,0,p),'census entry cap')
    reject(lambda:census.caps(0,p['maximum_cache_payload_bytes']+1,p),'census payload cap')
    census.caps(p['maximum_cache_entries'],p['maximum_cache_payload_bytes'],p);count+=1
    return dict(status='PURE_PREPARATION_PASSED',assertions=count,synthetic_transition_rows=4,new_native_tick_calls=0,new_native_settle_calls=0,new_world_measure_calls=0,
        archived_census_executed=False,notice='Synthetic repetition tests exercise contracts, not research hit counts.')

if __name__=='__main__':
    import json
    print(json.dumps(check(),sort_keys=True))
