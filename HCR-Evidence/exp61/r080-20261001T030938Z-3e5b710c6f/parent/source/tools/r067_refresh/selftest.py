"""Synthetic boundary checks, not research observations."""
import argparse
from copy import deepcopy
from pathlib import Path
from tools.r050_review_boundary.common import dump, load, require
from .worker import prepare, request_for


def main(out):
    plan = load(out/'plan.json'); passed = []
    def response(status='measured', score=-1.0):
        return dict(request=request_for(plan,'fresh'),delivered_at=1,valid_at=1,
            source='ideal_current_sensor',status=status,score=score)
    for status in ('unknown','conflict'):
        result = prepare(plan,'fresh',response(status,None))
        require(result['status']==status and result['actual_input']==plan['observation']
            and result['stored_before']==result['stored_after'], 'No invented measurement')
        passed.append(status)
    result=prepare(plan,'fresh',response());require(result['actual_input']['edges'][1]['score']==-1.0,'False measurement')
    require(result['stored_after'][0]['value'] is False,'False stored explicitly');passed.append('false_not_unknown')
    result=prepare(plan,'history',None);require(result['cost']['observation_calls']==0,'No phantom calls');passed.append('history_zero_calls')
    changes=[('wrong_edge',lambda x:x['request'].update(edge_id='e0')),
        ('wrong_scope',lambda x:x['request']['scope'].update(epoch=42)),
        ('old_timestamp',lambda x:x.update(valid_at=0)),
        ('unknown_false',lambda x:x.update(status='unknown',score=-1.0)),
        ('boolean_score',lambda x:x.update(score=True)),
        ('wrong_source',lambda x:x.update(source='cached_original'))]
    for name, mutate in changes:
        bad=deepcopy(response());mutate(bad)
        try:prepare(plan,'fresh',bad)
        except ValueError:passed.append(name)
        else:raise AssertionError('Not rejected: '+name)
    require(plan==load(out/'plan.json'),'No in-place plan mutation');passed.append('immutable_plan')
    dump(out/'validation/selftest.json',dict(passed=passed,synthetic=True,new_native_executions=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
