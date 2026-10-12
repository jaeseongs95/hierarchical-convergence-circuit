""".04 전체 초기cube의 포함 사슬을 pinned Fraction 산술로 별도 검산한다."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import runpy
import sys

ORDER=['e:0','e:1','p:0:0','p:0:1','goal']
MODEL='swapped-s004-td1-off'
BASIN_CHECKER_SHA='7c9a9b9ae49495b561d0c6a7aaeddfaf7eaf6c892ef34ca261a668f44e0d5bb2'
BASIN_PROTOCOL_SHA='a1358e1245d61092f2063d32cde0f2ca783ce44dfb9412ca6e015295ff76cf6d'

def full_cube(lo,hi):
    # MUTATION_TARGET_CUBE
    return len(lo)==len(hi)==5 and all(a==Q(-1) and b==Q(1) for a,b in zip(lo,hi))

def valid_transition(arithmetic,old,new):
    # MUTATION_TARGET_TRANSITION
    return arithmetic['contains_transition'](*arithmetic['advance'](*arithmetic['model'],*old),*new)

def enters_target(arithmetic,box,root):
    # MUTATION_TARGET_ENTRY
    return arithmetic['strict_entry'](*box,*root)

def validate_cube_trace(trace,arithmetic):
    fields={'schema','protocol_sha256','model_id','state_order','initial_set','steps','proposal_status','entry_certificate_index'}
    if (not isinstance(trace,dict) or set(trace)!=fields or trace['schema']!='HCCONGlobalBasinTrace.v1'
        or trace['model_id']!=MODEL or trace['state_order']!=ORDER or trace['initial_set']!='[-1,1]^5'):
        raise ValueError('global trace binding mismatch')
    status=trace['proposal_status'];root=trace['entry_certificate_index']
    if (status not in ('entered_box','budget_exhausted') or (status=='entered_box' and (type(root) is not int or root!=3))
        or (status=='budget_exhausted' and root is not None)):raise ValueError('target root/status mismatch')
    steps=trace['steps']
    if not isinstance(steps,list) or not 1<=len(steps)<=1001:raise ValueError('invalid prefix budget')
    boxes=[]
    for k,step in enumerate(steps):
        if (not isinstance(step,dict) or set(step)!={'step','lower','upper'} or type(step['step']) is not int or step['step']!=k
            or any(not isinstance(step[s],list) or len(step[s])!=5 for s in ('lower','upper'))):
            raise ValueError('nonconsecutive step or dimension mismatch')
        lo,hi=[list(map(arithmetic['grid'],step[s])) for s in ('lower','upper')]
        if any(a>b for a,b in zip(lo,hi)):raise ValueError('reversed endpoints')
        boxes.append((lo,hi))
    if not full_cube(*boxes[0]):raise ValueError('initial set is not full cube')
    if status=='budget_exhausted' and len(boxes)!=1001:raise ValueError('premature budget exhaustion')
    return boxes

def check_cube_trace(trace,arithmetic,root_box):
    result={'accepted':False,'model_id':MODEL,'checked_steps':0,'entry_step':None,'root_index':None,
            'all5_global_convergence':False,'all7_global_convergence':False,'global_root_count':None}
    try:
        boxes=validate_cube_trace(trace,arithmetic)
        for k,box in enumerate(boxes):
            if k:
                if not valid_transition(arithmetic,boxes[k-1],box):return dict(result,reason='noncontaining transition at step '+str(k))
                result['checked_steps']=k
            if enters_target(arithmetic,box,root_box):
                if trace['proposal_status']!='entered_box' or k!=len(boxes)-1:
                    return dict(result,reason='does not end at first certified entry')
                lo,hi=box;rl,rh=root_box
                slack=min([lo[i]-rl[i] for i in range(5)]+[rh[i]-hi[i] for i in range(5)])
                return dict(result,accepted=True,reason='full cube connects to certified unique contracting root',
                            entry_step=k,root_index=3,terminal_slack=arithmetic['outward'](slack),
                            all5_global_convergence=True,all7_global_convergence=True,global_root_count=1)
        return dict(result,reason='INCONCLUSIVE: no strict whole-cube entry within frozen prefix')
    except (ValueError,TypeError,KeyError,IndexError) as error:return dict(result,reason=str(error))

def load_problem(repo,p):
    deps=p['dependencies']
    def pinned(pin):
        path=(repo/pin['path']).resolve();data=path.read_bytes()
        if (not path.is_relative_to(repo.resolve()) or len(data)!=pin['bytes']
            or hashlib.sha256(data).hexdigest()!=pin['sha256']):raise ValueError('dependency mismatch')
        return path,data
    for dep in deps.values():pinned(dep)
    if deps['basin_checker']['sha256']!=BASIN_CHECKER_SHA or deps['basin_protocol']['sha256']!=BASIN_PROTOCOL_SHA:
        raise ValueError('unsupported arithmetic/model dependency')
    a=runpy.run_path(str(pinned(deps['basin_checker'])[0]),run_name='global_basin_arithmetic')
    bp=a['decode'](pinned(deps['basin_protocol'])[1]);a['protocol_check'](bp)
    for field in ('root_protocol','root_record','root_checker','proposal_helper'):
        if deps[field]!=bp[field]:raise ValueError('root/model dependency binding mismatch')
    rp=a['decode'](pinned(deps['root_protocol'])[1])
    model=a['independent_models'](repo,bp,rp)[MODEL]
    b,G,d,q_iso=model
    if not (0<d<=1 and all(c>=0 for row in G for c in row) and 0<=q_iso<1):
        raise ValueError('monotone/domain/isolated contraction conditions fail')
    root_checker=runpy.run_path(str(pinned(deps['root_checker'])[0]),run_name='global_root_recheck')
    root_models=root_checker['load_models'](repo,rp)
    if tuple(model[:3])!=root_models[MODEL]:raise ValueError('root model differs from forward model')
    certificate=a['decode'](pinned(deps['root_record'])[1])['discovery']['certificates'][3]
    if certificate['model_id']!=MODEL or certificate['state_order']!=ORDER:raise ValueError('root/model/order mismatch')
    root_result,root_box=root_checker['check_certificate'](certificate,3,root_models,deps['root_protocol']['sha256'])
    if not root_result['accepted'] or root_box is None:raise ValueError('root certificate rejected')
    a['model']=model[:3]
    return a,root_box,{'root_reverification':root_result,'exact_model_equality':True,'G_nonnegative':True,
                       'domain_preserved':True,'isolated_qF_upper':a['outward'](q_iso,True),'isolated_incident_links':0}

def self_test():
    def endpoint(q):return f'{q:.50f}'
    base={'schema':'HCCONGlobalBasinTrace.v1','protocol_sha256':'synthetic','model_id':MODEL,'state_order':ORDER,
          'initial_set':'[-1,1]^5','steps':[{'step':0,'lower':[endpoint(-1)]*5,'upper':[endpoint(1)]*5}],
          'proposal_status':'entered_box','entry_certificate_index':3}
    a={'grid':Q,'model':(), 'advance':lambda lo,hi:([v/2 for v in lo],[v/2 for v in hi]),
       'contains_transition':lambda il,ih,lo,hi:all(c<=a<=b<=d for a,b,c,d in zip(il,ih,lo,hi)),
       'strict_entry':lambda lo,hi,rl,rh:all(a<c<=d<b for a,b,c,d in zip(rl,rh,lo,hi)), 'outward':str}
    good=json.loads(json.dumps(base));good['steps'].append({'step':1,'lower':[endpoint(-.5)]*5,'upper':[endpoint(.5)]*5})
    root=([Q(-3,4)]*5,[Q(3,4)]*5)
    assert not enters_target(a,([Q(-3,4)]*5,[Q(0)]*5),root),'strict terminal boundary control'
    assert check_cube_trace(good,a,root)['accepted'],'valid synthetic fullcube chain'
    bad=json.loads(json.dumps(good));bad['steps'][0]['lower']=[endpoint(0)]*5;bad['steps'][0]['upper']=[endpoint(0)]*5
    assert not check_cube_trace(bad,a,root)['accepted'],'fullcube shrink control'
    bad=json.loads(json.dumps(good));bad['steps'][1]['lower']=[endpoint(0)]*5;bad['steps'][1]['upper']=[endpoint(0)]*5
    assert not check_cube_trace(bad,a,root)['accepted'],'transition inclusion control'
    for mutate in ('model','root','order','missing_step'):
        bad=json.loads(json.dumps(good))
        if mutate=='model':bad['model_id']='swapped-s003-td1-off'
        elif mutate=='root':bad['entry_certificate_index']=0
        elif mutate=='order':bad['state_order']=list(reversed(ORDER))
        else:bad['steps'][1]['step']=2
        assert not check_cube_trace(bad,a,root)['accepted'],'binding/sequence control '+mutate
    return {'passed':True,'synthetic_only':True,'controls':['fullcube','transition','strict_entry','model','root','order','missing_step']}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--self-test',action='store_true')
    for name in ('repo','protocol','protocol-sha256','input','output'):parser.add_argument('--'+name)
    args=parser.parse_args()
    if args.self_test:print(json.dumps(self_test()));return
    if any(getattr(args,n) is None for n in ('repo','protocol','protocol_sha256','input','output')):parser.error('all file arguments required')
    result={'schema':'HCCONGlobalBasinCheck.v1','protocol_sha256':args.protocol_sha256}
    try:
        data=Path(args.protocol).read_bytes();p=json.loads(data)
        if hashlib.sha256(data).hexdigest()!=args.protocol_sha256:raise ValueError('protocol hash mismatch')
        expected={'schema':'HCCONGlobalBasinProtocol.v1','model_id':MODEL,'state_order':ORDER,'initial_x':'[-1,1]^5',
                  'target_root_index':3,'max_steps':1000,'grid_places':50,'taylor_degree':96,'auto_retry':False}
        if any(p.get(k)!=v or (type(v) in (int,bool) and type(p[k]) is not type(v)) for k,v in expected.items()):raise ValueError('unsupported frozen protocol')
        a,root,bindings=load_problem(Path(args.repo).resolve(),p);trace=a['decode'](Path(args.input).read_bytes())
        if trace.get('protocol_sha256')!=args.protocol_sha256:raise ValueError('trace protocol binding mismatch')
        result.update(model_binding=bindings,result=check_cube_trace(trace,a,root))
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,OSError,SyntaxError) as error:result['error']=str(error)
    with Path(args.output).open('x',encoding='utf-8',newline='\n') as out:json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
    if 'error' in result or not result['result']['accepted']:raise SystemExit(1)

if __name__=='__main__':main()
