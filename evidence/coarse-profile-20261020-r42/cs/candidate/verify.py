"""Reuse R40 semantic oracle; verify matched exact storage bytes and timer ledger."""
from copy import deepcopy
from hcr.model import fingerprint
from tools.r32_semantic_join.runtime import require
from tools.r40_factor_query.verify import SavedNetworks,LAYERS,summarize as prior_summary,audit as prior_audit
from tools.r42_coarse_profile.runtime import LABELS,comparable

def audit(r,c,packets,p,networks):
    require(r['mode'] in p['modes'] and r['workload']=='q4','mode/workload');out=prior_audit(r,c,packets,p,networks);out['mode']=r['mode'];return out

def ledger(metric,row):
    require(type(metric['core_cpu_ns']) is int and metric['core_cpu_ns']>=0,'whole core ns');profile=metric['profile']
    if row['mode']=='plain':require(profile is None,'plain has no probes');return None
    require(profile['restored'] is True and profile['restored_bindings']==9 and profile['clock']=='process_time_ns' and profile['observed_core_ns']==metric['core_cpu_ns'],'restoration and clock');events=profile['events'];require('core' in events and set(events)<=set(LABELS),'declared phase labels')
    for d in events.values():require(set(d)=={'calls','inclusive_ns','exclusive_ns'} and all(type(v) is int and v>=0 for v in d.values()) and d['calls']>0 and d['inclusive_ns']>=d['exclusive_ns'],'integer phase metrics')
    root=events['core'];require(root['calls']==1 and sum(d['exclusive_ns'] for d in events.values())==root['inclusive_ns'] and profile['support_ns']==metric['core_cpu_ns']-root['inclusive_ns']>=0,'exclusive partition')
    def calls(n):return events.get(n,{}).get('calls',0)
    native=row['physical_native_calls'];require(all(calls(n)==native for n in ['kernel','program_build','settle','result_materialize']),'physical calls/ticks match profiler');require(calls('source_export_guard')==1 and calls('contract_validate')==(1 if row['arm']=='exact_joint' else 2),'input contract counts')
    require(calls('producer')==(0 if row['arm']=='exact_joint' else 1) and calls('document_build')==(0 if row['arm']=='exact_joint' else 2) and calls('membership')==(0 if row['arm']=='exact_joint' else 3) and calls('consumer')==(0 if row['arm']=='exact_joint' else 4) and calls('encode_role')==row['role_total'],'original producer and consumer counts')
    return dict({n:d['exclusive_ns'] for n,d in events.items()},profile_support=profile['support_ns'])

def pairs(records):
    catalog={(r['case'],r['workload'],r['repetition'],r['arm'],r['mode']):r for r in records};rows=[]
    for key,r in catalog.items():
        if key[-1]!='plain':continue
        other=catalog[(*key[:-1],'profiled')];require(comparable(r)==comparable(other),'all kernel refs/full record bits match paired execution');rows.append(dict(case=key[0],workload=key[1],repetition=key[2],arm=key[3],record_sha256=fingerprint(comparable(r)),kernel_refs=len(r['network_ids']),exact_record_equal=True))
    require(len(rows)==288 and len(catalog)==576,'matched pair coverage');return rows

def mutations(r,c,packets,p,networks,metric,row,records):
    changes=[('revision',lambda x:x['binding'].update(revision=2)),('source',lambda x:x['binding']['source_refs']['R'].__setitem__(0,'wrong')),('payload',lambda x:x['binding']['payload']['factors']['S'].__setitem__(0,.5)),('payload_hash',lambda x:x['binding'].update(payload_sha256='wrong')),('seal',lambda x:x.update(producer_seal_sha256='wrong')),('Rmessage',lambda x:x['messages']['R'].__setitem__(0,.5)),('query_swap',lambda x:x['queries'].__setitem__(slice(1,3),x['queries'][1:3][::-1])),('eligibility',lambda x:x['queries'][0]['eligibility'].__setitem__(0,.5)),('selected',lambda x:x['queries'][0].update(selected_index=99)),('prefix_count',lambda x:x.update(prefix_calls=0)),('network_ref',lambda x:x['network_ids'].__setitem__(0,x['network_ids'][-1])),('workload',lambda x:x.update(workload='q1'))];out=[]
    for name,change in changes:
        bad=deepcopy(r);change(bad)
        try:audit(bad,c,packets,p,networks)
        except (ValueError,KeyError):out.append(name)
        else:raise ValueError('accepted record mutation '+name)
    for name,change in [('timer_negative',lambda x:x.update(core_cpu_ns=-1)),('restoration',lambda x:x['profile'].update(restored=False)),('partition',lambda x:x['profile']['events']['core'].update(exclusive_ns=x['profile']['events']['core']['exclusive_ns']+1)),('settle_count',lambda x:x['profile']['events']['settle'].update(calls=0)),('support',lambda x:x['profile'].update(support_ns=-1))]:
        bad=deepcopy(metric);change(bad)
        try:ledger(bad,row)
        except ValueError:out.append(name)
        else:raise ValueError('accepted ledger mutation '+name)
    bad=deepcopy(r);bad['network_ids'][0]=bad['network_ids'][-1]
    try:pairs([bad if x is r else x for x in records])
    except ValueError:out.append('paired_kernel_bytes')
    else:raise ValueError('accepted paired kernel mutation')
    return out

def summarize(rows):return dict(by_mode={mode:prior_summary([r for r in rows if r['mode']==mode]) for mode in ['plain','profiled']})
