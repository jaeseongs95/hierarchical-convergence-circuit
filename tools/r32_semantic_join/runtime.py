"""Native lower path and native upper role join; no file or reference-label access."""
from hcr import codec
from hcr.model import Config,Cost,Group,Link,Program,fingerprint

def require(v,m):
    if not v:raise ValueError(m)

def kernel(program,drives,cfg,cost):
    from hcr.dynamics import settle
    ticks=[]
    state,conv=settle(program,drives,cfg,cost,observe=lambda i,s,r,k:ticks.append(dict(tick=i,state=dict(s),residual=r,stable_steps=k)))
    return dict(program=codec.plain(program),program_sha256=program.digest,drives=drives,initial={g.id:.5 for g in program.groups},ticks=ticks,state=state,convergence=codec.plain(conv),cost=cost.snapshot(),adopted=state['goal']>=.5 if conv.status.value=='stable_decision' else None)

def lower(public,predicate,kernel_config):
    from hcr.workspace import make_program
    from hcr.binding import Binding
    from hcr.proof import reconstruct
    obs=codec.observation_from(public);cfg=Config(**kernel_config);cost=Cost()
    program=make_program(2,((0,1),),cfg,cost);drives={'e:0':cfg.evidence_gain*obs.edges[0].score,'e:1':cfg.evidence_gain*obs.edges[1].score,'goal':0.0}
    k=kernel(program,drives,cfg,cost);proof=reconstruct(obs,program,Binding(obs.digest,obs.revision,(0,1)),k['state'],k['adopted'],cost)
    return dict(schema='hcr-r32-lower-source-v1',observation=public,predicate=predicate,config=kernel_config,kernel=k,proof=codec.plain(proof),cost=cost.snapshot())

def export(source):
    k=source['kernel'];obs=source['observation']
    require(k['adopted'] is True and source['proof']['under_assumptions_valid'] and source['proof']['final'] is not None,'positive supported lower required')
    return dict(schema='hcr-r32-relation-v1',predicate=source['predicate'],subject=obs['start'],object=obs['goal'],revision=obs['revision'],confidence=k['state']['goal'],value=True,
        origin_sha256=fingerprint(source),observation_sha256=fingerprint(obs),proof_sha256=fingerprint(source['proof']),config_sha256=fingerprint(source['config']))

def guard(packet,source,predicate,vocabulary):
    require(packet==export(source),'packet source binding')
    require(packet['predicate']==predicate and packet['revision']==0 and packet['subject'] in vocabulary and packet['object'] in vocabulary,'predicate role revision contract')
    require(packet['subject']!=packet['object'],'lower relation endpoints')

def encode(query,packets,arm,gain):
    """Independent field coding only: never compares one role with another."""
    require(arm in ('typed','scalar_erased'),'numeric arm')
    alphabet=query['vocabulary'];require(len(alphabet)==2 and len(set(alphabet))==2,'two-symbol alphabet')
    code={alphabet[0]:-gain,alphabet[1]:gain}
    values=dict(qx=code[query['subject']],qz=code[query['object']])
    lookups=2
    for slot,name in [(0,'r'),(1,'s')]:
        fact=packets[slot]
        values[name+'c']=gain*(2*fact['confidence']-1)
        for role,field in [('a','subject'),('b','object')]:
            values[name+role]=0.0 if arm=='scalar_erased' else code[fact[field]]
            lookups+=int(arm=='typed')
    return values,dict(symbol_lookups=lookups,erased_role_values=4 if arm=='scalar_erased' else 0,confidence_arithmetic=6)

def proof(value,query,packets):
    if value is None:return None
    r,s=packets;terms=[[r['subject'],query['subject']],[r['object'],s['subject']],[s['object'],query['object']]]
    return dict(rule='relational_join' if value else 'relational_join_counterexample',origin_refs=[p['origin_sha256'] for p in packets],proof_refs=[p['proof_sha256'] for p in packets],
        role_terms=terms,premises=[r['value'],s['value']])

def execute(query,packets,arm,kernel_config,program_document):
    """Consumer input has no raw observations, lower edges, truth, or case id."""
    cfg=Config(**kernel_config);require(len(packets)==2 and [x['predicate'] for x in packets]==['R','S'],'ordered fact predicates')
    if arm=='ordinary_join':
        r,s=packets
        equality_checks=[r['subject']==query['subject'],r['object']==s['subject'],s['object']==query['object']]
        premise_checks=[r['value'],s['value']];value=all(premise_checks+equality_checks)
        return dict(query=query,packets=packets,arm=arm,kernel=None,value=value,proof=proof(value,query,packets),adapter_cost=dict(join_equalities=3,premise_checks=2),native_upper_settle_calls=0)
    drives,adapter=encode(query,packets,arm,cfg.evidence_gain)
    doc=program_document;program=Program(tuple(Group(**g) for g in doc['groups']),tuple(Link(**e) for e in doc['links']),tuple(tuple(path) for path in doc['paths']),doc['edge_count'])
    program.validate(cfg);cost=Cost(dynamic_groups_created=len(program.groups),dynamic_links_created=len(program.links));k=kernel(program,drives,cfg,cost);value=k['adopted']
    return dict(query=query,packets=packets,arm=arm,kernel=k,value=value,proof=proof(value,query,packets),adapter_cost=adapter,native_upper_settle_calls=1)
