"""Exact-rational real-map contraction screen, not a native rounding certificate."""
from fractions import Fraction as F
from math import isfinite

def encoded(value):return dict(numerator=value.numerator,denominator=value.denominator)
def decoded(value):return F(value['numerator'],value['denominator'])

def certificate(program,config,drives,weights):
    ids=[g['id'] for g in program['groups']]
    if set(weights)!=set(ids) or any(F(v)<=0 for v in weights.values()):raise ValueError('norm weights')
    damping=F(config['damping']);temperature=F(config['temperature']);self_term=F(config['self_excitation'])+F(config['inhibition']);rows=[]
    for g in program['groups']:
        incoming=[e for e in program['links'] if e['target']==g['id']]
        center=2*(F(g['bias'])+F(drives.get(g['id'],0)))
        radius=2*sum(abs(F(e['weight'])) for e in incoming)+self_term
        distance=max(F(0),abs(center)-radius)/temperature
        polynomial=sum((distance**k)/f for k,f in [(0,1),(1,1),(2,2),(3,6),(4,24)])
        derivative=min(F(1,4),1/polynomial)
        weighted=(1-damping)+damping*derivative*(2*self_term+4*sum(abs(F(e['weight']))*F(weights[e['source']])/F(weights[g['id']]) for e in incoming))/temperature
        rows.append(dict(group=g['id'],z_distance_lower=encoded(distance),sigmoid_derivative_upper=encoded(derivative),weighted_row_upper=encoded(weighted)))
    q=max(decoded(row['weighted_row_upper']) for row in rows)
    return dict(rows=rows,q_upper=encoded(q),eligible=q<=F(19,20),scope='ideal real-valued map over [0,1]^n; not binary64/finite-stop proof')

def choose(arm,previous,binding,gate,ids):
    neutral={k:.5 for k in ids}
    if arm=='reset':return neutral,dict(action='reset',reason='baseline',source_cell=None)
    if arm not in ('carry','guarded'):raise ValueError('arm')
    if previous is None:return neutral,dict(action='reset',reason='no_source',source_cell=None)
    if previous['binding']!=binding:return neutral,dict(action='reset',reason='binding_changed',source_cell=None)
    if previous['status'] not in ('stable_decision','stable_ambiguous'):return neutral,dict(action='reset',reason='nonstable_source',source_cell=None)
    state=previous['state']
    if set(state)!=set(ids) or any(type(v) is not float or not isfinite(v) or not 0<=v<=1 for v in state.values()):raise ValueError('source state')
    if arm=='guarded' and (gate is None or not gate['eligible']):return neutral,dict(action='reset',reason='contraction_not_established',source_cell=None)
    return dict(state),dict(action='warm',reason='past_state' if arm=='carry' else 'real_contraction_screen',source_cell=previous['cell'])
