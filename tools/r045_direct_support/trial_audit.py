"""Reuse the pinned independent native/state/proof/controller auditor, then add measurements."""
from .storage import digest, require


def audit_trial(run, trial, case, seed, conditions):
    from r044_reuse_contribution.trial_audit import audit_trial as previous_audit
    from r044_reuse_contribution.gate_audit import measure_execution
    from r044_reuse_contribution.policy_audit import check
    from .measurements import measure
    from .trajectory import describe
    before = digest(run)
    record = previous_audit(run,trial,case,seed,conditions)
    record.update(family=case['family'], id_variant=case['id_variant'],
                  reported_wall_seconds=run['wall_seconds'])
    record['reuse_measurements'] = measure_execution(run,trial,case)
    record['direct_measurements'] = measure(run,trial,case,record['reuse_measurements'])
    record['diagnostics'] = describe(run,record,case)
    record['input_order_policy_audit'] = check(run['base'])
    require(digest(run) == before, 'auditor changed raw run')
    return record
