"""Saved numeric transition census. This never replaces a native tick or its side effects."""
from copy import deepcopy
import hashlib
import json
import math
import struct
import time
from tools.r20_evidence_feedback.policy import require

def exact_bytes(value):
    def tagged(v):
        if v is None:return ['none']
        if type(v) is bool:return ['bool',v]
        if type(v) is int:return ['int',str(v)]
        if type(v) is float:
            require(math.isfinite(v),'finite key number');return ['float',v.hex()]
        if type(v) is str:return ['str',v]
        if type(v) is list:return ['list',[tagged(x) for x in v]]
        require(type(v) is dict and all(type(k) is str for k in v),'key type')
        return ['dict',[[k,tagged(v[k])] for k in sorted(v)]]
    return json.dumps(tagged(value),separators=(',',':'),ensure_ascii=False).encode('utf-8')

def digest(value):return hashlib.sha256(value).hexdigest()

def inputs(event):return {n:event[n] for n in ['program','config','current','drives','top_down','semantics_sha256']}
def transition_key(event):return exact_bytes(inputs(event))

def kernel_input(event):
    v=inputs(event);v['current']=event['initial'];return exact_bytes(v)

def freeze(v):
    """Independent tuple/IEEE754 representation for the audit index, not the JSON key."""
    if type(v) is float:return ('float',struct.pack('!d',v))
    if type(v) is list:return ('list',tuple(freeze(x) for x in v))
    if type(v) is dict:return ('dict',tuple((k,freeze(v[k])) for k in sorted(v)))
    return (type(v).__name__,v)

def origin(event):return {n:event[n] for n in ['case','kernel_index','tick']}

def hit_kind(previous,event):
    if previous['case']!=event['case']:return 'cross_case'
    if previous['kernel_index']!=event['kernel_index']:return 'same_case_other_settle'
    return 'same_settle'

def caps(entries,payload,p):
    require(0<=entries<=p['maximum_cache_entries'],'census entry cap')
    require(0<=payload<=p['maximum_cache_payload_bytes'],'census payload cap')

def summarize(rows):
    hits=[r for r in rows if r['hit']]
    return dict(transitions=len(rows),hits=len(hits),misses=len(rows)-len(hits),
        locality={kind:sum(r['locality']==kind for r in hits) for kind in ['same_settle','same_case_other_settle','cross_case']},
        repeated_kernel_invocation_hits=sum(r['repeated_kernel_invocation'] for r in hits),
        same_public_input_hits=sum(r['same_public_input'] for r in hits),
        cross_case_identical_public_input_hits=sum(r['locality']=='cross_case' and r['same_public_input'] for r in hits),
        attribution={kind:{repeat:{public:sum(r['locality']==kind and r['repeated_kernel_invocation']==(repeat=='repeated_invocation') and
            r['same_public_input']==(public=='same_public') for r in hits) for public in ['same_public','different_public']}
            for repeat in ['repeated_invocation','not_repeated_invocation']} for kind in ['same_settle','same_case_other_settle','cross_case']},
        case_local_non_repeated_invocation_hits=sum(r['locality']!='cross_case' and not r['repeated_kernel_invocation'] for r in hits),
        possible_omitted_group_updates=sum(r['possible_group_updates'] for r in hits),
        possible_omitted_signal_transmissions=sum(r['possible_signal_transmissions'] for r in hits),
        possible_omitted_normalization_ops=sum(r['possible_group_updates'] for r in hits),
        generated_key_bytes=sum(r['key_bytes'] for r in rows),key_sha256_calls=len(rows),next_value_binding_sha256_calls=len(rows),map_lookups=len(rows),
        copied_state_values=sum(r['copied_state_values'] for r in rows),insertions=sum(not r['hit'] for r in rows),
        cache_entries_peak=max((r['cache_entries'] for r in rows),default=0),logical_payload_bytes_peak=max((r['cache_payload_bytes'] for r in rows),default=0),
        measured_phase_wall_seconds={n:sum(r['phase_wall_seconds'][n] for r in rows) for n in ['key','hash','lookup','copy_store','saved_value_check']})

def analyze(events,scope,p):
    require(scope in p['scopes'],'scope');cache={};rows=[];payload=0;last_case=None
    cpu=time.process_time();wall=time.perf_counter()
    for event in events:
        if scope=='case_local' and last_case!=event['case']:cache={};payload=0
        last_case=event['case'];times={};before=time.perf_counter();key=transition_key(event);times['key']=time.perf_counter()-before
        before=time.perf_counter();key_sha=digest(key);times['hash']=time.perf_counter()-before
        before=time.perf_counter();prior=cache.get(key);times['lookup']=time.perf_counter()-before
        # Python bytes keys compare the complete key, even when internal hash values collide.
        hit=prior is not None;before=time.perf_counter();value=dict(prior['next'] if hit else event['next'])
        if not hit:
            saved=dict(next=value,event=event,header=kernel_input(event),public=exact_bytes(event['public_numeric']))
            added=len(key)+len(exact_bytes(value))+len(exact_bytes(origin(event)))+len(saved['header'])+len(saved['public'])
            caps(len(cache)+1,payload+added,p);cache[key]=saved;payload+=added
        times['copy_store']=time.perf_counter()-before
        before=time.perf_counter();require(freeze(value)==freeze(event['next']),'same key different saved next-state');times['saved_value_check']=time.perf_counter()-before
        locality=hit_kind(prior['event'],event) if hit else None
        repeated=hit and locality!='same_settle' and prior['header']==kernel_input(event)
        rows.append(dict(**origin(event),hit=hit,origin=None if not hit else origin(prior['event']),locality=locality,
            repeated_kernel_invocation=bool(repeated),same_public_input=hit and prior['public']==exact_bytes(event['public_numeric']),
            key_sha256=key_sha,key_bytes=len(key),next_state_sha256=digest(exact_bytes(value)),
            possible_group_updates=len(event['program']['groups']) if hit else 0,
            possible_signal_transmissions=sum(event['top_down'] or e['kind']!='top_down' for e in event['program']['links']) if hit else 0,
            copied_state_values=len(value),cache_entries=len(cache),cache_payload_bytes=payload,phase_wall_seconds=times))
    return dict(rows=rows,summary=summarize(rows),analysis_cpu_seconds=time.process_time()-cpu,analysis_wall_seconds=time.perf_counter()-wall)

def audit(record,events,scope,p):
    require(len(record['rows'])==len(events),'census row count');index={};last_case=None;payload=0
    for row,event in zip(record['rows'],events,strict=True):
        if scope=='case_local' and last_case!=event['case']:index={};payload=0
        last_case=event['case'];signature=freeze(inputs(event));prior=index.get(signature);hit=prior is not None
        require(row['hit']==hit,'reuse decision');require({n:row[n] for n in origin(event)}==origin(event),'event order')
        require(row['key_sha256']==digest(transition_key(event)) and row['key_bytes']==len(transition_key(event)),'key binding')
        require(row['next_state_sha256']==digest(exact_bytes(event['next'])),'saved next-state binding')
        locality=hit_kind(prior,event) if hit else None
        require(row['origin']==(origin(prior) if hit else None) and row['locality']==locality,'reuse origin')
        require(row['repeated_kernel_invocation']==(hit and locality!='same_settle' and freeze(dict(inputs(prior),current=prior['initial']))==freeze(dict(inputs(event),current=event['initial']))),'kernel repetition attribution')
        require(row['same_public_input']==(hit and freeze(prior['public_numeric'])==freeze(event['public_numeric'])),'public repetition attribution')
        if hit:require(freeze(prior['next'])==freeze(event['next']),'same key different saved next-state')
        else:
            index[signature]=event
            payload+=len(transition_key(event))+len(exact_bytes(event['next']))+len(exact_bytes(origin(event)))+len(kernel_input(event))+len(exact_bytes(event['public_numeric']))
        caps(len(index),payload,p)
        require(row['cache_entries']==len(index) and row['cache_payload_bytes']==payload,'cache payload accounting')
        require(row['possible_group_updates']==(len(event['program']['groups']) if hit else 0) and
            row['possible_signal_transmissions']==(sum(event['top_down'] or e['kind']!='top_down' for e in event['program']['links']) if hit else 0),'counterfactual arithmetic ceiling')
        require(row['copied_state_values']==len(event['next']),'copy count')
        require(set(row['phase_wall_seconds'])=={'key','hash','lookup','copy_store','saved_value_check'} and all(math.isfinite(v) and v>=0 for v in row['phase_wall_seconds'].values()),'phase timings')
    require(record['summary']==summarize(record['rows']),'census aggregate')
    require(record['analysis_cpu_seconds']>=0 and record['analysis_wall_seconds']>=0,'analysis timing')

MUTATIONS={'hit':'reuse decision','key':'key binding','origin':'reuse origin','ceiling':'counterfactual arithmetic ceiling','aggregate':'census aggregate'}
def mutated(record,name):
    bad=deepcopy(record)
    if name=='hit':bad['rows'][0]['hit']=True
    elif name=='key':bad['rows'][0]['key_sha256']='0'*64
    elif name=='origin':
        row=next(r for r in bad['rows'] if r['hit']);row['origin']['tick']=row['tick']+1
    elif name=='ceiling':bad['rows'][0]['possible_group_updates']+=1
    else:bad['summary']['hits']+=1
    return bad
