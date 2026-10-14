"""동일 first ON 그래프의 현지 native 재생과 실수 interval 제안. 최종 판정은 별도 checker."""
import argparse
from decimal import Decimal, Context, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import platform
import runpy
import sys
import time


def pinned(repo, ref):
    data=(repo/ref['path']).read_bytes()
    if len(data)!=ref['bytes'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:
        raise ValueError('source pin mismatch')
    return data


def policy(trace, settings, margin_threshold):
    stable=0
    tolerance=float.fromhex(settings['tolerance_hex'])
    for n in range(1,settings['cap']+1):
        before,after=trace[n-1],trace[n]
        residual=max(abs(a-b) for a,b in zip(after,before))
        stable=stable+1 if residual<=tolerance else 0
        margin=abs(2*after[-1]-1)
        status=None
        if stable>=settings['patience']:
            status='stable_decision' if margin>=margin_threshold else 'stable_ambiguous'
        elif n>=2 and residual>tolerance*10 and max(abs(a-b) for a,b in zip(after,trace[n-2]))<tolerance:
            status='oscillating'
        elif n==settings['cap']:
            status='budget_exhausted'
        if status:
            return dict(status=status,tick=n,state_hex=[x.hex() for x in after],
                        residual_hex=residual.hex(),margin_hex=margin.hex(),stable_steps=stable,
                        residual_dominant=[i for i,(a,b) in enumerate(zip(after,before)) if abs(a-b)==residual])
    raise ValueError('missing policy result')


def main(args):
    repo=Path(args.repo).resolve()
    data=Path(args.protocol).read_bytes()
    if hashlib.sha256(data).hexdigest()!=args.protocol_sha256:raise ValueError('protocol pin mismatch')
    proto=json.loads(data)
    for ref in proto['sources']:pinned(repo,ref)
    raws=[json.loads(pinned(repo,r)) for r in proto['raw']]
    events=raws[0]['execution']['packet']['document']['events']
    cfg=next(e['payload']['config']['kernel'] for e in events if e['event']=='r02_engine_created')
    net=next(e['payload'] for e in events if e['event']=='r02_network' and e['payload']['network_id']==proto['network_id'])
    sys.path.insert(0,str(repo/'src'))
    from hcr.model import Config,Group,Link,Program,Cost
    from hcr.dynamics import tick,settle
    config=Config(**cfg)
    program=Program(tuple(Group(**g) for g in net['program']['groups']),tuple(Link(**e) for e in net['program']['links']),
                    tuple(tuple(p) for p in net['program']['paths']),net['program']['edge_count'])
    order=proto['state_order']
    if [g.id for g in program.groups]!=order or not net['top_down']:raise ValueError('ordered graph mismatch')
    replay=[]
    for raw,ref in zip(raws,proto['raw']):
        es=raw['execution']['packet']['document']['events']
        nt=next(e['payload'] for e in es if e['event']=='r02_network' and e['payload']['network_id']==proto['network_id'])
        actual=[]
        state,convergence=settle(program,nt['drives'],config,Cost(),top_down=True,
            observe=lambda n,p,r,s:actual.append({'tick':n,'state':p,'residual':r,'stable_steps':s}))
        recorded=[e['payload'] for e in es if e['event']=='r02_tick' and e['payload']['network_id']==proto['network_id']]
        same=len(actual)==len(recorded) and all(all(a[k]==r[k] for k in ('tick','state','residual','stable_steps')) for a,r in zip(actual,recorded))
        replay.append({'model_id':ref['model_id'],'bitwise_equal':same,'ticks':convergence.ticks,'status':convergence.status.value})
        if not same:raise ValueError('raw replay fidelity mismatch: '+ref['model_id'])
    helper=runpy.run_path(str(repo/'tools/analysis/on_fixed_points.py'))
    P,A,M=helper['point'],helper['add'],helper['mul']
    D=Decimal.from_float
    b=[A(P(D(g.bias)),P(D(net['drives'].get(g.id,0.0)))) for g in program.groups]
    matrix=[[P(0) for _ in order] for _ in order]
    for edge in program.links:
        i,j=order.index(edge.target),order.index(edge.source)
        matrix[i][j]=A(matrix[i][j],P(D(edge.weight)))
    diagonal=helper['div'](A(P(D(cfg['self_excitation'])),P(D(cfg['inhibition']))),P(2))
    for i in range(7):matrix[i][i]=A(matrix[i][i],diagonal)
    damping=P(D(cfg['damping']));keep=A(P(1),helper['neg'](damping))
    unit=Decimal('1e-'+str(proto['arithmetic']['interval_grid_places']))
    down=Context(prec=80,rounding=ROUND_FLOOR);up=Context(prec=80,rounding=ROUND_CEILING)
    def encode(box):return [[format(down.quantize(l,unit),'f'),format(up.quantize(h,unit),'f')] for l,h in box]
    results=[];started=time.monotonic()
    for sample in proto['scores']:
        drive=net['drives'].copy();drive['e:1']=4.0*float.fromhex(sample['hex'])
        current={key:.5 for key in order};trace=[[current[k] for k in order]];cost=Cost()
        for _ in range(proto['budget']['native_forced_ticks']):
            current=tick(program,current,drive,config,cost,top_down=True)
            trace.append([current[k] for k in order])
        bb=b.copy();bb[order.index('e:1')]=P(D(drive['e:1']))
        box=[P(0) for _ in order];boxes=[]
        for _ in range(proto['budget']['real_prefix_ticks']):
            z=helper['preactivation'](bb,matrix,box)
            image=[helper['tanh_interval'](v) for v in z]
            nxt=[A(M(keep,p),M(damping,h)) for p,h in zip(box,image)]
            encoded=encode(nxt);box=[(Decimal(l),Decimal(h)) for l,h in encoded];boxes.append(encoded)
        trace_bytes='\n'.join(','.join(p.hex() for p in state) for state in trace).encode('ascii')
        results.append({'id':sample['id'],'score_hex':sample['hex'],'drive_hex':drive['e:1'].hex(),
            'native_full_trace_sha256':hashlib.sha256(trace_bytes).hexdigest(),
            'native_prefix_hex':[[p.hex() for p in state] for state in trace[:161]],'real_x_boxes':boxes,
            'policies':{p['id']:policy(trace,p,cfg['margin_threshold']) for p in proto['policies']},
            'checkpoints':{str(n):[p.hex() for p in trace[n]] for n in proto['native_checkpoints']}})
        print(sample['id']+' prepared',flush=True)
        if time.monotonic()-started>proto['budget']['wall_time_seconds']:raise ValueError('wall budget')
    record={'schema':'HCCONNativeStopProposal.v1','protocol_sha256':args.protocol_sha256,'replay':replay,
       'environment':{'python':sys.version,'platform':platform.platform(),'implementation':platform.python_implementation()},'samples':results}
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--protocol',required=True)
    parser.add_argument('--protocol-sha256',required=True);parser.add_argument('--output',required=True)
    main(parser.parse_args())
