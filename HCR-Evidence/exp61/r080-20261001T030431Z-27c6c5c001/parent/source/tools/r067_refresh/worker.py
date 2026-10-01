"""Explicit baseline controller and unchanged native inference; no private truth access."""
import argparse
from copy import deepcopy
from itertools import product
from pathlib import Path
from tools.r050_review_boundary.common import dump, fingerprint, load, require, seal, unseal
from tools.r063_formation.worker import execute


def request_for(plan, arm):
    require(arm in plan['arms'], 'Unknown arm')
    if arm == 'history':
        return None
    return dict(controller='explicit_baseline', edge_id='e1', source='v1', target='v2',
        scope=plan['fact_scope'], requested_at=1, budget=1,
        channel='cached' if arm == 'stale' else 'current')


def prepare(plan, arm, response):
    original = plan['observation']; actual = deepcopy(original)
    old = plan['old_fact']; request = request_for(plan, arm)
    require(old['edge_id'] == 'e1' and type(old['value']) is bool, 'Historical fact')
    status = 'history'; score = -1.0 if old['value'] is False else 1.0
    stored = [old]; valid_at = old['valid_at']
    if request is not None:
        require(response is not None and response['request'] == request, 'Response request binding')
        require(response['delivered_at'] == 1 and response['source'] ==
            ('cached_original' if arm == 'stale' else 'ideal_current_sensor'), 'Response provenance')
        require(response['valid_at'] == (0 if arm == 'stale' else 1), 'Measurement freshness')
        status = response['status']; require(status in ('measured', 'unknown', 'conflict'), 'Response status')
        score = response['score']; valid_at = response['valid_at']
        if status == 'measured':
            require(type(score) in (int, float) and score in ((0.8,) if arm == 'stale' else (-1.0, 1.0)), 'Measured score')
        else:
            require(score is None, 'Unknown/conflict cannot encode False')
        if arm == 'fresh' and status == 'measured':
            stored = [dict(**{k: old[k] for k in ('context','epoch','edge_id','source','target')},
                value=score > 0, valid_at=1, provenance=dict(response_sha256=fingerprint(response)))]
    else:
        require(response is None, 'History must not get a measurement')
    if score is not None:
        actual['edges'][1]['score'] = score
    # The whole observation ID/revision and e0 remain fixed; freshness is logged outside native input.
    return dict(arm=arm, controller='explicit_baseline', request=request, response=response,
        original_input=original, actual_input=actual, status=status, valid_at=valid_at,
        prior_conflict=(original['edges'][1]['score'] > 0) != old['value'],
        stored_before=[old], stored_after=stored, persistence_used_in_this_decision=False,
        input_changed=actual != original,
        cost=dict(additional_observation_budget=1, observation_calls=int(request is not None),
            current_measurement_calls=int(arm == 'fresh'), stale_presentations=int(arm == 'stale'),
            fact_reads=1, fact_value_writes=int(arm == 'fresh' and status == 'measured'),
            conflict_comparisons=1, information_gain_bits=None))


def main(out):
    plan = load(out/'plan.json'); memory = load(out/'parent/memory/after_correction.json')
    for slot, arm, gate in product(plan['slots'], plan['arms'], (False, True)):
        identity = f"{slot}-{arm}-{'on' if gate else 'off'}"; where = out/'evaluation'/identity
        initial = execute(plan, dict(observation=plan['observation']), memory, gate,
            'frozen_eval', where/'before/progress', 'r067-'+identity+'-before')
        dump(where/'before/inference.json', seal(dict(schema='hcc-r067-inference-v1', execution=initial,
            identity=identity, phase='before', plan_sha256=fingerprint(plan))))
        request = request_for(plan, arm)
        dump(where/'request.json', dict(request=request, after_initial_inference=True))
        response = None if request is None else unseal(load(out/'measurements'/f'{identity}.json'), 'hcc-r067-response-v1')['response']
        prepared = prepare(plan, arm, response); dump(where/'input.json', prepared)
        final = execute(plan, dict(observation=prepared['actual_input']), memory, gate,
            'frozen_eval', where/'after/progress', 'r067-'+identity+'-after')
        dump(where/'after/inference.json', seal(dict(schema='hcc-r067-inference-v1', execution=final,
            identity=identity, phase='after', plan_sha256=fingerprint(plan), input_sha256=fingerprint(prepared))))
        print(identity, 'before/after recorded', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True); main(p.parse_args().out)
