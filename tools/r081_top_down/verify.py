"""Recompute the summary from journals; reject corruption of paired measurements."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require
from .audit import collect


def main(out):
    expected=collect(out);actual=load(out/'summary.json')
    require(actual==expected,'Exact raw-derived summary')
    def first(x):return x['rows'][0]['first_decision']
    def disabled(x):return next(l for l in x['rows'][1]['first_decision']['link_terms'] if l['kind']=='top_down')
    mutations={
        'coverage':lambda x:x['rows'].pop(),
        'first_status':lambda x:first(x)['convergence'].update(status='invented'),
        'first_progress':lambda x:first(x).update(progress_mismatch_kind='invented'),
        'candidate_value':lambda x:first(x).update(candidate_value=None),
        'ready':lambda x:first(x).update(ready=not first(x)['ready']),
        'coverage_flag':lambda x:first(x).update(graph_complete=not first(x)['graph_complete']),
        'event_scope':lambda x:first(x).update(generation=-1),
        'goal':lambda x:first(x).update(goal_activation=-1),
        'final_ancestry':lambda x:x['rows'][0]['final_support'].update(selected_edge_id_path=['invented']),
        'D_DAG':lambda x:x['rows'][0]['final_support'].update(recomputed_D_DAG=-1),
        'ticks':lambda x:x['rows'][0]['cost'].update(kernel_ticks=-1),
        'reproduction_count':lambda x:x.update(reproduction_executions=0),
        'discovery_count':lambda x:x.update(new_independent_samples=4),
        'prediction_literal':lambda x:x['predictions']['remove_bundle_s003_true'].update(verdict='invented'),
        'prediction_category':lambda x:x['predictions']['category_change_exists'].update(verdict='invented'),
        'prediction_numeric':lambda x:x['predictions']['numeric_difference_both'].update(verdict='invented'),
        'paired_delta':lambda x:x['pairs'][0].update(first_goal_difference_false_minus_true=99),
        'paired_program':lambda x:x['pairs'][0].update(paired_program_equal=False),
        'top_down':lambda x:x['rows'][1].update(top_down=True),
        'active_signals':lambda x:x['rows'][1]['first_decision'].update(active_links_per_tick=-1),
        'disabled_transmitted':lambda x:disabled(x).update(transmitted=True),
        'disabled_actual_input':lambda x:disabled(x).update(last_tick_centered_link_input=99),
        'would_be_term':lambda x:disabled(x).update(would_be_last_tick_centered_term=99),
        'terminal_centered':lambda x:disabled(x).update(terminal_centered_link_term=99),
        'terminal_uncentered':lambda x:disabled(x).update(terminal_uncentered_activation_product=99),
        'duration':lambda x:x['rows'][0]['durations'].update(native_active_seconds=-1),
        'pool_applicability':lambda x:x['rows'][0].update(pool_metrics=0),
        'energy_unknown':lambda x:x.update(actual_energy_joules=0),
    }
    rejected=[]
    for name,mutate in mutations.items():
        bad=deepcopy(actual);mutate(bad)
        require(bad!=expected,'Undetected summary corruption '+name);rejected.append(name)
    dump(out/'validation/summary-verification.json',dict(verified=True,rejected_summary_mutations=rejected,
        raw_recalculation=True,new_native_executions=0,research_sample=False))
    print('Summary and measurement verification passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
