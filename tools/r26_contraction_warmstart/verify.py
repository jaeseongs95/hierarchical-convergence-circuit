"""Separate scalar/rational saved-record checks; never invokes native dynamics."""
import math
from fractions import Fraction as F
from tools.r19_cross_level.probe import require
from tools.r24_trust_boundary.census import freeze

def rational_gate(program,cfg,drives,weights):
    d,t,sh=F(cfg['damping']),F(cfg['temperature']),F(cfg['self_excitation'])+F(cfg['inhibition']);rows=[]
    def enc(x):return dict(numerator=x.numerator,denominator=x.denominator)
    for group in program['groups']:
        key=group['id'];lo=hi=2*(F(group['bias'])+F(drives.get(key,0)))/t
        lo-=sh/t;hi+=sh/t;coeff=[]
        for edge in program['links']:
            if edge['target']!=key:continue
            weight=abs(F(edge['weight']));lo-=2*weight/t;hi+=2*weight/t;coeff.append((edge['source'],weight))
        a=F(0) if lo<=0<=hi else min(abs(lo),abs(hi));u=min(F(1,4),24/(24+24*a+12*a*a+4*a**3+a**4))
        q=1-d+2*d*sh*u/t
        for source,weight in coeff:q+=4*d*weight*u*F(weights[source])/F(weights[key])/t
        rows.append(dict(group=key,z_distance_lower=enc(a),sigmoid_derivative_upper=enc(u),weighted_row_upper=enc(q)))
    q=max(F(row['weighted_row_upper']['numerator'],row['weighted_row_upper']['denominator']) for row in rows)
    return dict(rows=rows,q_upper=enc(q),eligible=q<=F(19,20),scope='ideal real-valued map over [0,1]^n; not binary64/finite-stop proof')

def scalar(record,cfg,tolerance):
    program=record['program'];state=dict(record['initial']);history=[];stable=0;maximum=0.;stop=None
    def near(a,b):
        nonlocal maximum
        maximum=max(maximum,abs(a-b));return abs(a-b)<=tolerance
    def same(a,b):return set(a)==set(b) and all(near(a[k],b[k]) for k in a)
    for number,row in enumerate(record['ticks'],1):
        values={g['id']:g['bias']+record['drives'].get(g['id'],0.) for g in program['groups']}
        for edge in program['links']:values[edge['target']]+=edge['weight']*(2*state[edge['source']]-1)
        nxt={}
        for group in program['groups']:
            key=group['id'];old=state[key];drive=values[key]
            positive=drive+cfg['self_excitation']*old-cfg['inhibition']*(1-old)
            negative=-drive+cfg['self_excitation']*(1-old)-cfg['inhibition']*old
            z=(positive-negative)/cfg['temperature'];target=1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
            nxt[key]=(1-cfg['damping'])*old+cfg['damping']*target
        residual=max(abs(nxt[k]-state[k]) for k in state);stable=stable+1 if residual<=cfg['residual_tolerance'] else 0
        require(row['tick']==number and row['stable_steps']==stable and same(row['state'],nxt) and near(row['residual'],residual),'scalar trace')
        margin=abs(2*nxt['goal']-1)
        if stable>=cfg['patience']:stop='stable_decision' if margin>=cfg['margin_threshold'] else 'stable_ambiguous'
        elif history and residual>10*cfg['residual_tolerance'] and max(abs(nxt[k]-history[-1][k]) for k in nxt)<cfg['residual_tolerance']:stop='oscillating'
        if stop is not None:state=nxt;require(number==len(record['ticks']),'after termination');break
        history.append(state);history=history[-3:];state=nxt
    if stop is None:require(len(record['ticks'])==cfg['max_ticks'],'premature stop');stop='budget_exhausted'
    conv=record['convergence'];require(conv['status']==stop and conv['ticks']==number and conv['stable_steps']==stable and near(conv['residual'],residual) and near(conv['margin'],margin),'scalar convergence')
    require(same(state,record['state']) and record['adopted']==(state['goal']>=.5 if stop=='stable_decision' else None),'scalar readout')
    from hcr.model import Cost
    cost=record['cost'];expected=Cost().snapshot();expected.update(kernel_ticks=number,group_updates=number*len(program['groups']),normalization_ops=number*len(program['groups']),signal_transmissions=number*len(program['links']));require(cost==expected,'native cost')
    return maximum

def audit_stream(data,stream,p,program,cfg,binding_for):
    from hcr.model import fingerprint
    rows=data['rows'];require(data['stream']==stream['key'] and len(rows)==18,'stream matrix');cache={a:None for a in p['arms']};expected=[];maximum=0.
    for index,cell in enumerate(stream['cells']):
        order=p['arms'][(index+stream['order_offset'])%3:]+p['arms'][:(index+stream['order_offset'])%3]
        for arm in order:expected.append((index,cell['key'],arm))
    require([(r['index'],r['cell'],r['arm']) for r in rows]==expected,'cell order')
    for row in rows:
        index,arm=row['index'],row['arm'];cell=stream['cells'][index];previous=cache[arm];binding=binding_for(arm);record=row['kernel'];drives=dict(f0=cfg['evidence_gain']*cell['scores'][0],f1=cfg['evidence_gain']*cell['scores'][1],goal=0.)
        require(row['binding']==binding and record['program']==program and record['program_sha256']==fingerprint(program) and record['drives']==drives,'input binding')
        gate=rational_gate(program,cfg,drives,p['weights']) if arm=='guarded' and previous is not None else None
        require(row['gate']==gate,'rational gate')
        if arm=='reset':choice=dict(action='reset',reason='baseline',source_cell=None)
        elif previous is None:choice=dict(action='reset',reason='no_source',source_cell=None)
        elif arm=='guarded' and not gate['eligible']:choice=dict(action='reset',reason='contraction_not_established',source_cell=None)
        else:choice=dict(action='warm',reason='past_state' if arm=='carry' else 'real_contraction_screen',source_cell=previous['cell'])
        initial={g['id']:.5 for g in program['groups']} if choice['action']=='reset' else previous['state']
        require(row['choice']==choice and row['source_available_cell']==(None if previous is None else previous['cell']) and freeze(record['initial'])==freeze(initial),'initial provenance')
        maximum=max(maximum,scalar(record,cfg,p['scalar_tolerance']))
        stable=record['convergence']['status'] in ('stable_decision','stable_ambiguous')
        written=3 if arm!='reset' and stable else 0;read=3 if choice['action']=='warm' else 0
        require(row['state_values_written']==written and row['state_values_read']==read and row['logical_state_payload_bytes']==written*8 and row['native_settle_calls']==1,'state/work ledger')
        require(row['gate_evaluations']==int(gate is not None),'gate count')
        for n in ['cpu_seconds','wall_seconds','gate_cpu_seconds','gate_wall_seconds']:require(type(row[n]) in (int,float) and math.isfinite(row[n]) and row[n]>=0,'timing values')
        require(row['gate_cpu_seconds']<=row['cpu_seconds']+1e-9 and row['gate_wall_seconds']<=row['wall_seconds']+1e-9,'timing inclusion')
        if gate is None:require(row['gate_cpu_seconds']==row['gate_wall_seconds']==0,'unperformed gate cost')
        cache[arm]=dict(cell=cell['key'],binding=binding,state=dict(record['state']),status=record['convergence']['status']) if written else None
    baseline={row['index']:row['kernel'] for row in rows if row['arm']=='reset'};outcomes=[]
    for row in rows:
        b=baseline[row['index']];k=row['kernel'];difference=max(abs(k['state'][n]-b['state'][n]) for n in b['state'])
        if row['choice']['action']=='reset':require(freeze(k)==freeze(b),'cold reset exact')
        outcomes.append(dict(index=row['index'],cell=row['cell'],arm=row['arm'],action=row['choice']['action'],status_changed=k['convergence']['status']!=b['convergence']['status'],readout_changed=k['adopted']!=b['adopted'],max_terminal_abs_difference=difference,quality_preserved=k['convergence']['status']==b['convergence']['status'] and k['adopted']==b['adopted'] and difference<=p['terminal_state_tolerance']))
    return outcomes,maximum
