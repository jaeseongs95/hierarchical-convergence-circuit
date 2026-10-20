"""Frozen source/logic/role/proof/cost checks and separate scalar replay; no native runs."""
from copy import deepcopy
import itertools
from hcr import codec
from hcr.model import Config,Cost,fingerprint
from hcr.evaluation.reference import assess
from hcr.evaluation.adaptive_audit_support import chain_program
from tools.r19_cross_level.probe import independent_kernel

def require(v,m):
    if not v:raise ValueError(m)

def logic(p):
    features=['rc','sc','ra','rb','sa','sb','qx','qz'];nodes=[]
    for i,(a,b) in enumerate([('ra','qx'),('rb','sa'),('sb','qz')]):
        nodes.extend([dict(id=f'eq{i}p',op='and',inputs=[[a,True],[b,True]]),dict(id=f'eq{i}n',op='and',inputs=[[a,False],[b,False]]),dict(id=f'eq{i}',op='or',inputs=[[f'eq{i}p',True],[f'eq{i}n',True]])])
    nodes.append(dict(id='goal',op='and',inputs=[[k,True] for k in ['eq0','eq1','eq2','rc','sc']]))
    groups=[dict(id=k,level=0,bias=0.0) for k in features];links=[];gain=p['kernel']['relation_gain'];td=p['kernel']['top_down_gain']
    for n in nodes:
        groups.append(dict(id=n['id'],level=1,bias=(-gain if n['op']=='and' else gain)*(len(n['inputs'])-1)))
        for source,positive in n['inputs']:
            sign=1 if positive else -1;links.extend([dict(source=source,target=n['id'],weight=sign*gain,kind='support'),dict(source=n['id'],target=source,weight=sign*td,kind='top_down')])
    expected=dict(groups=groups,links=links,edge_count=2,paths=[[0,1]])
    require(p['upper_program']==expected and len(groups)==18,'authored equality graph grammar')
    return nodes

def packet_for(source):
    o=source['observation']
    return dict(schema='hcr-r32-relation-v1',predicate=source['predicate'],subject=o['start'],object=o['goal'],revision=o['revision'],confidence=source['kernel']['state']['goal'],value=True,
      origin_sha256=fingerprint(source),observation_sha256=fingerprint(o),proof_sha256=fingerprint(source['proof']),config_sha256=fingerprint(source['config']))

def audit_lower(r,source,p):
    require(r['schema']=='hcr-r32-lower-source-v1' and r['observation']==source['observation'] and r['predicate']==source['predicate'] and r['config']==p['kernel'],'lower source input')
    obs=codec.observation_from(r['observation']);cfg=Config(**p['kernel']);k=r['kernel'];program=chain_program(2,[[0,1]],cfg)
    require(k['program']==program and k['drives']=={'e:0':cfg.evidence_gain,'e:1':cfg.evidence_gain,'goal':0.0},'lower native grammar')
    error=independent_kernel(k,p['kernel'],p['scalar_tolerance']);require(k['adopted'] is True,'lower positive source unavailable')
    from hcr.model import Decision,Convergence,Status,Mode,Proof,ProofNode
    pr=r['proof'];proof=Proof(tuple(ProofNode(**dict(n,parents=tuple(n['parents']))) for n in pr['nodes']),pr['final'],pr['primitive_depth'],tuple(tuple(x) for x in pr['assumed_edges']),pr['under_assumptions_valid'],tuple(tuple(x) for x in pr['paths']))
    # assess needs only these observable attributes, not a runtime/session object.
    from types import SimpleNamespace
    decision=SimpleNamespace(observation_digest=obs.digest,value=k['adopted'],proof=proof,convergence=SimpleNamespace(status=Status(k['convergence']['status'])))
    assessment=codec.plain(assess(decision,obs,{e.id:True for e in obs.edges}));require(assessment['correct'] is True and assessment['proof_valid'] and assessment['assumption_correct'] is True,'lower primitive proof and truth')
    for eid,v in proof.assumed_edges:
        i=next(i for i,e in enumerate(obs.edges) if e.id==eid);require(v is (k['state']['e:'+str(i)]>=.5),'source proof signal support')
    n=len(k['ticks']);expected=Cost(dynamic_groups_created=len(program['groups']),dynamic_links_created=len(program['links']),kernel_ticks=n,group_updates=n*len(program['groups']),normalization_ops=n*len(program['groups']),signal_transmissions=n*len(program['links']))
    require(k['cost']==expected.snapshot(),'lower construction and numeric cost');expected.proof_nodes_reconstructed=len(proof.nodes);require(r['cost']==expected.snapshot(),'lower proof cost')
    return dict(key=source['key'],ticks=n,confidence=k['state']['goal'],numeric_replay_max_absolute_error=error,cost=r['cost'],strict_correct=True)

def audit_upper(r,case,arm,p,sources,truth):
    query=case['query'];packets=[packet_for(sources[k]) for k in case['source_keys']]
    require(r['query']==query and r['packets']==packets and r['arm']==arm,'actual upper packet/query binding')
    expected_bridge=dict(source_records_loaded=2,source_serialized_bytes=sum(len(codec.dumps(sources[k]).encode()) for k in case['source_keys']),origin_sha256_calls=4,packet_digest_calls=16,packet_validations=2,packet_serialized_bytes=sum(len(codec.dumps(x).encode()) for x in packets))
    require(r['bridge_cost']==expected_bridge,'source materialization and bridge cost')
    facts=packets;terms=[[facts[0]['subject'],query['subject']],[facts[0]['object'],facts[1]['subject']],[facts[1]['object'],query['object']]];checks=[a==b for a,b in terms]
    logical=all(checks) and all(f['value'] for f in facts);require(logical is truth,'frozen semantic reference')
    error=0.;cost=Cost().snapshot()
    if arm=='ordinary_join':
        require(r['kernel'] is None and r['value'] is logical and r['native_upper_settle_calls']==0 and r['adapter_cost']==dict(join_equalities=3,premise_checks=2),'ordinary information-matched join')
    else:
        require(arm in ('typed','scalar_erased') and r['native_upper_settle_calls']==1,'numeric arm/call count');k=r['kernel'];require(k['program']==p['upper_program'],'fixed upper Program')
        code={query['vocabulary'][0]:-p['kernel']['evidence_gain'],query['vocabulary'][1]:p['kernel']['evidence_gain']}
        drives={name:code[value] for name,value in [('qx',query['subject']),('qz',query['object'])]}
        for slot,name in enumerate(['r','s']):
            drives[name+'c']=p['kernel']['evidence_gain']*(2*packets[slot]['confidence']-1)
            drives[name+'a']=0.0 if arm=='scalar_erased' else code[packets[slot]['subject']]
            drives[name+'b']=0.0 if arm=='scalar_erased' else code[packets[slot]['object']]
        require(k['drives']==drives,'fieldwise role encoding')
        require(r['adapter_cost']==dict(symbol_lookups=6 if arm=='typed' else 2,erased_role_values=0 if arm=='typed' else 4,confidence_arithmetic=6),'encoding ledger')
        error=independent_kernel(k,p['kernel'],p['scalar_tolerance']);require(r['value'] is k['adopted'],'unrepaired numeric readout')
        n=len(k['ticks']);cost=Cost(dynamic_groups_created=len(k['program']['groups']),dynamic_links_created=len(k['program']['links']),kernel_ticks=n,group_updates=n*len(k['program']['groups']),normalization_ops=n*len(k['program']['groups']),signal_transmissions=n*len(k['program']['links'])).snapshot()
        require(k['cost']==cost,'upper exact operation accounting')
    proof=None if r['value'] is None else dict(rule='relational_join' if r['value'] else 'relational_join_counterexample',origin_refs=[f['origin_sha256'] for f in facts],proof_refs=[f['proof_sha256'] for f in facts],role_terms=terms,premises=[f['value'] for f in facts])
    require(r['proof']==proof,'semantic proof references/terms')
    valid=r['value'] is not None and r['value'] is logical
    return dict(key=case['key'],arm=arm,truth=truth,value=r['value'],correct=r['value'] is truth,abstained=r['value'] is None,proof_valid=valid,strict_correct=valid,
        numeric_replay_max_absolute_error=error,cost=cost,upper_native_settles=r['native_upper_settle_calls'],source_keys=case['source_keys'],adapter_cost=r['adapter_cost'],bridge_cost=r['bridge_cost'])

def collision_check(records,cases):
    groups={}
    for case in cases:
        r=records[(case['key'],'scalar_erased')];k=r['kernel'];key=fingerprint(dict(program=k['program'],drives=k['drives']))
        groups.setdefault(key,[]).append(dict(key=case['key'],value=r['value'],kernel=k))
    for group in groups.values():require(all(x['kernel']==group[0]['kernel'] for x in group),'scalar collision native trace identity')
    return [dict(cases=[x['key'] for x in g],value=g[0]['value']) for g in groups.values()]

def mutations(record,case,p,sources,truth):
    out={}
    for name in ['role','confidence','origin','revision','drive','tick','readout','proof','cost']:
        b=deepcopy(record)
        if name in ('role','confidence','origin','revision'):
            field={'role':'subject','confidence':'confidence','origin':'origin_sha256','revision':'revision'}[name]
            b['packets'][0][field]={'role':'wrong','confidence':.25,'origin':'0'*64,'revision':1}[name]
        elif name=='drive':b['kernel']['drives']['ra']*= -1
        elif name=='tick':b['kernel']['ticks'][0]['state']['goal']+=.01
        elif name=='readout':b['value']=not b['value']
        elif name=='proof':b['proof']['role_terms'][0][0]='wrong'
        else:b['kernel']['cost']['kernel_ticks']+=1
        try:audit_upper(b,case,'typed',p,sources,truth)
        except ValueError as exc:out[name]=str(exc)
        else:raise ValueError('mutation accepted '+name)
    return out

def structural_check(p):
    from tools.r32_semantic_join.runtime import encode
    nodes=logic(p);count=0;query=dict(vocabulary=['zero','one'],subject='zero',object='one')
    for bits in itertools.product([False,True],repeat=6):
        values=dict(zip(['ra','rb','sa','sb','qx','qz'],bits));values.update(rc=True,sc=True)
        for n in nodes:
            inputs=[values[k] if positive else not values[k] for k,positive in n['inputs']];values[n['id']]=all(inputs) if n['op']=='and' else any(inputs)
        expected=bits[0]==bits[4] and bits[1]==bits[2] and bits[3]==bits[5]
        require(values['goal'] is expected,'exhaustive Boolean graph semantics');count+=1
        q=dict(query,subject=query['vocabulary'][int(bits[4])],object=query['vocabulary'][int(bits[5])]);facts=[dict(subject=query['vocabulary'][int(bits[0])],object=query['vocabulary'][int(bits[1])],confidence=.9),dict(subject=query['vocabulary'][int(bits[2])],object=query['vocabulary'][int(bits[3])],confidence=.9)]
        d,c=encode(q,facts,'typed',4.0);require([d[k]>0 for k in ['ra','rb','sa','sb','qx','qz']]==list(bits) and c['symbol_lookups']==6,'independent field mapping');count+=1
        d,c=encode(q,facts,'scalar_erased',4.0);require(all(d[k]==0 for k in ['ra','rb','sa','sb']) and c['erased_role_values']==4,'role erasure');count+=1
    return dict(status='STRUCTURAL_CHECKS_PASSED',checks=count,native_inference_calls=0,native_settle_calls=0,learning_calls=0)
