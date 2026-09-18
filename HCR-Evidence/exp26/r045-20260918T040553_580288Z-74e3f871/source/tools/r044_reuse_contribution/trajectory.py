"""The R042 evaluator-only projection is retained; signature and path inventory are split."""
from copy import deepcopy
from r042_id_role_isolation.trajectory import describe as previous_describe
from .storage import digest, require


def describe(run, record, case):
    before = digest(run)
    result = previous_describe(run, record, case)
    projection = result['final_proof_projection']
    result['final_support_signature'] = (None if projection is None else dict(
        value=record['final']['value'], D_DAG=projection['D_DAG'],
        assumed_edges=deepcopy(projection['assumed_edges'])))
    result['completed_path_inventory'] = deepcopy(result['terminal_canonical_paths'])
    result['minimal_goal_proof_DAG_isomorphism'] = None
    result['proof_metric_scope'] = 'support signature is not full or minimal proof DAG identity'
    require(digest(run) == before, 'evaluator modified raw run')
    return result
