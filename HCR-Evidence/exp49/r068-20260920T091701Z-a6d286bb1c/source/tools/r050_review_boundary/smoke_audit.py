"""Independent audit of implementation-only native smoke records."""
from __future__ import annotations
import argparse
from pathlib import Path
from .common import dump, load, require, unseal
from .audit import NativeVerifier, validate_arm, independent_target, FORBIDDEN
import sys

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',required=True,type=Path)
    a=ap.parse_args(argv)
    plan=unseal(load(a.run/'plan.json'),'hcc-r050-plan-v1')
    root=a.run/'validation'/'native-smoke'
    verifier=NativeVerifier(plan)
    total=0
    for td in (False,True):
        case=next(c for c in plan['cases'] if c['strength']==.02 and c['relation']=='++'
                  and c['identity_variant']==0 and c['top_down'] is td)
        base=load(root/'baselines'/(case['id']+'.json'))
        b=unseal(base,'hcc-r050-baseline-v1')
        verifier.execution(b['execution'],case,case['observation'],0,'baseline')
        require(b['experimental_probe_target']==independent_target(case['observation'],b['execution']['candidate']), 'Smoke target')
        for arm in ('hold','same_input_restart','echo_revision_restart','strength_revision_restart'):
            validate_arm(load(root/'raw'/case['id']/(arm+'.json')),base,case,plan,root,verifier)
            total+=1
    require(not(FORBIDDEN & set(sys.modules)),'Smoke auditor imported producer')
    dump(root/'audit.json',dict(verified=True,baselines=2,arm_records=total,research_experiment=False,
         purpose='implementation/contract validation only; excluded from EXP-31 aggregation'))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
