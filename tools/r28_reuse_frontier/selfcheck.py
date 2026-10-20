"""Pure checks only; no native settle and no benchmark timing."""
import math
import random
import sys
from copy import deepcopy
from dataclasses import replace
from tools.r19_cross_level.probe import require
from tools.r26_contraction_warmstart import policy
from tools.r26_contraction_warmstart.verify import rational_gate
from tools.r28_reuse_frontier import predicate as gate

def check(value,expected):
    require(sys.float_info.radix==2 and sys.float_info.mant_dig==53 and sys.float_info.max_exp==1024,'binary64 platform')
    compiled=gate.compile_predicate(value,expected);proof=gate.verify_compiled(compiled,value,expected)
    t=compiled.threshold;lower=math.nextafter(t,0.);upper=math.nextafter(t,math.inf)
    points=[-4.,-upper,-t,-lower,-0.,0.,lower,t,upper,4.];checks=0
    pairs=[(a,b) for a in points for b in points]
    # Frozen seed and uniform bit-order points are diagnostics, not a distributional claim.
    rng=random.Random(280074)
    pairs += [(gate.number(rng.randrange(gate.bits(4.)+1))*(-1 if rng.randrange(2) else 1),
               gate.number(rng.randrange(gate.bits(4.)+1))*(-1 if rng.randrange(2) else 1)) for _ in range(64)]
    for a,b in pairs:
        drives=dict(f0=a,f1=b,goal=0.);one=policy.certificate(value['program'],value['config'],drives,value['weights'])
        two=rational_gate(value['program'],value['config'],drives,value['weights'])
        require(one==two and gate.eligible(compiled,drives)==one['eligible'],'oracle/predicate agreement');checks+=1
    rejected={}
    def rejection(name,fn):
        try:fn()
        except ValueError as exc:rejected[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    for label,threshold in [('threshold_down',lower),('threshold_up',upper)]:
        rejection(label,lambda threshold=threshold:gate.verify_compiled(replace(compiled,threshold=threshold),value,expected))
    for name in ['config','weight','bias','link_order','top_down','source','norm']:
        bad=deepcopy(value)
        if name=='config':bad['config']['patience']+=1
        elif name=='weight':bad['program']['links'][0]['weight']+=.01
        elif name=='bias':bad['program']['groups'][0]['bias']+=.01
        elif name=='link_order':bad['program']['links'].reverse()
        elif name=='top_down':bad['top_down']=False
        elif name=='source':bad['sources']['native']='0'*64
        else:bad['weights']['goal']=7
        rejection(name,lambda bad=bad:gate.compile_predicate(bad,expected))
    for name,x in [('nan',math.nan),('inf',math.inf),('outside',math.nextafter(4.,math.inf)),('integer',1)]:
        rejection(name,lambda x=x:gate.eligible(compiled,dict(f0=x,f1=4.,goal=0.)))
    rejection('goal_drive',lambda:gate.eligible(compiled,dict(f0=4.,f1=4.,goal=.01)))
    rejection('extra_drive',lambda:gate.eligible(compiled,dict(f0=4.,f1=4.,goal=0.,extra=0.)))
    # Deliberate comparator mutant must disagree at the accepted endpoint.
    require(gate.eligible(compiled,dict(f0=t,f1=4.,goal=0.)) and not (abs(t)>t and 4.>t),'strict comparator mutant')
    rejected['strict_comparator']='endpoint disagreement'
    invalid=dict(binding='bound',status='stable_decision',state=dict(f0=math.nan,f1=.5,goal=.5),cell='old')
    rejection('invalid_source_before_false_gate',lambda:policy.choose('guarded',invalid,'bound',dict(eligible=False),['f0','f1','goal']))
    return dict(status='PURE_PREDICATE_CHECKED',oracle_pairs=checks,targeted_rejections=rejected,proof=proof,
                binary_search_iterations=compiled.iterations,native_settle_calls=0,training_calls=0,world_measure_calls=0)
