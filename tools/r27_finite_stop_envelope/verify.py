"""Exact unrounded Taylor sandwich and separately reconstructed finite bound."""
from fractions import Fraction as F
from tools.r19_cross_level.probe import require
from tools.r26_contraction_warmstart.verify import rational_gate
from tools.r24_trust_boundary.census import freeze
from .envelope import enc,dec

def exp_sandwich(a):
    term=total=F(1)
    for k in range(1,129):term=term*a/k;total+=term
    return total,total+term*a/F(129)/(1-a/F(130))

def exp_enclosure(a,lo,hi):
    require(0<=a<=16 and lo>0 and lo<=hi,'exp enclosure')
    slo,shi=exp_sandwich(a)
    require(lo<=slo and shi<=hi and hi-lo<=F(1,10**40),'exp enclosure')
    require((lo*(1<<192)).denominator==(hi*(1<<192)).denominator==1,'exp dyadic grid')

def point(record,cfg,weights,bound):
    gate=rational_gate(record['program'],cfg,record['drives'],weights)
    require(bound['gate']==gate,'global bound');q=dec(gate['q_upper'])
    if q>=1:
        require(bound==dict(status='GLOBAL_BOUND_INCONCLUSIVE',gate=gate),'noncontractive certificate');return
    require(bound['status']=='FINITE_TERMINAL_ENVELOPE' and [c['group'] for c in bound['components']]==[g['id'] for g in record['program']['groups']],'point shape')
    prev=record['initial'] if len(record['ticks'])==1 else record['ticks'][-2]['state'];last=record['state'];errors={};d=F(cfg['damping']);t=F(cfg['temperature'])
    for g,c in zip(record['program']['groups'],bound['components'],strict=True):
        key=g['id'];x=F(prev[key]);total=F(g['bias'])+F(record['drives'].get(key,0))
        for e in record['program']['links']:
            if e['target']==key:total+=F(e['weight'])*(2*F(prev[e['source']])-1)
        positive=total+F(cfg['self_excitation'])*x-F(cfg['inhibition'])*(1-x)
        negative=-total+F(cfg['self_excitation'])*(1-x)-F(cfg['inhibition'])*x
        z=(positive-negative)/t;require(c['z']==enc(z),'exact logit');lo,hi=dec(c['exp_lower']),dec(c['exp_upper']);exp_enclosure(abs(z),lo,hi)
        if z<0:a,b=1/(1+hi),1/(1+lo)
        else:a,b=lo/(1+lo),hi/(1+hi)
        a,b=(1-d)*x+d*a,(1-d)*x+d*b
        require(c['ideal_next_lower']==enc(a) and c['ideal_next_upper']==enc(b),'ideal step enclosure')
        error=max(abs(F(last[key])-a),abs(F(last[key])-b));errors[key]=error/F(weights[key]);require(c['defect_bound']==enc(error),'native point defect')
    residual=max(abs(F(last[k])-F(prev[k]))/F(weights[k]) for k in weights);eta=max(errors.values());rho=dec(bound['fixed_point_radius'])
    require(bound['residual_norm']==enc(residual) and bound['defect_norm']==enc(eta),'last step norms')
    require(rho>=0 and (1-q)*rho==q*residual+eta,'fixed-point radius')

def pair(base,candidate,b0,b1,cfg,weights,tolerance,seen):
    if freeze(base)==freeze(candidate):expected=dict(kind='EXACT_RECORD_IDENTITY',certified=True,state_difference_upper=enc(F(0)),terminal_goal_envelope=None,predicted_adopted=base['adopted'])
    elif b0['status']!='FINITE_TERMINAL_ENVELOPE' or b1['status']!='FINITE_TERMINAL_ENVELOPE':expected=dict(kind='UNPROVEN_GLOBAL_BOUND',certified=False,state_difference_upper=None,terminal_goal_envelope=None,predicted_adopted=None)
    else:
        r,s=dec(b0['fixed_point_radius']),dec(b1['fixed_point_radius']);upper=max(F(weights[k])*(r+s) for k in weights)
        interval=[F(base['state']['goal'])-F(weights['goal'])*(r+max(r,s)),F(base['state']['goal'])+F(weights['goal'])*(r+max(r,s))]
        sign=None
        if 2*interval[0]-1>=F(cfg['margin_threshold']):sign=True
        elif 1-2*interval[1]>=F(cfg['margin_threshold']):sign=False
        accepted=upper<=F(tolerance) and sign is not None and base['convergence']['status']==candidate['convergence']['status']=='stable_decision'
        expected=dict(kind='CONTRACTION_ENVELOPE' if accepted else 'UNPROVEN_RADIUS_MARGIN_OR_STATUS',certified=accepted,state_difference_upper=enc(upper),terminal_goal_envelope=[enc(v) for v in interval],predicted_adopted=sign)
    require(seen==expected,'pair decision')
    delta=max(abs(F(base['state'][k])-F(candidate['state'][k])) for k in weights)
    actual=base['convergence']['status']==candidate['convergence']['status'] and base['adopted']==candidate['adopted'] and delta<=F(tolerance)
    if seen['certified']:
        require(actual and seen['predicted_adopted']==base['adopted']==candidate['adopted'],'false certification')
        require(delta<=dec(seen['state_difference_upper']),'bound violated')
    return dict(observed_quality_preserved=actual,observed_max_terminal_abs_difference=float(delta))

def break_even(reset,candidate,gate,seen):
    a,b,g=F(reset),F(candidate),F(gate);budget=a+g-b
    expected=dict(reset=enc(a),candidate_including_gate=enc(b),gate=enc(g),candidate_without_gate_arithmetic=enc(b-g),allowable_gate_budget=enc(budget),gate_only_feasible_if_other_costs_fixed=budget>0,required_gate_reduction_fraction=enc((g-budget)/g) if budget>0 and g else None,hypothetical_minimum_amortization_uses=(g//budget)+1 if budget>0 else None,assumption='Saved other costs remain fixed; no optimized implementation or reuse validity measured')
    require(seen==expected,'cost ledger')
