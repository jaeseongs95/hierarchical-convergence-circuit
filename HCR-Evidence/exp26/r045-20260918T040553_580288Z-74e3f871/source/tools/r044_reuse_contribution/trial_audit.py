"""R041 trial accounting, now with an explicitly audited native reuse switch."""
from copy import deepcopy
from r038_early_adoption import metrics
from r041_scheduler_direction.trial_audit import candidate_view, check_wrapper
from .storage import require as demand, digest

def audit_trial(run: dict, trial: dict, case: dict, seed: dict, conditions: dict) -> dict:
    from .native_audit import audit_native, reachable
    demand(run['backend'] == 'native_hcr', '본 실험 audit에 synthetic backend 혼입')
    policy = {'native':'native_saved','posthoc_support':'native_saved','online_support':'support_first'}[trial['arm']]
    base_trial = dict(id=trial['id'],case=trial['case'],scope=trial['scope'],policy=policy,scheduler=trial['scheduler'],use_circuits=trial['use_circuits'])
    report, rows = audit_native(run['base'],case['observation'],seed,base_trial,conditions,case)
    wrapper = check_wrapper(run,trial)
    for index,(candidate,output) in enumerate(zip(run['base']['candidates'],run['base']['selections'])):
        view = candidate_view(candidate)
        count = metrics.frontier_at(run['base'],candidate)
        demand(view['graph_complete'] is (count == 0), 'readout graph_complete/frontier 불일치')
        row = rows[index]
        row.update(metrics.opportunity(view,candidate['readout']['accepted'],count))
        row.update(arm=trial['arm'],cohort=case['cohort'],
                   native_assumption_counts=metrics.assumption_counts(view,view['original_proof']),
                   selected_assumption_counts=metrics.assumption_counts(view,output['proof']))
        sr = report['selections'][index]
        sr['legacy_field_meant_assumptions_checked'] = sr.pop('supported_assumptions')
        sr.update(row['selected_assumption_counts'])
    final = run['final']; value = final['value']
    worlds = {name:dict(expected=reachable(case['observation'],w),external_correct=None if value is None else
                       value is reachable(case['observation'],w)) for name,w in case['worlds'].items()}
    core = run['base']['packet']['document']['engine']
    native_cost = deepcopy(core['pending']['cost'])
    demand(native_cost['kernel_ticks'] == run['usage']['native_kernel_ticks'], '최종 누적 native 비용')
    final_proof = None
    if final['accepted']:
        final_proof = (run['posthoc_selection']['proof'] if trial['arm'] == 'posthoc_support'
                       else run['base']['selections'][final['readout_ordinal']]['proof'])
    final_counts = (None if not run['base']['candidates'] else
                    metrics.assumption_counts(candidate_view(run['base']['candidates'][-1]),final_proof))
    semantic = metrics.semantic_events(run['base']['packet']['document']['events'])
    return dict(trial=trial,cohort=case['cohort'],scheduler_usage=run['base']['scheduler_usage'],audit=report,wrapper=wrapper,readouts=rows,
        final=final,world_results=worlds,classification=metrics.correctness(value,worlds),
        final_assumption_counts=final_counts,native_cost=native_cost,usage=run['usage'],
        native_finish_proof_nodes=sum(len(c['decision']['proof']['nodes']) for c in run['base']['candidates']),
        native_capture_scan_checks=None,unmeasured_cost_is_zero=False,
        native_event_semantic_hashes=[digest(e) for e in semantic],
        final_frontier_count=len(core['pending']['workspace']['frontier']),
        terminal_pending_ready=run['base']['terminal_pending_ready'],
        base_stop_reason=run['base']['adoption']['reason'])

