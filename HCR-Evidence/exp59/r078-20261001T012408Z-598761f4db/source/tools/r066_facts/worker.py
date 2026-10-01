"""Consume requested measurements, retrieve scoped facts, then run unchanged native inference."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import canonical, dump, fingerprint, load, require, seal, sha, unseal
from tools.r063_formation.worker import execute


def records(parent, scope):
    request = unseal(load(parent/'request.json'), 'hcc-r064-request-v1')['request']
    measured = unseal(load(parent/'measurements.json'), 'hcc-r064-measurements-v1')
    require(request is not None, 'No requested correction available')
    obs = measured['observations']['corrected_observation']
    require(obs['revision'] == request['revision'] and obs['episode_id'] == request['episode_id'], 'Requested measurement identity')
    result = []
    for edge in obs['edges']:
        if edge['id'] in request['edge_ids']:
            require(edge['score'] in (-1.0, 1.0), 'Only explicit Boolean measurements')
            result.append(dict(**scope, edge_id=edge['id'], source=edge['source'], target=edge['target'],
                value=edge['score'] == 1.0, provenance=dict(file='parent/measurements.json',
                sha256=sha((parent/'measurements.json').read_bytes()), request_sha256=measured['request_sha256'],
                episode_id=obs['episode_id'], revision=obs['revision'])))
    require(len(result) == len(request['edge_ids']), 'Missing requested edge')
    return result


def lookup(table, scope, observation):
    """A linear scan is sufficient for the frozen two-record baseline."""
    output = deepcopy(observation); queries = []; checks = 0
    for edge in output['edges']:
        matches = []
        for fact in table:
            checks += 1
            require(type(fact['value']) is bool and type(fact['epoch']) is int, 'Fact types')
            if (fact['context'], fact['epoch'], fact['edge_id']) == (scope['context'], scope['epoch'], edge['id']):
                require((fact['source'], fact['target']) == (edge['source'], edge['target']), 'Edge identity rebound')
                matches.append(fact)
        values = {fact['value'] for fact in matches}
        status = 'unknown' if not values else 'conflict' if len(values) > 1 else 'hit'
        value = next(iter(values)) if status == 'hit' else None
        queries.append(dict(edge_id=edge['id'], status=status, value=value, records=matches))
        if status == 'hit': edge['score'] = 1.0 if value else -1.0
    return dict(queries=queries, comparisons=checks, actual_input=output)


def prepare(parent, plan, case, channel, arm):
    supplied = records(parent, plan['fact_scope']) if channel == 'edge_correction' else []
    table = supplied if arm != 'current' else []
    queried = lookup(table, case['scope'], case['observation']) if arm == 'lookup' else dict(
        queries=[], comparisons=0, actual_input=deepcopy(case['observation']))
    hits = sum(q['status'] == 'hit' for q in queried['queries'])
    return dict(channel=channel, arm=arm, scope=case['scope'], original_input=case['observation'],
        supplied_facts=supplied, stored_facts=table, **queried,
        explicit_input_intervention=queried['actual_input'] != case['observation'],
        cost=dict(binary_correctness_payload_bits=1, supplied_edge_value_bits=len(supplied),
            stored_edge_value_bits=len(table), retrieved_edge_value_bits=hits,
            table_serialized_bytes=len(canonical(table)), lookup_queries=len(queried['queries']),
            record_comparisons=queried['comparisons'], prior_measurement_edge_values=len(supplied),
            new_external_measurement_calls=0, original_observation_presentations=1,
            native_observation_presentations=1, information_gain_bits=None))


def main(out):
    plan = load(out/'plan.json')
    for channel, snapshot in plan['channels'].items():
        memory = load(out/'parent/memory'/f'{snapshot}.json')
        for arm in plan['arms']:
            for gate in (False, True):
                for case in plan['cases']:
                    identity = f"{channel}-{arm}-{'on' if gate else 'off'}-{case['id']}"
                    where = out/'evaluation'/identity
                    prepared = prepare(out/'parent', plan, case, channel, arm)
                    dump(where/'input.json', prepared)
                    e = execute(plan, dict(observation=prepared['actual_input']), memory, gate,
                        'frozen_eval', where/'progress', 'r066-'+identity)
                    dump(where/'inference.json', seal(dict(schema='hcc-r066-inference-v1', identity=identity,
                        plan_sha256=fingerprint(plan), input_sha256=sha((where/'input.json').read_bytes()),
                        channel=channel, arm=arm, use_circuits=gate, case=case['id'], execution=e)))
                    print(identity, 'recorded', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    main(p.parse_args().out)
