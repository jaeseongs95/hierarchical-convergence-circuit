"""Independent pair-elimination fixed point; never calls producer refinement or native."""
import math
import struct
from hcr.model import fingerprint
from tools.r19_cross_level.probe import require

def inspect(entry):
    p=entry['program'];ids=[g['id'] for g in p['groups']]
    def b(x):
        require(type(x) is float and math.isfinite(x),'verifier float label');return struct.pack('>d',x)
    require(len(ids)==len(set(ids)) and 'goal' in ids and len(ids)<=32 and set(entry['initial'])==set(ids) and set(entry['drives'])<=set(ids),'verifier identities')
    require(type(entry['top_down']) is bool and all(type(v) is float and 0<=v<=1 and math.isfinite(v) for v in entry['initial'].values()),'verifier domain')
    label={g['id']:(g['level'],g['id']=='goal',b(g['bias']),b(entry['drives'].get(g['id'],0.)),b(entry['initial'][g['id']])) for g in p['groups']};incoming={k:[] for k in ids}
    for edge in p['links']:
        require(edge['source'] in label and edge['target'] in label and edge['kind'] in ('support','top_down'),'verifier links')
        weight=b(edge['weight'])
        if entry['top_down'] or edge['kind']!='top_down':incoming[edge['target']].append((edge['source'],weight,edge['kind']))
    relation={(a,b) for a in ids for b in ids if label[a]==label[b]};rounds=0
    while True:
        remove=set()
        for a,b in relation:
            left,right=incoming[a],incoming[b]
            if len(left)!=len(right) or any(wa!=wb or ka!=kb or (sa,sb) not in relation for (sa,wa,ka),(sb,wb,kb) in zip(left,right)):
                remove.add((a,b))
        rounds+=1
        if not remove:break
        relation-=remove;require(rounds<=len(ids)**2+1,'pair elimination bound')
    return ids,incoming,relation,rounds

def verify(entry,plan):
    require(plan['binding']==fingerprint(entry),'source/input binding')
    ids,incoming,relation,rounds=inspect(entry);classes=plan['classes'];flat=[k for c in classes for k in c]
    require(classes and all(c for c in classes) and len(flat)==len(set(flat)) and set(flat)==set(ids),'partition coverage')
    order={k:i for i,k in enumerate(ids)}
    require(all(c==sorted(c,key=order.get) for c in classes) and [c[0] for c in classes]==sorted((c[0] for c in classes),key=order.get),'representative order')
    for c in classes:
        for a in c:require(set(c)=={b for b in ids if (a,b) in relation},'closure/maximality')
    n,m=len(ids),len(classes);total=sum(len(incoming[k]) for k in ids);retained=sum(len(incoming[c[0]]) for c in classes)
    expected=dict(original_groups=n,representative_groups=m,original_active_links=total,representative_row_links=retained,
        projected_group_updates_omitted_per_tick=n-m,projected_normalizations_omitted_per_tick=n-m,
        projected_link_operations_omitted_per_tick=total-retained,projected_full_state_output_slots_per_tick=n,
        projected_alias_copy_slots_per_tick=n-m,actual_native_group_updates=0,actual_native_link_operations=0)
    require(plan['ledger']==expected,'projected work ledger');r=plan['refinement_rounds']
    require(type(r) is int and 1<=r<=n+1 and plan['analysis_work']==dict(local_labels=n,refinement_rows=n*r,ordered_incoming_entries=total*r),'analysis work ledger')
    return dict(pair_elimination_rounds=rounds,related_pairs=len(relation),nontrivial_classes=sum(len(c)>1 for c in classes),
        sufficient_condition_checked=True,actual_runtime_equivalence_tested=False,native_execution_calls=0)
