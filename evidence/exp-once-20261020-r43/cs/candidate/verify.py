"""Saved-only oracle, full-byte pairing and independently reconstructed exp ledger."""
from copy import deepcopy
import hashlib,json,math
from hcr.model import fingerprint,Cost
from tools.r32_semantic_join.runtime import require
from tools.r33_typed_feedback.verify import replay
from tools.r40_factor_query.verify import SavedNetworks,LAYERS,audit as prior_audit,summarize as prior_summary
from tools.r43_exp_once.runtime import canonical,opportunity,direct_input

def audit(r,c,packets,p,networks):
    require(r['workload']=='q4' and r['mode'] in ['baseline','exp_once'] and (r['arm']!='exact_joint' or r['mode']=='baseline'),'frozen cell')
    if r['arm']!='exact_joint':
        offset=p['store_offsets'][r['arm']+'/'+r['mode']];require(all(n.startswith('n') and n[1:].isdigit() and offset<=int(n[1:])<offset+1000 for n in r['network_ids']),'independent storage arm identity')
    row=prior_audit(r,c,packets,p,networks);row['mode']=r['mode'];return row

def order(k):
    ids=[g['id'] for g in k['program']['groups']]
    require(list(k['initial'])==list(k['state'])==ids and all(list(x['state'])==ids for x in k['ticks']),'state insertion order')

def pairs(records,networks,p):
    catalog={(r['case'],r['repetition'],r['arm'],r['mode']):r for r in records};require(len(catalog)==len(records)==480,'cell identity unique');out=[]
    exclusions=['mode','network_ids','prefix_core_cpu_seconds','query_core_cpu_seconds']
    for (case,rep,arm,mode),r in catalog.items():
        if mode!='baseline' or arm=='exact_joint':continue
        other=catalog[(case,rep,arm,'exp_once')]
        require({k:v for k,v in r.items() if k not in exclusions}=={k:v for k,v in other.items() if k not in exclusions},'full returned record equality')
        h=hashlib.sha256()
        for left,right in zip(r['network_ids'],other['network_ids'],strict=True):
            a=networks[left];b=networks[right]
            # The codec restores dictionary order from the pinned Program before pairing.
            order(a);order(b);body=canonical(a,p['kernel']);require(body==canonical(b,p['kernel']),'expanded full kernel bytes');h.update(body)
        out.append(dict(case=case,repetition=rep,arm=arm,kernels=len(r['network_ids']),full_bytes_exact=True,kernel_stream_sha256=h.hexdigest()))
    require(len(out)==192,'native pair coverage');return out

def summarize(rows):return dict(by_mode={m:prior_summary([r for r in rows if r['mode']==m]) for m in ['baseline','exp_once']})

def counted_pair(row,p):
    a=row['baseline'];b=row['exp_once'];require(a['physical']['exp_probe'] is b['physical']['exp_probe'] is True and a['physical']['restored'] is b['physical']['restored'] is True,'counted mode/restoration')
    ka=a['kernel'];kb=b['kernel'];require(canonical(ka,row['config'])==canonical(kb,row['config']),'counted full bytes');ids=[g['id'] for g in ka['program']['groups']];require(a['key_orders']==b['key_orders']==dict(initial=ids,final=ids,ticks=[ids for _ in ka['ticks']]),'counted state key order')
    op=opportunity(ka,row['config']);require(row['opportunity']==op and a['physical']['exp_calls']==op['baseline_exp_calls'] and b['physical']['exp_calls']==op['exp_once_exp_calls'],'actual exp counter equation')
    err=max(replay(ka,row['config'],p['scalar_tolerance']),replay(kb,row['config'],p['scalar_tolerance']))
    if row['kind']=='prior':
        entry=next(e for e in p['correctness_inputs'] if e['key']==row['key']);require(row['config']==p['kernel'] and row['reference_sha256']==entry['content_sha256']==hashlib.sha256(canonical(ka,row['config'])).hexdigest(),'prior kernel content binding')
    else:
        control=next(e for e in p['control_tests'] if e['name']==row['key']);require(row['config']==dict(p['kernel'],self_excitation=0.,inhibition=0.,max_ticks=1,patience=1) and ka['program']==dict(groups=[dict(id='goal',level=1,bias=0.)],links=[],paths=[[0]],edge_count=1) and ka['drives']=={'goal':control['drive']} and ka['initial']=={'goal':.5} and ka['convergence']['status']==row['expected_status']==control['status'],'controller control input/status')
    return dict(group_updates=op['group_updates'],negative_updates=op['negative_updates'],baseline_exp_calls=a['physical']['exp_calls'],exp_once_exp_calls=b['physical']['exp_calls'],ticks=2*op['ticks'],max_scalar_error=err)

def direct_checks(rows,p):
    require(len(rows)==18 and {r['test'] for r in rows}=={t['name'] for t in p['direct_tests']},'direct coverage');calls=groups=negative=0
    for row in rows:
        test=next(t for t in p['direct_tests'] if t['name']==row['test']);a=row['baseline'];b=row['exp_once'];require(a['restored'] is b['restored'] is True,'direct restoration');calls+=2
        if test['kind']=='invalid':
            require(a==b and a['error_type']=='ContractError' and a['exp_calls']==0 and a['cost']==row['zero_cost']==Cost().snapshot(),'same invalid input rejection')
        else:
            require(a['next']==b['next'] and a['next_order']==b['next_order'] and a['cost']==b['cost'] and a.get('error_type') is None and b.get('error_type') is None,'direct output/cost exact')
            doc,current,drives,cfg,top=direct_input(test,p);cfgvars={k:getattr(cfg,k) for k in cfg.__dataclass_fields__};k=dict(program=doc,drives=drives,initial=current,ticks=[dict(state=a['next'])],top_down=top);op=opportunity(k,cfgvars)
            expected_cost=Cost(kernel_ticks=1,group_updates=len(doc['groups']),normalization_ops=len(doc['groups']),signal_transmissions=sum(e['kind']!='top_down' or top for e in doc['links'])).snapshot()
            require(a['next_order']==[g['id'] for g in doc['groups']] and a['cost']==expected_cost and a['exp_calls']==op['baseline_exp_calls'] and b['exp_calls']==op['exp_once_exp_calls'],'direct actual exp count/order/cost');groups+=op['group_updates'];negative+=op['negative_updates']
    require(calls==36,'direct tick invocation count');return dict(invocations=calls,successful_tick_operations=24,rejected_before_tick_operations=12,groups_per_arm=groups,negative_per_arm=negative)

def mutations(r,c,packets,p,networks,records,counted):
    changes=[('revision',lambda x:x['binding'].update(revision=2)),('source',lambda x:x['binding']['source_refs']['R'].__setitem__(0,'wrong')),('payload',lambda x:x['binding']['payload']['factors']['S'].__setitem__(0,.5)),('payload_hash',lambda x:x['binding'].update(payload_sha256='wrong')),('seal',lambda x:x.update(producer_seal_sha256='wrong')),('Rmessage',lambda x:x['messages']['R'].__setitem__(0,.5)),('query_swap',lambda x:x['queries'].__setitem__(slice(1,3),x['queries'][1:3][::-1])),('eligibility',lambda x:x['queries'][0]['eligibility'].__setitem__(0,.5)),('selected',lambda x:x['queries'][0].update(selected_index=99)),('prefix_count',lambda x:x.update(prefix_calls=0)),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1])),('workload',lambda x:x.update(workload='q1'))];out=[]
    for name,change in changes:
        bad=deepcopy(r);change(bad)
        try:audit(bad,c,packets,p,networks)
        except (ValueError,KeyError):out.append(name)
        else:raise ValueError('accepted semantic mutation '+name)
    for name,change in [('actual_exp_count',lambda x:x['exp_once']['physical'].update(exp_calls=x['exp_once']['physical']['exp_calls']+1)),('restore',lambda x:x['baseline']['physical'].update(restored=False)),('group_ledger',lambda x:x['opportunity'].update(group_updates=x['opportunity']['group_updates']+1)),('counted_tick_state',lambda x:x['exp_once']['kernel']['ticks'][0]['state'].update(goal=.123))]:
        bad=deepcopy(counted);change(bad)
        try:counted_pair(bad,p)
        except ValueError:out.append(name)
        else:raise ValueError('accepted counted mutation '+name)
    bad=deepcopy(r);bad['network_ids'][0]=bad['network_ids'][-1]
    try:pairs([bad if x is r else x for x in records],networks,p)
    except ValueError:out.append('paired_kernel_bytes')
    else:raise ValueError('accepted paired reference mutation')
    return out
