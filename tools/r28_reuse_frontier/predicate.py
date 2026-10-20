"""Boolean-only specialization of the frozen R26 Fraction screen."""
from dataclasses import dataclass
import math
import struct
from fractions import Fraction as F
from hcr.model import fingerprint
from tools.r19_cross_level.probe import require
from tools.r26_contraction_warmstart import policy

def bits(x):return struct.unpack('>Q',struct.pack('>d',x))[0]
def number(n):return struct.unpack('>d',struct.pack('>Q',n))[0]

@dataclass(frozen=True)
class Compiled:
    threshold:float
    binding:str
    iterations:int

def profile(program,config,weights,sources,top_down):
    return dict(program=program,config=config,weights=weights,sources=sources,top_down=top_down,
                domain='binary64 drives f0/f1 in [-4,4], goal=0',threshold=[19,20],version='R28-boolean-v1')

def compile_predicate(value,expected):
    require(fingerprint(value)==expected and value['top_down'] is True,'unsupported binding')
    program,cfg,weights=value['program'],value['config'],value['weights']
    def allowed(x):return policy.certificate(program,cfg,dict(f0=x,f1=x,goal=0.),weights)['eligible']
    lo,hi=bits(0.),bits(4.);require(not allowed(0.) and allowed(4.),'search bracket');steps=0
    while hi-lo>1:
        mid=(lo+hi)//2;steps+=1
        if allowed(number(mid)):hi=mid
        else:lo=mid
    require(steps<=63,'search cap')
    result=Compiled(number(hi),expected,steps)
    verify_compiled(result,value,expected)
    return result

def verify_compiled(compiled,value,expected):
    """Independent expanded polynomial oracle plus whole-domain monotonicity premises."""
    from tools.r26_contraction_warmstart.verify import rational_gate
    require(fingerprint(value)==expected and compiled.binding==expected and value['top_down'] is True,'unsupported binding')
    p,c,w=value['program'],value['config'],value['weights'];groups=p['groups'];edges=p['links']
    require([g['id'] for g in groups]==['f0','f1','goal'] and all(g['bias']==0. for g in groups),'zero bias structure')
    require([(e['source'],e['target'],e['kind']) for e in edges]==[('f0','goal','support'),('f1','goal','support'),('goal','f0','top_down'),('goal','f1','top_down')],'ordered structure')
    require(edges[0]['weight']==edges[1]['weight'] and edges[2]['weight']==edges[3]['weight'] and w['f0']==w['f1'],'identical input rows')
    require(0<F(c['damping'])<=1 and F(c['temperature'])>0 and F(c['self_excitation'])+F(c['inhibition'])>=0 and all(F(v)>0 for v in w.values()),'monotone coefficients')
    # x=max(0,(2|u|-radius)/T) is nondecreasing; 1/(1+x+x²/2+x³/6+x⁴/24)
    # and min(1/4,.) are nonincreasing. Nonnegative row coefficients preserve this order.
    # The equal input rows and the constant admissible goal row reduce max(q_i)<=19/20
    # to one monotone scalar predicate. Adjacent finite positive binary64s then prove
    # the entire accepted suffix, including signed zero and negative drives by symmetry.
    t=compiled.threshold;require(type(t) is float and math.isfinite(t) and 0<t<=4.,'threshold range')
    at=rational_gate(p,c,dict(f0=t,f1=t,goal=0.),w)
    before=rational_gate(p,c,dict(f0=math.nextafter(t,0.),f1=math.nextafter(t,0.),goal=0.),w)
    goal=at['rows'][2]['weighted_row_upper'];require(F(goal['numerator'],goal['denominator'])<=F(19,20),'constant goal row')
    require(at['eligible'] and not before['eligible'],'adjacent threshold proof')
    require(bits(math.nextafter(t,0.))+1==bits(t),'binary64 adjacency')
    return dict(binding=expected,threshold_hex=t.hex(),predecessor_hex=math.nextafter(t,0.).hex(),
                goal_q=goal,monotone_input_rows=True,scope='eligible Boolean only; not native quality or gate metadata')

def eligible(compiled,drives):
    require(set(drives)=={'f0','f1','goal'} and all(type(v) is float and math.isfinite(v) for v in drives.values())
            and drives['goal']==0. and all(-4.<=drives[k]<=4. for k in ['f0','f1']),'unsupported drives')
    return abs(drives['f0'])>=compiled.threshold and abs(drives['f1'])>=compiled.threshold
