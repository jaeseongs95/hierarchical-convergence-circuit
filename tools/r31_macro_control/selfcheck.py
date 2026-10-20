"""Synthetic matcher/role/fallback checks; zero native inference, learning or settle."""
from dataclasses import replace
from types import SimpleNamespace as NS
from hcr import codec,dynamics
from hcr.model import AdaptiveCost,ExpansionBudget
from hcr.patterns import make_pattern
from hcr.trace import Trace
from hcr.evaluation.adaptive_audit_support import scan_patterns,circuit_id
from tools.r31_macro_control.macro import OrdinaryMacroPool
from tools.r31_macro_control.verify import require

def check(p):
    cfg=codec.adaptive_config_from(p['config']);pattern=make_pattern(2,cfg.kernel);raw=dict(pattern=codec.plain(pattern),active=True)
    cid=circuit_id(raw);c=NS(id=cid,pattern=pattern,active=True,version=1);m=NS(circuits=[c]);checks=0
    original_tick,original_settle=dynamics.tick,dynamics.settle
    def forbidden(*a,**k):raise AssertionError('native numerical work forbidden in preparation')
    dynamics.tick=dynamics.settle=forbidden
    try:
        for case in p['cases']:
            obs=codec.observation_from(case['observation'])
            for budget in [0,1,1024]:
                from hcr.workspace import AdaptiveWorkspace
                ws=AdaptiveWorkspace(obs,cfg,AdaptiveCost(),Trace(),'synthetic')
                result=OrdinaryMacroPool(cfg,m).activate_candidates(ws,ExpansionBudget(64,budget,32))
                expected=scan_patterns(obs,dict(visited=[obs.start],path=[]),dict(circuits=[raw]),cfg,budget)
                scan=next(e['payload'] for e in ws.trace.records if e['event']=='r02_binding_scan')
                require(all(scan[k]==v for k,v in expected.items()),'synthetic matching oracle');checks+=1
                require(ws.cost.pool_calls==ws.cost.kernel_ticks==0,'zero numerical work');checks+=1
                if not expected['complete'] or not expected['matched']:require(not result,'partial fallback');checks+=1
                else:
                    require([a.eligible for a in result]==[all(obs.edges[i].score is not None and obs.edges[i].score>0 for i in x['binding']['edge_order']) for x in expected['matched']],'public sign rule');checks+=1
                    for a in result:
                        a.binding.check(obs,len(a.binding.edge_order))
                        try:a.binding.check(replace(obs,revision=obs.revision+1),len(a.binding.edge_order))
                        except Exception as exc:require('stale' in str(exc),'stale rejection cause');checks+=1
                        else:raise ValueError('stale role binding accepted')
        # Context restoration also on an exception; never leaves shared class patched.
        from tools.r31_macro_control.runtime import control
        from hcr import expansion
        old=expansion.CircuitActivationPool
        try:
            with control('macro'):
                require(expansion.CircuitActivationPool is OrdinaryMacroPool,'patch active');raise RuntimeError('sentinel')
        except RuntimeError as exc:require(str(exc)=='sentinel','sentinel')
        require(expansion.CircuitActivationPool is old,'patch restored');checks+=2
    finally:dynamics.tick,dynamics.settle=original_tick,original_settle
    return dict(status='STRUCTURAL_CHECKS_PASSED',checks=checks,native_inference_calls=0,native_settle_calls=0,learning_calls=0)
