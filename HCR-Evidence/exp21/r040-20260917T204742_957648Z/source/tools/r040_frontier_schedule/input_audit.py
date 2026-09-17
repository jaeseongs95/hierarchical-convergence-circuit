"""원 입력 검산은 EXP20을 유지하고 72개 treatment 순서를 별도 검산한다."""
from r039_order_isolation.input_audit import check_cases, check_canonical
from .contracts import demand


def check_trial_schedule(rows):
    expected=[]
    cells=(('input_order','native'),('input_order','posthoc_support'),('input_order','online_support'),
           ('edge_id_min','native'),('edge_id_min','posthoc_support'),('edge_id_min','online_support'))
    for i,order in enumerate(('SMD','SDM','MSD','MDS','DSM','DMS')):
        for j,prior in enumerate(('legacy','route_only')):
            for n in range(6):
                scheduler,arm=cells[(i+j+n)%6]
                expected.append(dict(id='t%04d'%len(expected),case='order_'+order,scope=prior,arm=arm,scheduler=scheduler))
    demand(rows==expected,'EXP21 미등록/누락/중복 treatment 또는 동결 순서 변경')
