"""Small pure mathematical/boundary checks, not archived research analysis."""
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction as F
from hcr.model import Config
from hcr.codec import plain
from tools.r19_cross_level.probe import programs,require
from tools.r26_contraction_warmstart.selfcheck import check as original_check
from . import envelope as e,verify

def check():
    prior=original_check();count=0
    def assertion(ok,msg):
        nonlocal count
        require(ok,msg);count+=1
    def reject(call,reason):
        try:call()
        except ValueError as exc:assertion(str(exc)==reason,'selfcheck cause '+str(exc))
        else:raise ValueError('selfcheck accepted '+reason)
    for a in [F(0),F(1,16),F(1),F(8),F(16)]:
        lo,hi=e.exp_bounds(a);verify.exp_enclosure(a,lo,hi);assertion(hi-lo<=F(1,10**40),'exp enclosure width')
    assertion(e.exp_bounds(0)==(F(1),F(1)),'zero exp exact')
    reject(lambda:e.exp_bounds(F(-1)),'exp domain');reject(lambda:e.exp_bounds(F(16)+F(1,2**53)),'exp domain')
    lo,hi=e.exp_bounds(1);reject(lambda:verify.exp_enclosure(F(1),lo,lo),'exp enclosure')
    for a in [F(1,3),F(-1,3),F(1,2**193)]:assertion(e.down(a)<=a<=e.up(a) and e.up(a)-e.down(a)<=F(1,2**192),'outward dyadic')
    cfg=asdict(Config(prior_gain=0));program=plain(programs(Config(**cfg))[0]);weights=dict(f0=1,f1=1,goal=8);state={k:.5 for k in weights}
    # Deliberately synthetic step; defect must be retained, not assumed to be machine epsilon.
    fake=dict(program=program,drives=dict(f0=4.,f1=3.2,goal=0.),initial=dict(state),state=dict(state),ticks=[dict(state=dict(state))],convergence=dict(status='stable_ambiguous'),adopted=None)
    bound=e.point(fake,cfg,weights);verify.point(fake,cfg,weights,bound);assertion(e.dec(bound['defect_norm'])>0 and e.dec(bound['fixed_point_radius'])>0,'nonzero point defect retained')
    for key,reason in [('fixed_point_radius','fixed-point radius'),('defect_norm','last step norms')]:
        bad=deepcopy(bound);bad[key]=e.enc(e.dec(bad[key])+1);reject(lambda bad=bad:verify.point(fake,cfg,weights,bad),reason)
    neutral=deepcopy(fake);neutral['drives']={k:0. for k in weights};b=e.point(neutral,cfg,weights);verify.point(neutral,cfg,weights,b);assertion(b['status']=='GLOBAL_BOUND_INCONCLUSIVE','q>=1 inconclusive')
    bad=deepcopy(b);bad['status']='FINITE_TERMINAL_ENVELOPE';reject(lambda:verify.point(neutral,cfg,weights,bad),'noncontractive certificate')
    c=e.pair(fake,deepcopy(fake),bound,bound,cfg,weights,1e-4);verify.pair(fake,fake,bound,bound,cfg,weights,1e-4,c);assertion(c['kind']=='EXACT_RECORD_IDENTITY','typed identity')
    different=deepcopy(fake);different['initial']['goal']=-0.;c=e.pair(fake,different,bound,bound,cfg,weights,1e-4);verify.pair(fake,different,bound,bound,cfg,weights,1e-4,c);assertion(not c['certified'],'large defect is not safe')
    for r,c,g in [(1.,2.,.25),(1.,2.,1.),(1.,2.,1.5),(1.,.9,0.)]:
        seen=e.break_even(r,c,g);verify.break_even(r,c,g,seen);assertion(seen['gate_only_feasible_if_other_costs_fixed']==(F(r)+F(g)-F(c)>0),'cost sign')
    return dict(status='PURE_FINITE_ENVELOPE_CHECKS_PASSED',assertions=count,prior_boundary_assertions=prior['assertions'],new_native_calls=0,new_timing_runs=0,archived_research_certificates_generated=0)
