"""Reference feedback, independent session/learning replay and paired analysis."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.model import Feedback
from hcr.prior_policy import read_scope
from hcr.evaluation.reference import assess, reachable
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.audit import validate_reservations, candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.candidate_audit import verify_candidate
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, seal, sha, unseal

SPEC_FINGERPRINT='21a5ab149c43db7461e24ad59fae2a793217a09795071881a0ae31c29f4ea6c2'


def verify_execution(plan,e,case,memory,gate,mode,identity):
    require(set(e)=={'packet','candidate','advances','ready','stop'},'Execution fields')
    states,report=packet_states(e['packet'])
    require(report['verified'],'Native state replay')
    doc=e['packet']['document'];core=doc['engine'];p=core['pending']
    require(doc['session_id']==identity,'Session identity')
    require(core['config']==plan['config'] and core['memory']==memory and states[0]['memory']==memory,'Config/seed memory')
    require(read_scope(core)=='route_only' and core['switches']==dict(use_circuits=gate,top_down=True,allow_reexpansion=True),'Policy/switches')
    require(not core['held'] and not core['feedback'] and not core['requests'],'Unlisted learning or observation')
    require(p['observation']==case['observation'] and p['mode']==mode,'Observation/mode')
    operations=[t['operation'] for t in doc['transitions']]
    require(operations==['init','begin']+['advance']*e['advances'],'Generation operations')
    bound=plan['config']['kernel']['max_ticks']*(2 if gate and memory['circuits'] else 1)
    validate_reservations(e,states,plan['limits'],bound)
    require(e['ready'] is p['ready'],'Ready flag')
    if e['ready']:
        require(e['stop']=='readout_ready' and e['candidate'] is not None,'Native candidate missing')
        require(e['candidate']['reference']['segment']==0,'Readout segment')
        verify_candidate(e['candidate'],e['packet'],states)
    else:
        require(e['candidate'] is None and e['stop']=='external_compute_budget','Partial execution status')
        require(e['advances']==plan['limits']['max_advances_per_session'] or p['cost']['kernel_ticks']+bound>plan['limits']['max_kernel_ticks_per_session'],'Premature budget stop')
    return states


def reference(case,e):
    obs=codec.observation_from(case['observation'])
    # Frozen authored toy world: each nonzero score's sign is actual passability.
    # This evaluator contract is independent of native activation and judgment.
    truth={edge.id:edge.score>0 for edge in obs.edges}
    if e['candidate'] is None:
        return dict(feedback=None,assessment=None,truth=truth,reason='no_completed_candidate')
    d=codec.adaptive_decision_from(e['candidate']['decision'])
    assessment=assess(d,obs,truth)
    f=Feedback('external-'+d.id,d.id,obs.digest,assessment.correct,
        assessment.proof_valid and assessment.assumption_correct is True)
    return dict(feedback=codec.plain(f),assessment=codec.plain(assessment),truth=truth,reason='independent_toy_reference')


def verify_training(plan,run,i):
    case=plan['training'][i-1];where=run/'training'/f'{i:02d}'
    r=unseal(load(where/'inference.json'),'hcc-r063-training-v1')
    require(r['plan_sha256']==fingerprint(plan) and r['episode']==i and r['case_id']==case['id'],'Training binding')
    memory=load(run/'memory'/f'{i-1}.json');require(r['memory_before']==memory,'Memory chain')
    verify_execution(plan,r['execution'],case,memory,True,'train','r063-train-'+case['id'])
    return r,reference(case,r['execution'])


def mutation_checks(plan,e,case,memory,gate,mode,identity):
    mutations={
        'advance_count':lambda x:x.update(advances=x['advances']+1),
        'source':lambda x:x['packet']['document']['source_hashes'].update({'unexpected.py':'0'*64}),
        'value':lambda x:x['packet']['document']['engine']['pending'].update(value=not x['packet']['document']['engine']['pending']['value']),
        'memory':lambda x:x['packet']['document']['engine']['memory'].update(version=99),
        'proof':lambda x:x['candidate']['decision']['proof'].update(primitive_depth=99),
        'support':lambda x:x['candidate']['diagnostic'].update(support_gap_edges=['invented']),
        'adoption':lambda x:x['candidate']['readout'].update(accepted=not x['candidate']['readout']['accepted']),
    }
    rejected=[]
    for name,mutate in mutations.items():
        bad=deepcopy(e);mutate(bad);bad['packet']['sha256']=fingerprint(bad['packet']['document'])
        try:verify_execution(plan,bad,case,memory,gate,mode,identity)
        except (ValueError,AssertionError,RuntimeError):rejected.append(name)
        else:raise AssertionError('Undetected mutation: '+name)
    return rejected


def metrics(e,case):
    truth=reachable(codec.observation_from(case['observation']),{x['id']:x['score']>0 for x in case['observation']['edges']})
    m=candidate_measures(e,truth);cost=counter_values(e)
    networks={x['payload']['network_id']:x['payload']['kind'] for x in e['packet']['document']['events'] if x['event']=='r02_network'}
    split={k:0 for k in ('pool','decision')}
    for event in e['packet']['document']['events']:
        if event['event']=='r02_tick':split[networks[event['payload']['network_id']]]+=1
    require(sum(split.values())==cost['kernel_ticks'],'Raw tick ledger')
    return dict(measures=m,cost=cost,network_ticks=split)


def final_audit(plan,run):
    formation=[]
    for i in range(1,len(plan['training'])+1):
        r,expected=verify_training(plan,run,i);where=run/'training'/f'{i:02d}'
        ref=unseal(load(where/'reference.json'),'hcc-r063-reference-v1')
        require(ref==dict(schema='hcc-r063-reference-v1',**expected,inference_sha256=load(where/'inference.json')['sha256']),'External reference/feedback')
        learn=unseal(load(where/'learning.json'),'hcc-r063-learning-v1')
        after=load(run/'memory'/f'{i}.json')
        require(learn['memory_after']==after and learn['feedback']==expected['feedback'],'Learning feedback and memory publication')
        if expected['feedback'] is None:
            require(learn['status']=='not_applied_no_candidate' and learn['packet'] is None and learn['patch'] is None and after==r['memory_before'],'No-candidate learning boundary')
        else:
            require(learn['status']=='applied','Feedback status')
            packet=learn['packet'];_,audit=packet_states(packet);require(audit['verified'],'Independent native learning replay')
            before=r['execution']['candidate']['packet']['document'];doc=packet['document']
            require(doc['transitions'][:-1]==before['transitions'] and doc['events'][:-2]==before['events'],'Feedback must extend exact assessed finish branch')
            require(doc['transitions'][-1]['operation']=='feedback' and doc['engine']['memory']==after,'Native memory publication')
            require(doc['events'][-2]['payload']==expected['feedback'] and doc['events'][-1]['payload']['patch']==learn['patch'],'Native feedback/patch binding')
        formation.append(dict(episode=i,case=r['case_id'],reference=expected['assessment'],
            circuits=[dict(id='pattern-'+fingerprint(c['pattern'])[:24],length=len(c['pattern']['relations']),strength=c['strength'],evidence_episodes=c['evidence_episodes']) for c in after['circuits']],
            pending=[dict(length=len(c['pattern']['relations']),evidence_episodes=c['evidence_episodes']) for c in after['pending']],
            patch=learn['patch'],inference=metrics(r['execution'],plan['training'][i-1])))
    rows=[]
    for n in (0,len(plan['training'])):
        memory=load(run/'memory'/f'{n}.json')
        for gate in (False,True):
            for case in plan['cases']:
                identity=f"m{n}-{'on' if gate else 'off'}-{case['id']}"
                r=unseal(load(run/'evaluation'/identity/'inference.json'),'hcc-r063-evaluation-v1')
                require(r['plan_sha256']==fingerprint(plan) and r['identity']==identity and r['case_id']==case['id'] and r['memory_count']==n and r['use_circuits'] is gate and r['memory_before']==memory,'Frozen factorial input binding')
                verify_execution(plan,r['execution'],case,memory,gate,'frozen_eval','r063-eval-'+identity)
                row=dict(identity=identity,memory_count=n,use_circuits=gate,case=case['id'],**metrics(r['execution'],case))
                if plan['purpose']=='implementation_validation':
                    row['rejected_mutations']=mutation_checks(plan,r['execution'],case,memory,gate,'frozen_eval','r063-eval-'+identity)
                rows.append(row)
    require(len(list((run/'evaluation').glob('*/inference.json')))==len(rows),'Exact evaluation coverage')
    pairs=[]
    for case in plan['cases']:
        cells={(r['memory_count'],r['use_circuits']):r for r in rows if r['case']==case['id']}
        preoff,preon,postoff,poston=[cells[k] for k in [(0,False),(0,True),(len(plan['training']),False),(len(plan['training']),True)]]
        def outcome(r):return {k:r['measures'][k] for k in ('raw_decision','accepted','adopted_value','proof_valid','support_gap_count')}
        p=dict(case=case['id'],pre_gate_outcome_equal=outcome(preoff)==outcome(preon),off_before_after_outcome_equal=outcome(preoff)==outcome(postoff),
            pre_gate_cost_equal=preoff['cost']==preon['cost'],off_before_after_cost_equal=preoff['cost']==postoff['cost'],
            circuit_reuses=poston['cost']['circuit_reuses'],post_gate_outcome_equal=outcome(poston)==outcome(postoff),
            expansion_delta=poston['cost']['expansions']-postoff['cost']['expansions'],
            kernel_tick_delta=poston['cost']['kernel_ticks']-postoff['cost']['kernel_ticks'],
            eligible=poston['cost']['circuit_reuses']>0 and all(r['measures']['execution_stop']=='readout_ready' and r['measures']['native_failure_reason'] is None and r['measures']['convergence_status']!='budget_exhausted' for r in (poston,postoff)))
        p['predictions']={k:('not_evaluable' if not p['eligible'] else 'supported' if v else 'falsified') for k,v in dict(expansion_reduction=p['expansion_delta']<0,kernel_tick_reduction=p['kernel_tick_delta']<0,outcome_preservation=p['post_gate_outcome_equal']).items()}
        pairs.append(p)
    return dict(verified=True,training=formation,rows=rows,pairs=pairs,
        research_training_executions=len(plan['training']) if plan['purpose']=='research' else 0,
        research_evaluation_executions=len(rows) if plan['purpose']=='research' else 0,
        independent_samples=False,actual_energy_joules=None,peak_memory_bytes=None,
        independent_formula_replay=True,independent_process=True,independent_researcher=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--episode',type=int);args=parser.parse_args();run=args.run
    plan=unseal(load(run/'plan.json'),'hcc-r063-plan-v1')
    spec=plan['spec'];require(fingerprint(spec)==SPEC_FINGERPRINT,'Exact frozen spec')
    key='research' if plan['purpose']=='research' else 'smoke'
    require(plan['purpose'] in ('research','implementation_validation'),'Purpose')
    require(plan['training']==spec[key]['training'] and plan['cases']==spec[key]['cases'],'Frozen matrix')
    require(plan['limits']==spec['limits'] and plan['config']==spec['config'],'Frozen config/budget')
    from hcr.circuits import AdaptiveMemory
    require(load(run/'memory/0.json')==AdaptiveMemory(codec.adaptive_config_from(plan['config']).signature).document(),'Empty initial memory')
    require(sha((run/'source_manifest.json').read_bytes())==plan['source_manifest_sha256'],'Source manifest binding')
    require(files(run/'source')==load(run/'source_manifest.json')['files'],'Frozen execution source')
    if args.episode is not None:
        r,result=verify_training(plan,run,args.episode)
        dump(run/'training'/f'{args.episode:02d}'/'reference.json',seal(dict(schema='hcc-r063-reference-v1',**result,
            inference_sha256=load(run/'training'/f'{args.episode:02d}'/'inference.json')['sha256'])))
    else:
        summary=final_audit(plan,run)
        require(not (FORBIDDEN|{'hcr.learning','hcr.compiler','tools.r063_formation.worker'}) & set(sys.modules),'Auditor imported native producer')
        dump(run/'summary.json',summary)
    print('independent audit passed',args.episode,flush=True)


if __name__=='__main__':main()
