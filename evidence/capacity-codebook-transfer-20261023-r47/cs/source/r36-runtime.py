"""Typed leaf-slot guards around the unchanged R35 mathematical pipeline."""
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import lower,export,require
from tools.r35_compositional_slot.runtime import execute as prior_execute

def validate_inputs(candidates,context,t,contract):
    require(len(candidates)==2 and len(context)==len(t)==3,'two candidate/three leaf contract')
    require(all(c['predicate']=='R' and c['subject']==contract['candidate_subject'] for c in candidates),'candidate slot metadata')
    for facts,name in [(context,'C'),(t,'T')]:
        require(len(contract[name])==3,'three declared slots')
        for fact,slot in zip(facts,contract[name],strict=True):
            require(fact['predicate']==slot['predicate'] and fact['object']==slot['object'],'predicate/target slot metadata')

def execute(candidates,context,c_tree,t,t_tree,contract,vocabulary,arm,configuration,initial):
    validate_inputs(candidates,context,t,contract)
    r=prior_execute(candidates,context,c_tree,t,t_tree,True,vocabulary,arm,configuration,initial)
    r['leaf_contract_sha256']=fingerprint(contract);return r
