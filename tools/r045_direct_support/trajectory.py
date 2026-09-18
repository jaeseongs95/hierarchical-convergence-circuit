"""Generic evaluator-only ID projection; no EXP23 seven-edge map or hardcoded S path."""
from copy import deepcopy
from .storage import digest, require


def canonical_assumptions(items, inverse):
    if items is None: return None
    result = []
    for edge, value in items:
        require(edge in inverse and type(value) is bool, 'proof assumption identity/type')
        result.append([inverse[edge], value])
    return sorted(result)


def describe(run, record, case):
    from r041_scheduler_direction.trial_audit import candidate_view
    before = digest(run); obs = case['observation']
    inverse = {v:k for k,v in case['manipulation']['edge_map'].items()}
    def path(slots):
        require(type(slots) is list and all(type(i) is int and 0 <= i < len(obs['edges']) for i in slots), 'path slots')
        return [inverse[obs['edges'][i]['id']] for i in slots]
    def proof_path(ids):
        require(all(e in inverse for e in ids), 'proof edge IDs')
        return [inverse[e] for e in ids]
    base = run['base']; timeline = []
    require(len(base['candidates']) == len(record['readouts']), 'readout/candidate cardinality')
    for candidate, row in zip(base['candidates'], record['readouts']):
        view = candidate_view(candidate)
        require(view['observation'] == obs, 'readout observation changed')
        paths = [path(p) for p in view['completed_paths']]
        state = view['state']
        aligned = dict(edges=sorted([[inverse[e['id']], state['e:' + str(i)]] for i,e in enumerate(obs['edges'])]),
                       goal=state['goal'], prefixes=[])
        for pi, slots in enumerate(view['completed_paths']):
            for j in range(len(slots)):
                aligned['prefixes'].append(dict(route=path(slots), prefix=path(slots[:j+1]), activation=state[f'p:{pi}:{j}']))
        aligned['prefixes'].sort(key=lambda x:(x['route'],x['prefix']))
        timeline.append(dict(ordinal=row['ordinal'], ticks=row['kernel_ticks_at_readout'],
            raw_value=row['raw_value'], native_accepted=row['native_accepted'], native_value=row['native_value'],
            policy_accepted=row['policy_accepted'], policy_value=row['policy_value'],
            frontier_count=row['frontier_count'], completed_paths=paths,
            native_D_DAG=row['native_D_DAG'], policy_D_DAG=row['D_DAG'],
            native_assumptions=canonical_assumptions(row['native_assumptions'],inverse),
            selected_assumptions=canonical_assumptions(row['selected_assumptions'],inverse), state=aligned))
    final = record['final']; projection = None
    if final['accepted']:
        index = final['readout_ordinal']; proof = base['selections'][index]['proof']
        require(proof is not None, 'accepted without selected proof')
        projection = dict(value=final['value'], D_DAG=record['readouts'][index]['D_DAG'],
            assumed_edges=canonical_assumptions(proof['assumed_edges'],inverse),
            paths=[proof_path(p) for p in proof['paths']])
    terminal = base['packet']['document']['engine']['pending']['workspace']['routes']
    require(digest(run) == before, 'projection changed native artifacts')
    return dict(inverse_mapping=inverse, canonical_readouts=timeline,
        canonical_readout_sha256=digest(timeline) if timeline else None,
        terminal_canonical_paths=[path(p['path']) for p in terminal], final_support_signature=projection,
        minimal_goal_proof_DAG_isomorphism=None,
        proof_metric_scope='validated selected proof D_DAG and support projection, not minimum-DAG isomorphism',
        native_artifacts_modified=False)
