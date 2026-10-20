"""Stable refinement of ordered incoming rows, with exact binary64 labels."""
import math
import struct
from hcr.model import fingerprint
from tools.r19_cross_level.probe import require

def bits(x):
    require(type(x) is float and math.isfinite(x),'finite float label')
    return struct.pack('>d',x).hex()

def labels(entry):
    p=entry['program'];ids=[g['id'] for g in p['groups']]
    require(len(ids)==len(set(ids)) and 'goal' in ids and len(ids)<=32,'group identity')
    require(set(entry['initial'])==set(ids) and set(entry['drives'])<=set(ids) and type(entry['top_down']) is bool,'input identity')
    require(all(type(v) is float and math.isfinite(v) and 0<=v<=1 for v in entry['initial'].values()),'initial domain')
    result={g['id']:(g['level'],g['id']=='goal',bits(g['bias']),bits(entry['drives'].get(g['id'],0.)),bits(entry['initial'][g['id']])) for g in p['groups']}
    for e in p['links']:
        require(e['source'] in result and e['target'] in result and e['kind'] in ('support','top_down'),'link identity');bits(e['weight'])
    return ids,result

def rows(entry):
    result={g['id']:[] for g in entry['program']['groups']}
    for e in entry['program']['links']:
        if e['kind']=='top_down' and not entry['top_down']:continue
        result[e['target']].append((e['source'],bits(e['weight']),e['kind']))
    return result

def ledger(entry,classes):
    incoming=rows(entry);n=len(incoming);representatives=[c[0] for c in classes];edges=sum(map(len,incoming.values()));retained=sum(len(incoming[r]) for r in representatives)
    return dict(original_groups=n,representative_groups=len(classes),original_active_links=edges,representative_row_links=retained,
        projected_group_updates_omitted_per_tick=n-len(classes),projected_normalizations_omitted_per_tick=n-len(classes),
        projected_link_operations_omitted_per_tick=edges-retained,projected_full_state_output_slots_per_tick=n,
        projected_alias_copy_slots_per_tick=n-len(classes),actual_native_group_updates=0,actual_native_link_operations=0)

def analyze(entry):
    ids,local=labels(entry);incoming=rows(entry)
    def color(keys):
        known={};return {k:known.setdefault(keys[k],len(known)) for k in ids}
    current=color(local);rounds=0
    while True:
        signatures={k:(current[k],tuple((current[s],weight,kind) for s,weight,kind in incoming[k])) for k in ids}
        refined=color(signatures);rounds+=1
        if refined==current:break
        current=refined;require(rounds<=len(ids),'refinement bound')
    classes=[[k for k in ids if current[k]==i] for i in range(len(set(current.values())))]
    return dict(binding=fingerprint(entry),classes=classes,ledger=ledger(entry,classes),refinement_rounds=rounds,
        analysis_work=dict(local_labels=len(ids),refinement_rows=len(ids)*rounds,ordered_incoming_entries=sum(map(len,incoming.values()))*rounds),
        scope='maximal within ordered-row sufficient rule; not all semantic equivalences, learned compression or speed')
