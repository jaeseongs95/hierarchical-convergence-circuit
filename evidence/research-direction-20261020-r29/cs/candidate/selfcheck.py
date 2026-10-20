"""Synthetic structural controls, not the32census queries or native experiments."""
from copy import deepcopy
import math
import sys
from tools.r19_cross_level.probe import require
from tools.r29_research_direction import partition as producer
from tools.r29_research_direction.verify import verify

def toy():
    groups=[dict(id=k,level=0 if k!='goal' else 1,bias=0.) for k in ['a','b','goal']]
    links=[dict(source=s,target=t,weight=w,kind=kind) for s,t,w,kind in [('a','goal',1.5,'support'),('b','goal',1.5,'support'),('goal','a',.25,'top_down'),('goal','b',.25,'top_down')]]
    return dict(program=dict(groups=groups,links=links,paths=[[0,1]],edge_count=2),drives=dict(a=1.,b=1.,goal=0.),initial=dict(a=.5,b=.5,goal=.5),top_down=True,source='synthetic preparation only')

def check():
    require(sys.float_info.radix==2 and sys.float_info.mant_dig==53 and sys.float_info.max_exp==1024,'binary64 platform')
    entry=toy();plan=producer.analyze(entry);v=verify(entry,plan);require(['a','b'] in plan['classes'] and v['nontrivial_classes']==1,'synthetic symmetric opportunity')
    rejected={}
    def reject(name,e,p):
        try:verify(e,p)
        except ValueError as exc:rejected[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    for name in ['drive_ulp','initial','bias','weight','source','flag']:
        bad=deepcopy(entry)
        if name=='drive_ulp':bad['drives']['b']=math.nextafter(1.,2.)
        elif name=='initial':bad['initial']['b']=.25
        elif name=='bias':bad['program']['groups'][1]['bias']=math.nextafter(0.,1.)
        elif name=='weight':bad['program']['links'][3]['weight']=.5
        elif name=='source':bad['source']='different source'
        else:bad['top_down']=False
        reject(name,bad,plan)
        if name in ['drive_ulp','initial','bias','weight']:
            independent=producer.analyze(bad);verify(bad,independent);require(all(not {'a','b'}<=set(c) for c in independent['classes']),'asymmetry separates class')
    for name in ['false_negative','false_positive','coverage','ledger']:
        bad=deepcopy(plan)
        if name=='false_negative':bad['classes']=[['a'],['b'],['goal']];bad['ledger']=producer.ledger(entry,bad['classes'])
        elif name=='false_positive':bad['classes']=[['a','b','goal']];bad['ledger']=producer.ledger(entry,bad['classes'])
        elif name=='coverage':bad['classes'][0].append('a')
        else:bad['ledger']['projected_group_updates_omitted_per_tick']+=1
        reject(name,entry,bad)
    ordered=toy();ordered['program']['groups']=[dict(id=k,level=0 if k.startswith('s') else 1,bias=1. if k=='goal' else 0.) for k in ['s0','s1','x','y','goal']]
    ordered['drives']=dict(s0=1.,s1=2.);ordered['initial']={g['id']:.5 for g in ordered['program']['groups']}
    ordered['program']['links']=[dict(source=s,target=t,weight=w,kind='support') for s,t,w in [('s0','x',1.),('s1','x',2.),('s1','y',2.),('s0','y',1.)]]
    p=producer.analyze(ordered);verify(ordered,p);require(all(not {'x','y'}<=set(c) for c in p['classes']),'ordered incoming rows differ')
    p['classes']=[['s0'],['s1'],['x','y'],['goal']];p['ledger']=producer.ledger(ordered,p['classes']);reject('sum_equal_order_changed',ordered,p)
    duplicate=toy();duplicate['program']['links'].append(deepcopy(duplicate['program']['links'][2]));p=producer.analyze(duplicate);verify(duplicate,p);require(all(not {'a','b'}<=set(c) for c in p['classes']),'duplicate edge retained')
    zero=toy();zero['drives']['b']=-0.;zero['drives']['a']=0.;p=producer.analyze(zero);verify(zero,p);require(all(not {'a','b'}<=set(c) for c in p['classes']),'signed zero conservative label')
    return dict(status='SYNTHETIC_STRUCTURAL_CHECKS_PASS',positive_fixture=1,asymmetry_fixtures=4,order_duplicate_signed_zero_fixtures=3,targeted_rejections=rejected,
        native_tick_calls=0,native_settle_calls=0,training_calls=0,world_measure_calls=0,census_queries_analyzed=0,new_timing_runs=0)
