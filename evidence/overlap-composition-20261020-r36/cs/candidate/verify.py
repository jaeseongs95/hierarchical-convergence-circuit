"""Bounded saved-trace replay, typed-source audit and intermediate semantic scores."""
from collections.abc import Mapping
from functools import lru_cache
from copy import deepcopy
import json,re
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r34_feasible_state.verify import expand_network,verify_networks
from tools.r35_compositional_slot.verify import audit as prior_audit,oracle,mutations as prior_mutations

class SavedNetworks(Mapping):
    def __init__(self,folder,p):
        self.folder=folder;self.p=p;self.names=tuple(sorted(f.stem for f in folder.glob('n*.json') if re.fullmatch(r'n[0-9]{3,4}',f.stem)))
        self.allowed=frozenset(self.names);self._get=lru_cache(maxsize=18)(lambda name:expand_network(json.loads((folder/(name+'.json')).read_text(encoding='utf-8')),p))
    def __len__(self):return len(self.names)
    def __iter__(self):return iter(self.names)
    def __getitem__(self,name):
        require(name in self.allowed,'native reference name');return self._get(name)
    def verify_all(self):
        error=0.
        for name in self.names:
            _,e=verify_networks({name:json.loads((self.folder/(name+'.json')).read_text(encoding='utf-8'))},self.p);error=max(error,e)
        return error

def audit(r,c,packets,p,networks):
    candidates=[packets[k] for k in c['candidates']];context=[packets[k] for k in c['context']];t=[packets[k] for k in c['T']];contract=c['contract']
    require(r['leaf_contract_sha256']==fingerprint(contract),'typed leaf contract binding')
    require(all(x['predicate']=='R' and x['subject']==contract['candidate_subject'] for x in candidates),'candidate metadata slot')
    for facts,name in [(context,'C'),(t,'T')]:
        for fact,slot in zip(facts,contract[name],strict=True):require(fact['predicate']==slot['predicate'] and fact['object']==slot['object'],'leaf predicate/target slot binding')
    row=prior_audit(r,c,packets,p,networks);row.update(cohort=c['cohort'],c_pattern=c['c_pattern'],t_pattern=c['t_pattern'],selected_code=None if r['selected_index'] is None else c['vocabulary'].index(candidates[r['selected_index']]['object']))
    if r['arm']=='native':
        ks=[networks[name] for name in r['network_ids']];role_total=role_correct=ast_total=ast_correct=0
        for name,facts,expr,segment in [('C',context,c['c_expr'],ks[:8]),('T',t,c['t_expr'],ks[9:-1])]:
            feasible=oracle(candidates,facts,p['expressions'][expr],facts,p['expressions'][expr],True)['feasible'];values=[];patterns=[]
            for i,candidate in enumerate(candidates):
                block=segment[4*i:4*i+4];bits=[candidate['object']==fact['subject'] for fact in facts];patterns.append(bits)
                role_total+=3;role_correct+=sum(k['adopted'] is expected for k,expected in zip(block[:3],bits,strict=True));ast_total+=1;ast_correct+=block[3]['adopted'] is (i in feasible);values.append(block[3]['adopted'])
            row[name+'_AST_values']=values;row[name+'_leaf_patterns']=patterns
        row.update(role_total=role_total,role_correct=role_correct,AST_total=ast_total,AST_correct=ast_correct,intermediate_correct=role_total==role_correct and ast_total==ast_correct)
    return row

def mutations(r,c,packets,p,networks):
    rejected=prior_mutations(r,c,packets,p,networks)
    bad=deepcopy(r);bad['leaf_contract_sha256']='wrong'
    try:audit(bad,c,packets,p,networks)
    except ValueError:rejected.append('leaf_contract')
    else:raise ValueError('accepted wrong leaf contract')
    for name,key,field,value in [('C_predicate',c['context'][0],'predicate','wrong'),('C_target',c['context'][0],'object','wrong'),('T_predicate',c['T'][0],'predicate','wrong'),('T_target',c['T'][0],'object','wrong'),('candidate_subject',c['candidates'][0],'subject','wrong')]:
        altered=deepcopy(packets);altered[key][field]=value
        try:audit(r,c,altered,p,networks)
        except ValueError:rejected.append(name)
        else:raise ValueError('accepted slot mutation '+name)
    return rejected

def distinctions(rows,cases,p):
    canonical={(r['c_pattern'],r['t_pattern'],r['c_expr'],r['t_expr']):r for r in rows if r['arm']=='native' and r['cohort']=='canonical'}
    from tools.r35_compositional_slot.runtime import truth
    expected=[[truth(tree,[bool((mask>>i)&1) for i in range(3)]) for mask in range(8)] for tree in p['expressions']]
    output={}
    for phase in ['C','T']:
        vectors=[[canonical[(mask,0,i,0) if phase=='C' else (0,mask,0,i)][phase+'_AST_values'][0] for mask in range(8)] for i in range(6)]
        output[phase]=dict(expected_vectors=expected,native_vectors=vectors,distinct_expected=len({tuple(v) for v in expected}),distinct_native=len({tuple(v) for v in vectors}),vector_matches=[x==y for x,y in zip(vectors,expected,strict=True)],resolved=sum(x is not None for v in vectors for x in v))
    metamorphic=[]
    for r in rows:
        if r['arm']!='native' or r['cohort']!='sentinel':continue
        baseline=canonical[(r['c_pattern'],r['t_pattern'],r['c_expr'],r['t_expr'])]
        metamorphic.append(all(r[k]==baseline[k] for k in ['kind','selected_code','value','reason']))
    return dict(functions=output,metamorphic_pairs=len(metamorphic),metamorphic_invariant=sum(metamorphic),all_intermediates_correct=all(r.get('intermediate_correct',True) for r in rows))
