"""Retrospective finite-state bounds; never a pre-execution reuse gate."""
from fractions import Fraction as F
from tools.r26_contraction_warmstart import policy
from tools.r24_trust_boundary.census import freeze
enc,dec=policy.encoded,policy.decoded
BITS=192
TERMS=128
GRID=1<<BITS

def down(v):return F((v*GRID).numerator//(v*GRID).denominator,GRID)
def up(v):return -down(-v)

def exp_bounds(a):
    a=F(a)
    if not 0<=a<=16:raise ValueError('exp domain')
    lo=hi=F(1);slo=shi=F(1)
    for k in range(1,TERMS+1):
        lo=down(lo*a/k);hi=up(hi*a/k);slo+=lo;shi+=hi
    tail=hi*a/(TERMS+1)/(1-a/F(TERMS+2))
    return down(slo),up(shi+tail)

def point(record,cfg,weights):
    gate=policy.certificate(record['program'],cfg,record['drives'],weights);q=dec(gate['q_upper'])
    if q>=1:return dict(status='GLOBAL_BOUND_INCONCLUSIVE',gate=gate)
    previous=record['initial'] if len(record['ticks'])==1 else record['ticks'][-2]['state']
    last=record['state'];d,t,s=F(cfg['damping']),F(cfg['temperature']),F(cfg['self_excitation'])+F(cfg['inhibition']);components=[]
    for g in record['program']['groups']:
        key=g['id'];x=F(previous[key]);z=(2*(F(g['bias'])+F(record['drives'].get(key,0)))+2*sum(F(e['weight'])*(2*F(previous[e['source']])-1) for e in record['program']['links'] if e['target']==key)+s*(2*x-1))/t
        elo,ehi=exp_bounds(abs(z));low,high=1/(1+ehi),1/(1+elo)
        if z>=0:low,high=1-high,1-low
        lo,hi=(1-d)*x+d*low,(1-d)*x+d*high
        defect=max(abs(F(last[key])-lo),abs(F(last[key])-hi))
        components.append(dict(group=key,z=enc(z),exp_lower=enc(elo),exp_upper=enc(ehi),ideal_next_lower=enc(lo),ideal_next_upper=enc(hi),defect_bound=enc(defect)))
    r=max(abs(F(last[k])-F(previous[k]))/F(weights[k]) for k in weights)
    eta=max(dec(c['defect_bound'])/F(weights[c['group']]) for c in components)
    return dict(status='FINITE_TERMINAL_ENVELOPE',gate=gate,components=components,residual_norm=enc(r),defect_norm=enc(eta),fixed_point_radius=enc((q*r+eta)/(1-q)))

def pair(base,candidate,bound0,bound1,cfg,weights,tolerance):
    if freeze(base)==freeze(candidate):return dict(kind='EXACT_RECORD_IDENTITY',certified=True,state_difference_upper=enc(F(0)),terminal_goal_envelope=None,predicted_adopted=base['adopted'])
    if any(b['status']!='FINITE_TERMINAL_ENVELOPE' for b in [bound0,bound1]):return dict(kind='UNPROVEN_GLOBAL_BOUND',certified=False,state_difference_upper=None,terminal_goal_envelope=None,predicted_adopted=None)
    r0,r1=dec(bound0['fixed_point_radius']),dec(bound1['fixed_point_radius']);upper=F(max(weights.values()))*(r0+r1)
    center=F(base['state']['goal']);radius=F(weights['goal'])*(r0+max(r0,r1));lo,hi=center-radius,center+radius
    threshold=F(cfg['margin_threshold'])/2;sign=True if lo>=F(1,2)+threshold else False if hi<=F(1,2)-threshold else None
    stable=all(r['convergence']['status']=='stable_decision' for r in [base,candidate])
    accepted=upper<=F(tolerance) and sign is not None and stable
    return dict(kind='CONTRACTION_ENVELOPE' if accepted else 'UNPROVEN_RADIUS_MARGIN_OR_STATUS',certified=accepted,state_difference_upper=enc(upper),terminal_goal_envelope=[enc(lo),enc(hi)],predicted_adopted=sign)

def break_even(reset,candidate,gate):
    reset,candidate,gate=map(F,[reset,candidate,gate]);budget=reset-(candidate-gate)
    return dict(reset=enc(reset),candidate_including_gate=enc(candidate),gate=enc(gate),candidate_without_gate_arithmetic=enc(candidate-gate),allowable_gate_budget=enc(budget),gate_only_feasible_if_other_costs_fixed=budget>0,required_gate_reduction_fraction=None if budget<=0 or gate==0 else enc(1-budget/gate),hypothetical_minimum_amortization_uses=None if budget<=0 else (gate//budget)+1,assumption='Saved other costs remain fixed; no optimized implementation or reuse validity measured')
