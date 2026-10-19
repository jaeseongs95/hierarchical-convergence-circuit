"""Synthetic source provider; hidden feature/fault fixtures stay behind the callback."""
from copy import deepcopy
from tools.r21_active_measurement import sensor as old
from tools.r22_measurement_adoption.policy import response_spec


def response(public,request,source,fixture,p,*,native):
    item=deepcopy(fixture);mode=item['mode']
    if mode=='weak':item['mode']='valid'
    measurement=(old.deliver if native else old.expected)(public,request,item,response_spec(source,p))
    if mode=='weak':
        for edge in measurement['observation']['edges']:edge['score']=.2 if edge['score']>0 else -.2
    return dict(measurement=measurement,acquisition_id=public['observation']['id']+':'+source+':1',
        root_measurement_ids=deepcopy(fixture['root_measurement_ids']))


def deliver(public,request,source,fixture,p):return response(public,request,source,fixture,p,native=True)
def expected(public,request,source,fixture,p):return response(public,request,source,fixture,p,native=False)
