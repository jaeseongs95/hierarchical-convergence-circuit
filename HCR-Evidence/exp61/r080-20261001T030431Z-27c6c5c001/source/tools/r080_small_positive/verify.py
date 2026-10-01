"""Recompute raw-derived measurements and reject targeted summary corruption."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require
from .audit import collect


def main(out):
    expected=collect(out);actual=load(out/'summary.json')
    require(actual==expected,'Exact independently recomputed summary')
    target=next(i for i,r in enumerate(actual['rows']) if r['id']=='swapped-s00-off')
    def first(x):return x['rows'][target]['first_decision']
    mutations={
        'coverage':lambda x:x['rows'].pop(),
        'first_network_status':lambda x:first(x)['convergence'].update(status='stable_ambiguous'),
        'first_progress_reason':lambda x:first(x).update(progress_mismatch_kind='unresolved_or_no_goal_candidate'),
        'candidate_value':lambda x:first(x).update(candidate_value=None),
        'ready':lambda x:first(x).update(ready=True),
        'graph_complete':lambda x:first(x).update(graph_complete=True),
        'advance_mapping':lambda x:first(x).update(generation=2),
        'frontier':lambda x:first(x).update(frontier=[]),
        'goal':lambda x:first(x).update(goal_activation=.5),
        'final_ancestry':lambda x:x['rows'][target]['final_support'].update(selected_edge_id_path=['e2','e3']),
        'D_DAG':lambda x:x['rows'][target]['final_support'].update(recomputed_D_DAG=99),
        'ticks':lambda x:x['rows'][target]['cost'].update(kernel_ticks=0),
        'reproduction_count':lambda x:x.update(reproduction_executions=0),
        'discovery_count':lambda x:x.update(new_independent_samples=7),
        'prediction':lambda x:x['predictions']['positive_grid_stable_true'].update(verdict='invented'),
        'actual_duration':lambda x:x['rows'][target]['durations'].update(native_active_seconds=-1),
        'centered_input':lambda x:first(x)['link_terms'][0].update(last_tick_centered_link_input=99),
        'pool_applicability':lambda x:x['rows'][target].update(pool_metrics=0),
        'stability_prediction':lambda x:x['predictions']['small_positive_stability_boundary_exists'].update(verdict='invented'),
        'unknown_energy':lambda x:x.update(actual_energy_joules=0),
    }
    rejected=[]
    for name,mutate in mutations.items():
        bad=deepcopy(actual);mutate(bad)
        require(bad!=expected,'Undetected measurement/summary corruption '+name);rejected.append(name)
    dump(out/'validation/summary-verification.json',dict(verified=True,rejected_summary_mutations=rejected,
        native_executions=0,research_sample=False,raw_recalculation=True))
    print('Summary and measurement verification passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
