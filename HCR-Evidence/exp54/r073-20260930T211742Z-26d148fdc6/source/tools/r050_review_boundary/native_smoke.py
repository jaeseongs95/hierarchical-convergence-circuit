"""Implementation-only actual-core smoke test; never pooled with EXP-31 results."""
from __future__ import annotations
import argparse
from copy import deepcopy
from pathlib import Path
from .common import dump, load, require, unseal
from .worker import make_baseline, run_arm


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',required=True,type=Path)
    a=ap.parse_args(argv)
    plan=unseal(load(a.run/'plan.json'),'hcc-r050-plan-v1')
    location=a.run/'validation'/'native-smoke'
    counts=0
    for top_down in (False,True):
        # A weak, known-score case exercises both the rejection path and explicit
        # restart switches when the native engine exposes such a rejection.
        case=deepcopy(next(c for c in plan['cases'] if c['strength']==.02 and c['relation']=='++'
                           and c['identity_variant']==0 and c['top_down'] is top_down))
        baseline=make_baseline(plan,case,location)
        dump(location/'baselines'/(case['id']+'.json'),baseline)
        for arm in ('hold','same_input_restart','echo_revision_restart','strength_revision_restart'):
            record=run_arm(plan,case,baseline,arm,location)
            dump(location/'raw'/case['id']/(arm+'.json'),record)
            if record['execution'] is not None:
                require(record['execution']['packet']['document']['engine']['switches']['top_down'] is top_down,
                        'top_down flag leaked on restart')
            counts+=1
    dump(location/'producer_smoke.json',dict(executed=True,arm_records=counts,research_experiment=False,
         actual_core_called=True,oracle_or_synthetic_pass_not_research_evidence=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
