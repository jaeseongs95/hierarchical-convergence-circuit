"""첫 ON 연속 실수 가족의 전체 평형 분류를 위한 조건부 상자를 제안한다."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path

def read_pin(repo, pin):
    path=(repo/pin['path']).resolve(); data=path.read_bytes()
    if not path.is_relative_to(repo.resolve()) or len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']:
        raise ValueError('dependency pin mismatch')
    return json.loads(data) if path.suffix=='.json' else data

def propose(repo, p, sha):
    for pin in p['dependencies'].values(): read_pin(repo,pin)
    fp=read_pin(repo,p['dependencies']['fold_protocol'])
    bp=read_pin(repo,fp['dependencies']['basin_protocol'])
    raws=[read_pin(repo,{'path':m['raw_path'],'sha256':m['raw_sha256'],'bytes':m['raw_bytes']}) for m in bp['models']]
    nets=[r['execution']['packet']['document']['events'][8]['payload'] for r in raws]
    kernel=raws[0]['execution']['packet']['document']['events'][0]['payload']['config']['kernel']
    alpha=float(next(e['weight'] for e in nets[0]['program']['links'] if e['source']=='p:0:0' and e['target']=='e:0'))
    k=float((Q(kernel['self_excitation'])+Q(kernel['inhibition']))/2)
    h0,h1=[Q(n['drives']['e:1']) for n in nets]
    def states(y,h):
        a=u=1.; v=g=0.
        for _ in range(p['budget']['conditional_iterations']):
            a,u,v,g=(math.tanh(4+k*a+alpha*u),math.tanh(2*a+k*u+alpha*y),
                     math.tanh(h+k*v+alpha*y),math.tanh(2*y+k*g))
        return [a,u,v,g]
    padding=Q(p['conditional_padding']); queries=[]
    def query(y,h):
        lower=states(float(y[0]),float(h[0])); upper=states(float(y[1]),float(h[1]))
        name='Q'+str(len(queries)).zfill(4)
        queries.append({'id':name,'y':list(map(str,y)),'h':list(map(str,h)),
          'lower4':[str(Q(v)-padding) for v in lower],'upper4':[str(Q(v)+padding) for v in upper]})
        if len(queries)>p['budget']['max_queries']: raise ValueError('query budget exhausted')
        return name
    nh=p['budget']['h_cells']; hg=[h0+(h1-h0)*Q(i,nh) for i in range(nh+1)]; cells=[]
    for region in p['regions']:
        lo,hi=map(Q,region['y']); ny=region['cells']; yg=[lo+(hi-lo)*Q(i,ny) for i in range(ny+1)]
        for j in range(nh):
            for i in range(ny):
                cells.append({'region':region['id'],'h_index':j,'y_index':i,
                              'query':query(yg[i:i+2],hg[j:j+2])})
    edges=[query([Q(y),Q(y)],[h0,h1]) for y in p['edge_y']]
    return {'schema':'HCCONCriticalStripProposal.v1','protocol_sha256':sha,
            'cells':cells,'edges':edges,'queries':queries,
            'discovery':{'arithmetic':'binary64 corner proposals; exact checker decides',
                         'conditional_iterations':p['budget']['conditional_iterations'],'automatic_retries':0}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','protocol','protocol-sha256','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();data=Path(args.protocol).read_bytes();p=json.loads(data)
    if hashlib.sha256(data).hexdigest()!=args.protocol_sha256 or p['schema']!='HCCONCriticalStripProtocol.v1':raise ValueError('protocol binding mismatch')
    result=propose(Path(args.repo).resolve(),p,args.protocol_sha256)
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out:
        json.dump(result,out,ensure_ascii=False,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'cells':len(result['cells']),'queries':len(result['queries'])}))
if __name__=='__main__':main()
