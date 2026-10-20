"""Finite triangle: retain one shared Z witness, or erase that correlation."""
from hcr.model import Config,fingerprint
from tools.r32_semantic_join.runtime import lower,export,require
from tools.r33_typed_feedback.runtime import kernel
from tools.r34_feasible_state.runtime import onehot
from tools.r35_compositional_slot import compiler
from tools.r37_joint_tuple.runtime import membership,validate as validate_pair

AXES={'R':('X','Y'),'S':('Y','Z'),'U':('X','Z')}
def documents(cfg):
    docs=dict(role=compiler.equality(cfg),pair=compiler.expression(['and',0,1],cfg),feasible=compiler.feasible(4,cfg))
    for n in range(5):
        b=compiler.Builder(['m'+str(i) for i in range(n)],cfg);b.node('goal','or',[('m'+str(i),1) for i in range(n)]);docs['or'+str(n)]=b.document()
    return docs

def layout(domains,axes,order):
    return [dict(X=x,Y=y) for x in domains[axes[0]] for y in domains[axes[1]]][::1 if not order else -1]

def validate(domains,relations,vocabulary,order):
    require(set(domains)=={'X','Y','Z'} and len(set(sum(domains.values(),[])))==6 and all(len(v)==len(set(v))==2 for v in domains.values()),'three disjoint complete typed domains')
    require(order in [0,1] and set(relations)==set(AXES) and len(vocabulary)==len(set(vocabulary))==8 and set(sum(domains.values(),[]))<=set(vocabulary),'public layout/vocabulary/relations')
    for name,(a,b) in AXES.items():validate_pair(dict(X=domains[a],Y=domains[b]),layout(domains,(a,b),order),relations[name],name)

def combine(messages,order,cfg,docs,initial,arm):
    """Receives numeric relation tables only; same integer Z index is structural."""
    ij=[(i,j) for i in range(2) for j in range(2)][::1 if not order else -1];position={xy:i for i,xy in enumerate(ij)};ks=[];intermediate={};applied=[];gain=cfg.evidence_gain
    def gate(name,values):
        drives={'m'+str(i):gain*(2*v-1) for i,v in enumerate(values)}
        if name=='pair':drives['m2']=-gain
        k=kernel(docs[name],drives,cfg,initial);ks.append(k);return k['state']['goal']
    if arm=='native_shared':
        witnesses=[];joins=[]
        for x,y in ij:
            zz=[gate('pair',[messages['S'][position[y,z]],messages['U'][position[x,z]]]) for z in range(2)]
            union=gate('or2',zz);witnesses.append(zz);joins.append(union);applied.append(gate('pair',[messages['R'][position[x,y]],union]))
        intermediate=dict(shared_witnesses=witnesses,existential_join=joins)
    else:
        require(arm=='native_split','explicit independent-witness intervention')
        sy=[gate('or2',[messages['S'][position[y,z]] for z in range(2)]) for y in range(2)]
        ux=[gate('or2',[messages['U'][position[x,z]] for z in range(2)]) for x in range(2)];joins=[]
        for x,y in ij:
            union=gate('pair',[sy[y],ux[x]]);joins.append(union);applied.append(gate('pair',[messages['R'][position[x,y]],union]))
        intermediate=dict(independent_S=sy,independent_U=ux,independent_join=joins)
    return applied,intermediate,ks

def exact(domains,relations,order):
    a=layout(domains,('X','Y'),order)
    triples=[(x,y,z) for x in domains['X'] for y in domains['Y'] for z in domains['Z'] if any(f['subject']==x and f['object']==y for f in relations['R']) and any(f['subject']==y and f['object']==z for f in relations['S']) and any(f['subject']==x and f['object']==z for f in relations['U'])]
    eligible=[any(x==v['X'] and y==v['Y'] for x,y,z in triples) for v in a];ids=[i for i,b in enumerate(eligible) if b]
    return dict(kind='none' if not ids else 'unique' if len(ids)==1 else 'many',selected_index=ids[0] if len(ids)==1 else None,consistent=bool(ids),eligible=eligible,triples=triples,native_calls=0)

def execute(domains,relations,vocabulary,order,arm,configuration,initial):
    validate(domains,relations,vocabulary,order)
    if arm=='exact_joint':return dict(arm=arm,**exact(domains,relations,order))
    require(arm in ['native_shared','native_split'],'numeric arm');cfg=Config(**configuration);docs=documents(cfg);messages={};networks=[]
    for name,axes in AXES.items():
        values,ks=membership(layout(domains,axes,order),relations[name],vocabulary,cfg,docs,initial);messages[name]=values;networks.extend(ks)
    applied,intermediate,ks=combine(messages,order,cfg,docs,initial,arm);networks.extend(ks);gain=cfg.evidence_gain
    k=kernel(docs['feasible'],dict(**{'e'+str(i):gain*(2*v-1) for i,v in enumerate(applied)},complete=gain),cfg,initial);networks.append(k)
    kind=onehot(k,['none','unique','many','incomplete'],cfg.margin_threshold);eligibility=[k['state']['e'+str(i)] for i in range(4)];hi=(1+cfg.margin_threshold)/2;lo=(1-cfg.margin_threshold)/2;ids=[i for i,v in enumerate(eligibility) if v>=hi];index=ids[0] if kind=='unique' and len(ids)==1 and all(v<=lo for i,v in enumerate(eligibility) if i!=ids[0]) else None
    binding=dict(schema='hcr-r38-shared-witness-v1',revision=1,variables=['X','Y','Z'],projected_variables=['X','Y'],domains=domains,alternatives=layout(domains,('X','Y'),order),eligibility=eligibility,kind=kind,selected_index=index,coverage_activation=k['state']['complete'],shared_witness=arm=='native_shared',source_refs={n:[f['origin_sha256'] for f in fs] for n,fs in relations.items()},state_sha256=fingerprint(k),posterior_is_probability=False,contract='explicit_complete_domains_and_closed_relation_tables')
    return dict(arm=arm,messages=messages,intermediate=intermediate,applied=applied,binding=binding,kind=kind,selected_index=index,consistent=True if kind in ['unique','many'] else False if kind=='none' else None,networks=networks,native_calls=12*sum(map(len,relations.values()))+12+(17 if arm=='native_shared' else 13),independent_evidence_added=0)
