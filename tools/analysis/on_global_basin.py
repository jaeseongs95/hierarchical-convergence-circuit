"""고정 .04 첫 ON 실수 모델의 전체 초기cube 전이를 제안한다."""
import argparse
from decimal import Decimal, Context, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import runpy

DOWN=Context(prec=80,rounding=ROUND_FLOOR)
UP=Context(prec=80,rounding=ROUND_CEILING)
QUANTUM=Decimal('1e-50')

def pinned(repo,pin):
    path=(repo/pin['path']).resolve()
    if not path.is_relative_to(repo.resolve()):raise ValueError('dependency outside repository')
    data=path.read_bytes()
    if len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']:
        raise ValueError('dependency pin mismatch')
    return path,data

def grid(box):
    return [(DOWN.quantize(a,QUANTUM),UP.quantize(b,QUANTUM)) for a,b in box]

def propose(repo,p,sha):
    deps=p['dependencies']
    for pin in deps.values():pinned(repo,pin)
    helper=runpy.run_path(str(pinned(repo,deps['proposal_helper'])[0]))
    rp=json.loads(pinned(repo,deps['root_protocol'])[1])
    bp=json.loads(pinned(repo,deps['basin_protocol'])[1])
    for pin in rp['sources']:pinned(repo,{k:pin[k] for k in ('path','sha256','bytes')})
    helper['pinned'](repo/rp['foundation']['path'],rp['foundation']['sha256'])
    record=next(m for m in bp['models'] if m['model_id']==p['model_id'])
    b,G,d=helper['model'](repo,rp,record)
    damping=helper['point'](Decimal.from_float(d))
    stay=helper['add'](helper['point'](1),helper['neg'](damping))
    root=json.loads(pinned(repo,deps['root_record'])[1])['discovery']['certificates'][3]
    box=[(Decimal(-1),Decimal(1)) for _ in range(5)]
    steps=[];entry=None
    for k in range(p['max_steps']+1):
        sides=[[format(Decimal(0) if v==0 else v,'.50f') for v in side] for side in zip(*box)]
        steps.append({'step':k,'lower':sides[0],'upper':sides[1]})
        if all(Decimal(a)<x[0]<=x[1]<Decimal(z) for a,x,z in zip(root['lower'],box,root['upper'])):
            entry=3;break
        if k==p['max_steps']:break
        z=helper['preactivation'](b,G,box)
        h=[helper['tanh_interval'](v) for v in z]
        box=grid([helper['add'](helper['mul'](stay,x),helper['mul'](damping,y)) for x,y in zip(box,h)])
    return {'schema':'HCCONGlobalBasinTrace.v1','protocol_sha256':sha,'model_id':p['model_id'],
            'state_order':p['state_order'],'initial_set':'[-1,1]^5','steps':steps,
            'proposal_status':'entered_box' if entry is not None else 'budget_exhausted','entry_certificate_index':entry}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test',action='store_true')
    for name in ('repo','protocol','protocol-sha256','output'):parser.add_argument('--'+name)
    args=parser.parse_args()
    if args.self_test:
        from fractions import Fraction
        v=Context(prec=80).divide(Decimal(1),Decimal(3))
        a,b=grid([(v,v)])[0]
        assert Fraction(a)<=Fraction(1,3)<=Fraction(b),'outward grid control'
        print('PASS outward grid control');return
    if not all((args.repo,args.protocol,args.protocol_sha256,args.output)):parser.error('all file arguments required')
    data=Path(args.protocol).read_bytes();p=json.loads(data)
    if hashlib.sha256(data).hexdigest()!=args.protocol_sha256:raise ValueError('protocol hash mismatch')
    if (p['schema']!='HCCONGlobalBasinProtocol.v1' or p['model_id']!='swapped-s004-td1-off'
        or p['max_steps']!=1000 or p['grid_places']!=50 or p['initial_x']!='[-1,1]^5'):raise ValueError('unsupported frozen protocol')
    trace=propose(Path(args.repo).resolve(),p,args.protocol_sha256)
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out:
        json.dump(trace,out,ensure_ascii=False,indent=2);out.write('\n')
    print(json.dumps({'steps':len(trace['steps'])-1,'status':trace['proposal_status'],'root':trace['entry_certificate_index']}))

if __name__=='__main__':main()
