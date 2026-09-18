"""Evaluator-only exposure stages and per-decision computation signatures.

The R044 event accounting and independent native replay must precede this module.
No runtime, pool, matcher or selector implementation is imported here.
"""
from copy import deepcopy
from functools import wraps
from .storage import digest, require


def _path(slots, obs, inverse):
    require(type(slots) is list and all(type(i) is int and 0 <= i < len(obs['edges']) for i in slots), 'measurement slot')
    return [inverse[obs['edges'][i]['id']] for i in slots]


class MeasurementError(ValueError):
    """Additional exposure/signature accounting disagrees with validated raw events."""


def measurement_boundary(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise MeasurementError(str(exc)) from exc
    return wrapped


@measurement_boundary
def measure(run, trial, case, counts):
    before = digest(run)
    doc = run['base']['packet']['document']; cfg = doc['engine']['config']
    pending = doc['engine']['pending']; cost = pending['cost']
    inverse = {v:k for k,v in case['manipulation']['edge_map'].items()}
    obs = case['observation']; networks = {}; decisions = []; binding_rows = []; candidates = []
    matched = 0
    for event in doc['events']:
        name, p = event['event'], event['payload']
        if name == 'r02_binding_scan':
            matched += len(p['matched'])
            binding_rows.append(dict(event_seq=event['seq'], inspected=len(p['inspected']),
                edge_scans=len(p['scans']), matched=len(p['matched']), complete=p['complete'],
                fallback_reason=p['fallback_reason'],
                prefix=_path(p['prefix']['path'], obs, inverse)))
        elif name == 'r02_network':
            nid = p['network_id']
            require(nid not in networks, 'duplicate network identity')
            signature = dict(program=p['program'], drives=p['drives'], top_down=p['top_down'])
            networks[nid] = dict(network_id=nid, kind=p['kind'],
                program_drive_sha256=digest(signature), ticks=[], settled=None)
        elif name == 'r02_tick':
            n = networks[p['network_id']]
            require(p['tick'] == len(n['ticks']) + 1, 'decision signature tick sequence')
            n['ticks'].append({k:deepcopy(p[k]) for k in ('tick', 'state', 'residual', 'stable_steps')})
        elif name == 'r02_settled':
            n = networks[p['network_id']]
            n['settled'] = deepcopy(p['convergence'])
            require(len(n['ticks']) == p['convergence']['ticks'], 'signature/settle count')
        elif name == 'r02_pool_result':
            n = networks[p['network_id']]
            require(n['kind'] == 'pool' and n['settled'] is not None, 'pool result without settled pool')
            stable = n['settled']['status'] in ('stable_decision', 'stable_ambiguous')
            for a in p['activations']:
                reasons = []
                if not stable: reasons.append('pool_not_stable')
                if a['activation'] < cfg['activation_threshold']: reasons.append('activation_below_threshold')
                if a['mismatch'] > cfg['mismatch_threshold']: reasons.append('mismatch_above_threshold')
                require(type(a['eligible']) is bool and a['eligible'] is (not reasons), 'eligibility decomposition disagrees')
                candidates.append(dict(event_seq=event['seq'], network_id=p['network_id'], circuit_id=a['circuit_id'],
                    circuit_version=a['circuit_version'], canonical_span=_path(a['binding']['edge_order'], obs, inverse),
                    activation=a['activation'], mismatch=a['mismatch'], prior=a['prior'], eligible=a['eligible'],
                    rejection_reasons=reasons))
    require(type(cost['candidate_circuits']) is int and matched == cost['candidate_circuits'], 'matched candidate accounting')
    for n in networks.values():
        require(n['settled'] is not None, 'unfinished signature network')
        if n['kind'] == 'decision':
            decisions.append(dict(ordinal=len(decisions), network_id=n['network_id'],
                program_drive_sha256=n['program_drive_sha256'], kernel_ticks=len(n['ticks']),
                dynamics_sha256=digest(dict(ticks=n['ticks'], convergence=n['settled'])),
                convergence=deepcopy(n['settled'])))
    require(len(decisions) == counts['decision_networks'] and
        sum(d['kernel_ticks'] for d in decisions) == counts['decision_kernel_ticks'], 'decision signature accounting')
    route = counts['adopted_route']
    positive_adoption = run['final']['accepted'] is True and run['final']['value'] is True
    direct = None
    if positive_adoption and route is not None:
        require(type(route['circuit_uses']) is list, 'adopted circuit use schema')
        direct = bool(route['circuit_uses'])
        require(not direct or (trial['use_circuits'] and counts['macro_actions'] > 0), 'direct use without macro exposure')
    if not trial['use_circuits']:
        require(not binding_rows and not candidates and matched == 0, 'OFF candidate exposure')
    signature_sequence = [{k:d[k] for k in ('program_drive_sha256','dynamics_sha256','kernel_ticks')} for d in decisions]
    result = dict(verified=True, binding_rows=binding_rows, matched_candidates=matched,
        pool_candidate_evaluations=len(candidates), eligible_candidate_evaluations=sum(a['eligible'] for a in candidates),
        mismatch_rejected_evaluations=sum('mismatch_above_threshold' in a['rejection_reasons'] for a in candidates),
        candidates=candidates, decision_networks=decisions,
        decision_signature_sequence=signature_sequence,
        positive_adoption=positive_adoption, direct_circuit_use=direct,
        direct_circuit_use_count=None if direct is None else len(route['circuit_uses']),
        direct_canonical_route=None if not positive_adoption or route is None else deepcopy(route['canonical_IDs']),
        directness_scope='explicit_use_on_positive_adopted_route; negative_cut_or_no_route:null',
        candidate_counts_are_independent_samples=False, signatures_exclude_event_identifiers=True,
        memory_or_energy_savings_inferred=False)
    require(digest(run) == before, 'measurements modified raw run')
    return result
