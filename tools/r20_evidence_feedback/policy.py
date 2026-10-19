"""Fixed public lineage checks; declared source separation is not truth proof."""
import math
from hcr.model import fingerprint


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identifiers(values):
    return isinstance(values, list) and len(values)==len(set(values)) and all(isinstance(v,str) and 0<len(v)<=64 for v in values)


def validate(case):
    require(set(case)=={'id','revision','measurements','context','measurement_ids','aux'},'public fields')
    require(isinstance(case['id'],str) and 0<len(case['id'])<=64,'public identity')
    require(type(case['revision']) is int and case['revision']>=0,'public revision')
    require(case['measurement_ids']==['f0','f1'],'primary measurement roles')
    require(isinstance(case['measurements'],list) and len(case['measurements'])==2 and
        all(type(v) in (int,float) and math.isfinite(v) and -1<=v<=1 for v in case['measurements']),'public measurements')
    require(type(case['context']) in (int,float) and case['context'] in (-1,1),'public context')
    aux=case['aux']
    if aux is not None:
        require(set(aux)=={'source_id','revision','measurement_ids','parents','score'},'aux fields')
        require(isinstance(aux['source_id'],str) and 0<len(aux['source_id'])<=64,'aux source')
        require(type(aux['revision']) is int and aux['revision']>=0,'aux revision')
        require(identifiers(aux['measurement_ids']) and len(aux['measurement_ids'])>0 and identifiers(aux['parents']),'aux measurement lineage')
        require(type(aux['score']) in (int,float) and math.isfinite(aux['score']) and -1<=aux['score']<=1,'aux score')


def decide(case, lower, specification):
    checks=0
    def result(action,reason):
        return dict(action=action,reason=reason,predicate_checks=checks,
            public_sha256=fingerprint(case),lower_sha256=fingerprint(lower))
    checks+=1
    if lower['convergence']['status']=='stable_decision':
        return result('readout_only','lower_already_decided')
    checks+=1
    if lower['convergence']['status']!='stable_ambiguous':
        return result('abstain','lower_unsettled')
    aux=case['aux'];checks+=1
    if aux is None:
        return result('abstain','missing_aux')
    checks+=1
    if aux['source_id'] not in specification['aux_source_ids']:
        return result('abstain','unregistered_source')
    checks+=1
    if aux['revision']!=case['revision']:
        return result('abstain','stale_aux_revision')
    checks+=1
    if set(aux['measurement_ids']+aux['parents']) & set(case['measurement_ids']):
        return result('abstain','shared_measurement_lineage')
    checks+=1
    if abs(aux['score'])<specification['aux_min_abs_score']:
        return result('abstain','weak_aux_score')
    checks+=1
    if (aux['score']>0)!=(case['context']>0):
        return result('abstain','aux_context_disagreement')
    return result('feedback','fresh_disjoint_compatible_aux')
