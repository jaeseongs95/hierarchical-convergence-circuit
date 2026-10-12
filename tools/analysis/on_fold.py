"""연속 drive 가족의 fold와 저평형 가지를 제안한다. 판정은 별도 검산기 몫이다."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path

def read_pin(repo,pin):
    path=(repo/pin['path']).resolve();data=path.read_bytes()
    if not path.is_relative_to(repo.resolve()) or len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']:
        raise ValueError('dependency mismatch')
    return json.loads(data) if path.suffix=='.json' else data

def propose(repo,p,sha):
    for pin in p['dependencies'].values():read_pin(repo,pin)
    bp=read_pin(repo,p['dependencies']['basin_protocol'])
    raws=[read_pin(repo,{'path':m['raw_path'],'sha256':m['raw_sha256'],'bytes':m['raw_bytes']}) for m in bp['models']]
    net=[r['execution']['packet']['document']['events'][8]['payload'] for r in raws]
    kernel=raws[0]['execution']['packet']['document']['events'][0]['payload']['config']['kernel']
    alpha_q=Q(next(e['weight'] for e in net[0]['program']['links'] if e['source']=='p:0:0' and e['target']=='e:0'))
    k_q=(Q(kernel['self_excitation'])+Q(kernel['inhibition']))/2
    alpha,k=float(alpha_q),float(k_q)
    h0,h1=[Q(n['drives']['e:1']) for n in net]
    root0=read_pin(repo,p['dependencies']['root_record'])['discovery']['certificates'][0]
    root_y=[Q(root0['lower'][3]),Q(root0['upper'][3])]

    def states(y,h):
        a=u=1.;v=g=0.
        for _ in range(p['budget']['conditional_iterations']):
            a,u,v,g=(math.tanh(4+k*a+alpha*u),math.tanh(2*a+k*u+alpha*y),
                     math.tanh(h+k*v+alpha*y),math.tanh(2*y+k*g))
        return [a,u,v,g]

    def bundle(y,h):
        a,u,v,g=states(y,h)
        def E(x):return (1-x*x)/(1-k*(1-x*x))
        def K(x):return -2*x*(1-x*x)/(1-k*(1-x*x))**3
        den=1-2*alpha*E(a)*E(u)
        uy=alpha*E(u)/den;ay=alpha*E(a)*uy
        uyy=(2*E(u)*alpha*alpha*K(a)*uy*uy+K(u)*(2*ay+alpha)**2)/den
        L=-2+2*v+2*u+k*y+alpha*g;r=math.tanh(L);sigma=1-r*r
        Ly=2*alpha*E(v)+2*uy+k+2*alpha*E(g);Lh=2*E(v)
        Lyy=2*alpha*alpha*K(v)+2*uyy+4*alpha*K(g);Lyh=2*alpha*K(v)
        return [y-r,1-sigma*Ly,-sigma*Lh,2*r*sigma*Ly*Ly-sigma*Lyy,
                2*r*sigma*Ly*Lh-sigma*Lyh]

    y,h=map(lambda s:float(Q(s)),p['seed']);iterations=[]
    for index in range(p['budget']['newton_iterations']):
        R,Ry,Rh,Ryy,Ryh=bundle(y,h);det=Ry*Ryh-Rh*Ryy
        if not math.isfinite(det) or det==0:raise ValueError('singular candidate Newton matrix')
        dy=(Ryh*R-Rh*Ry)/det;dh=(-Ryy*R+Ry*Ry)/det
        iterations.append({'iteration':index+1,'y':y,'h':h,'R':R,'Ry':Ry,'dy':dy,'dh':dh})
        y,h=y-dy,h-dh
        if not (-1<y<1 and float(h0)<h<float(h1)):raise ValueError('candidate left frozen domain')
        if max(abs(dy),abs(dh))<1e-13:break
    center=[Q(y),Q(h)];radii=list(map(Q,p['fold_radius']))
    box=[[c-r,c+r] for c,r in zip(center,radii)]
    R,Ry,Rh,Ryy,Ryh=bundle(y,h);det=Ry*Ryh-Rh*Ryy
    C=[[Q(Ryh/det),Q(-Rh/det)],[Q(-Ryy/det),Q(Ry/det)]]
    padding=Q(p['conditional_padding']);queries=[];cache={}
    def query(ys,hs):
        key=tuple(ys+hs)
        if key in cache:return cache[key]
        lo=states(float(ys[0]),float(hs[0]));hi=states(float(ys[1]),float(hs[1]))
        name=f'Q{len(queries):03d}'
        queries.append({'id':name,'y':list(map(str,ys)),'h':list(map(str,hs)),
          'lower4':[str(Q(v)-padding) for v in lo],'upper4':[str(Q(v)+padding) for v in hi]})
        cache[key]=name
        if len(queries)>p['budget']['max_queries']:raise ValueError('query budget exhausted')
        return name
    point=lambda value:[value,value]
    fold={'center2':list(map(str,center)),'box2':[list(map(str,z)) for z in box],
          'C2x2':[[str(q) for q in row] for row in C],
          'center_query':query(point(center[0]),point(center[1])),'box_query':query(box[0],box[1])}
    yl,yr=center[0]-Q(p['local_y_halfwidth']),center[0]+Q(p['local_y_halfwidth'])
    hl,hh=box[1][0]-Q(p['parameter_guard']),box[1][1]+Q(p['parameter_guard'])
    critical={'y2':[str(yl),str(yr)],'h_low':str(hl),'h_high':str(hh),
      'rect_query':query([yl,yr],[hl,hh]),'low_left':query(point(yl),point(hl)),
      'low_center':query(point(center[0]),point(hl)),'low_right':query(point(yr),point(hl)),
      'high_center':query(point(center[0]),point(hh))}
    n=p['budget']['tube_count'];hs=[h0+(hl-h0)*(1-Q((n-i)**2,n*n)) for i in range(n+1)]
    ys=[]
    for hp in hs:
        low=float(root_y[0]-Q(1,100));high=float(center[0])
        if not bundle(low,float(hp))[0]<0<bundle(high,float(hp))[0]:raise ValueError('branch candidate bracketing failed')
        for _ in range(p['budget']['branch_bisections']):
            mid=(low+high)/2
            if bundle(mid,float(hp))[0]>0:high=mid
            else:low=mid
        ys.append(Q((low+high)/2))
    eps=Q(p['tube_padding']);tubes=[]
    for i in range(n):
        yy=[ys[i]-eps,ys[i+1]+eps]
        if i==0:yy=[min(yy[0],root_y[0]-eps),max(yy[1],root_y[1]+eps)]
        hp=[hs[i],hs[i+1]]
        tubes.append({'y2':list(map(str,yy)),'h2':list(map(str,hp)),
          'rect_query':query(yy,hp),'left_query':query(point(yy[0]),point(hp[0])),
          'right_query':query(point(yy[1]),point(hp[1]))})
    joins=[]
    for i in range(n-1):
        yy=[max(Q(tubes[i]['y2'][0]),Q(tubes[i+1]['y2'][0])),min(Q(tubes[i]['y2'][1]),Q(tubes[i+1]['y2'][1]))]
        hp=hs[i+1]
        if yy[0]>=yy[1]:raise ValueError('candidate join interval empty')
        joins.append({'y2':list(map(str,yy)),'h':str(hp),
          'left_query':query(point(yy[0]),point(hp)),'right_query':query(point(yy[1]),point(hp))})
    return {'schema':'HCCONFoldProposal.v1','protocol_sha256':sha,'fold':fold,'critical':critical,
            'tubes':tubes,'joins':joins,'queries':queries,'discovery':{'Newton':iterations,'final_float_y':y,
             'final_float_h':h,'conditional_iterations':p['budget']['conditional_iterations'],
             'notice':'Floating candidates and rounded conditional centers are proposals, not certificates'}}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','protocol','protocol-sha256','output'):ap.add_argument('--'+name,required=True)
    args=ap.parse_args();data=Path(args.protocol).read_bytes();p=json.loads(data)
    if hashlib.sha256(data).hexdigest()!=args.protocol_sha256 or p['schema']!='HCCONFoldProtocol.v1':raise ValueError('protocol binding')
    result=propose(Path(args.repo).resolve(),p,args.protocol_sha256)
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out:json.dump(result,out,ensure_ascii=False,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'queries':len(result['queries']),'tubes':len(result['tubes']),
                     'Newton_iterations':len(result['discovery']['Newton']),'proposal_h':result['discovery']['final_float_h']}))

if __name__=='__main__':main()
