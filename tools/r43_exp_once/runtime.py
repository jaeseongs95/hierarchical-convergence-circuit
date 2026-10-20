"""One invocation-local reuse of the same negative-branch math.exp value."""
import inspect,json,math,time
from contextlib import contextmanager
from hcr import dynamics
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import export,require
from tools.r33_typed_feedback.runtime import kernel,program
import tools.r40_factor_query.runtime as original

NATIVE_TICK=dynamics.tick
EXP=math.exp
SOURCE=inspect.getsource(NATIVE_TICK)
OLD='        target=1/(1+exp(-z)) if z>=0 else exp(z)/(1+exp(z))\n'
NEW='        if z>=0:\n            target=1/(1+exp(-z))\n        else:\n            ez=exp(z)\n            target=ez/(1+ez)\n'
require(SOURCE.count(OLD)==1 and NATIVE_TICK.__globals__['exp'] is EXP,'frozen builtin/source boundary')
CANDIDATE_SOURCE=SOURCE.replace(OLD,NEW)

def make_tick(mode,counter=None):
    require(mode in ['baseline','exp_once'],'implementation')
    if counter is None and mode=='baseline':return NATIVE_TICK
    ns=dict(NATIVE_TICK.__globals__)
    if counter is not None:
        def counted(x):counter['exp_calls']+=1;return EXP(x)
        ns['exp']=counted
    exec(compile(SOURCE if mode=='baseline' else CANDIDATE_SOURCE,'<r43-isolated-tick>','exec'),ns)
    return ns['tick']

CANDIDATE=make_tick('exp_once')
_active=False

@contextmanager
def installed(mode,counted=False):
    global _active
    require(not _active and dynamics.tick is NATIVE_TICK and NATIVE_TICK.__globals__['exp'] is EXP,'single research invocation/no foreign patch')
    info=dict(exp_calls=0,counted=counted,restored=False,mode=mode)
    fn=make_tick(mode,info) if counted else NATIVE_TICK if mode=='baseline' else CANDIDATE
    _active=True
    try:
        dynamics.tick=fn;info['builtin_exp_unprobed']=not counted and fn.__globals__['exp'] is EXP;info['tick_variant_verified']=fn is (NATIVE_TICK if mode=='baseline' else CANDIDATE) if not counted else True;require(counted or info['builtin_exp_unprobed'] and info['tick_variant_verified'],'timing has no exp probe');yield info
    finally:
        dynamics.tick=NATIVE_TICK;_active=False;info['restored']=dynamics.tick is NATIVE_TICK
        require(info['restored'],'restore original tick')

def canonical(k,cfg):return json.dumps(dict(kernel=k,config=cfg),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()

def opportunity(k,cfg):
    """Reconstruct pre-exp z from saved states; does not call exp/tick/settle."""
    pr=k['program'];state=k['initial'];groups=negative=0
    for row in k['ticks']:
        totals={g['id']:g['bias']+k['drives'].get(g['id'],0.0) for g in pr['groups']}
        for e in pr['links']:
            if e['kind']=='top_down' and not k.get('top_down',True):continue
            totals[e['target']]+=e['weight']*(2*state[e['source']]-1)
        for g in pr['groups']:
            p=state[g['id']];d=totals[g['id']];positive=d+cfg['self_excitation']*p-cfg['inhibition']*(1-p);neg=-d+cfg['self_excitation']*(1-p)-cfg['inhibition']*p;z=(positive-neg)/cfg['temperature'];groups+=1;negative+=z<0
        state=row['state']
    return dict(group_updates=groups,negative_updates=negative,baseline_exp_calls=groups+negative,exp_once_exp_calls=groups,ticks=len(k['ticks']))

def run(c,w,arm,mode,p,sources):
    require(mode in ['baseline','exp_once'] and (arm!='exact_joint' or mode=='baseline'),'cell')
    started=time.process_time_ns();wall=time.perf_counter_ns()
    with installed(mode) as info:
        packets={key:export(sources[key]) for key in sum(c['relations'].values(),[])}
        require(all(packets[k]['origin_sha256']==fingerprint(sources[k]) for k in packets),'source export guard')
        r=original.execute(c['domains'],{n:[packets[k] for k in keys] for n,keys in c['relations'].items()},c['vocabulary'],c['order'],w['queries'],arm,p['kernel'],c['initial'])
    elapsed=time.process_time_ns()-started;wall_elapsed=time.perf_counter_ns()-wall
    return r,dict(core_cpu_ns=elapsed,core_wall_ns=wall_elapsed,restored=info['restored'],exp_probe=False,builtin_exp_unprobed=info['builtin_exp_unprobed'],tick_variant_verified=info['tick_variant_verified'])

def counted_kernel(doc,drives,cfg,initial,mode):
    with installed(mode,True) as info:k=kernel(doc,drives,Config(**cfg),initial)
    return dict(kernel=k,key_orders=dict(initial=list(k['initial']),final=list(k['state']),ticks=[list(r['state']) for r in k['ticks']]),physical=dict(exp_calls=info['exp_calls'],restored=info['restored'],exp_probe=True))

def direct_input(test,p):
    cfg=dict(p['kernel'],self_excitation=0.,inhibition=0.);cfg=Config(**cfg)
    doc=dict(groups=[dict(id='goal',level=1,bias=0.)],links=[],paths=[[0]],edge_count=1);state={'goal':.5};drives={'goal':test.get('drive',0.)};top_down=True
    if test['name']=='state_zero':state['goal']=0.
    if test['name']=='state_one':state['goal']=1.
    if test['name'].startswith('duplicate_'):
        doc=dict(groups=[dict(id='x',level=0,bias=0.),dict(id='goal',level=1,bias=0.)],links=[dict(source='x',target='goal',weight=.3,kind='support'),dict(source='x',target='goal',weight=-.2,kind='support'),dict(source='goal',target='x',weight=.35,kind='top_down')],paths=[[0]],edge_count=1);state={'x':.25,'goal':.75};drives={'x':-.5,'goal':.2};top_down=test['name'].endswith('_on')
    name=test['name']
    if name=='missing_state':state={}
    elif name=='extra_state':state['wrong']=.5
    elif name=='nan_state':state['goal']=float('nan')
    elif name=='range_state':state['goal']=1.1
    elif name=='inf_drive':drives['goal']=float('inf')
    elif name=='unknown_drive':drives['wrong']=1.
    return doc,state,drives,cfg,top_down
