"""Recompute audited aggregation and prove that summary tampering is rejected."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require
from .audit import collect


def main(out):
    expected=collect(out); actual=load(out/'summary.json')
    require(actual==expected,'Exact independently recomputed summary')
    mutations={
        'coverage':lambda x:x['rows'].pop(),
        'selection':lambda x:x['rows'][-2]['first_selection'].update(edges=[0]),
        'activation':lambda x:x['rows'][-2]['pools'][0]['candidates'][0].update(activation=.1),
        'inhibition':lambda x:x['rows'][-2]['pools'][0].update(inhibition_edge_count=0),
        'cost':lambda x:x['rows'][0]['cost'].update(kernel_ticks=0),
        'proof':lambda x:x['rows'][-2]['candidate']['decision']['proof'].update(primitive_depth=99),
        'claim':lambda x:x.update(new_independent_samples=6),
        'binding_identity':lambda x:x['rows'][-2]['pools'][0]['candidates'][1].update(circuit_id='invented-second-pattern'),
        'prior_control':lambda x:x['rows'][-2]['pools'][0]['candidates'][0].update(prior=1),
        'unknown_energy':lambda x:x.update(actual_energy_joules=0),
    }
    rejected=[]
    for name,mutate in mutations.items():
        bad=deepcopy(actual);mutate(bad)
        require(bad!=expected,'Undetected summary mutation '+name);rejected.append(name)
    dump(out/'validation/summary-verification.json',dict(verified=True,rejected_summary_mutations=rejected,
        research_sample=False,separate_native_replay=False))
    print('Summary verification passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    main(p.parse_args().out)
