"""Synthetic table boundary tests, separate from native research executions."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require
from .worker import lookup, records, prepare


def main(out):
    plan = load(out/'plan.json'); case = plan['cases'][0]; scope = plan['fact_scope']
    table = records(out/'parent', scope); obs = case['observation']; passed = []
    for name, query, expected in [('match', scope, ['hit','hit']),
            ('context', dict(context='different',epoch=0), ['unknown','unknown']),
            ('epoch', dict(context=scope['context'],epoch=1), ['unknown','unknown'])]:
        r = lookup(table, query, obs); require([x['status'] for x in r['queries']] == expected, name)
        if name != 'match': require(r['actual_input'] == obs, 'Unknown must preserve input')
        passed.append(name)
    conflict = deepcopy(table); conflict.append(dict(table[1],value=not table[1]['value']))
    r = lookup(conflict, scope, obs)
    require(r['queries'][1]['status'] == 'conflict' and r['queries'][1]['value'] is None
        and r['actual_input']['edges'][1] == obs['edges'][1], 'Conflict must not select a fact')
    passed.append('conflict_preserves_original')
    require(lookup([],scope,obs)['actual_input'] == obs, 'Empty is unknown'); passed.append('empty_unknown')
    for name, field, value in [('bool_type','value',0),('epoch_type','epoch','0'),('identity','source','other')]:
        bad = deepcopy(table); bad[0][field] = value
        try: lookup(bad,scope,obs)
        except ValueError: passed.append(name)
        else: raise AssertionError('Did not reject '+name)
    for arm in plan['arms']:
        r = prepare(out/'parent',plan,case,'binary_feedback',arm)
        require(r['stored_facts'] == [] and not r['explicit_input_intervention'], 'No edge inference from binary')
    passed.append('binary_never_infers_edge')
    r = prepare(out/'parent',plan,case,'edge_correction','record_only')
    require(len(r['stored_facts']) == 2 and r['queries'] == [] and r['actual_input'] == obs, 'Record-only')
    passed.append('record_only_does_not_read')
    require(table == records(out/'parent',scope) and obs == case['observation'], 'No in-place mutation')
    dump(out/'validation/selftest.json',dict(passed=passed,synthetic=True,new_native_executions=0))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
