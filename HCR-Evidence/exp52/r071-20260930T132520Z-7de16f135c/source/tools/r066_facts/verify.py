"""Reconstruct the fact join from pinned evidence and replay native arithmetic independently."""
import argparse
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.reference import assess
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.common import canonical, dump, files, fingerprint, load, require, sha, unseal
from tools.r063_formation.audit import verify_execution, mutation_checks


def expected_facts(out, plan):
    request_doc = load(out/'parent/request.json')
    request = unseal(request_doc,'hcc-r064-request-v1')['request']
    measured = unseal(load(out/'parent/measurements.json'),'hcc-r064-measurements-v1')
    require(measured['request_sha256'] == request_doc['sha256'], 'Measurement/request binding')
    obs = measured['observations']['corrected_observation']
    require(obs['episode_id'] == request['episode_id'] and obs['revision'] == request['revision'], 'Measurement identity')
    by_id = {e['id']:e for e in obs['edges']}
    require(len(by_id) == len(obs['edges']) and set(request['edge_ids']) <= set(by_id), 'Unique measured IDs')
    result = []
    for edge_id in request['edge_ids']:
        e = by_id[edge_id];require(e['score'] in (-1.0,1.0), 'Binary measurement')
        result.append(dict(context=plan['fact_scope']['context'],epoch=plan['fact_scope']['epoch'],
            edge_id=edge_id,source=e['source'],target=e['target'],value={1.0:True,-1.0:False}[e['score']],
            provenance=dict(file='parent/measurements.json',sha256=sha((out/'parent/measurements.json').read_bytes()),
                request_sha256=measured['request_sha256'],episode_id=obs['episode_id'],revision=obs['revision'])))
    return result


def check_input(row, facts, case, channel, arm):
    supplied = facts if channel == 'edge_correction' else []
    stored = supplied if arm in ('record_only','lookup') else []
    require(row['channel']==channel and row['arm']==arm and row['scope']==case['scope'], 'Condition binding')
    require(row['original_input']==case['observation'] and row['supplied_facts']==supplied
        and row['stored_facts']==stored, 'Observation and fact provenance')
    # Independent keyed join; the producer uses a record-by-record scan.
    indexed = {(f['context'],f['epoch'],f['edge_id']):f for f in stored}
    require(len(indexed)==len(stored),'Research facts must be unique')
    actual=deepcopy(case['observation']);queries=[]
    if arm == 'lookup':
        for edge in actual['edges']:
            f=indexed.get((case['scope']['context'],case['scope']['epoch'],edge['id']))
            if f is not None:
                require((f['source'],f['target'])==(edge['source'],edge['target']),'Scoped edge endpoints')
                edge['score']={True:1.0,False:-1.0}[f['value']]
            queries.append(dict(edge_id=edge['id'],status='hit' if f is not None else 'unknown',
                value=None if f is None else f['value'],records=[] if f is None else [f]))
    comparisons=len(queries)*len(stored)
    require(row['queries']==queries and row['comparisons']==comparisons and row['actual_input']==actual,'Exact fact join/input intervention')
    require(row['explicit_input_intervention'] is (actual != case['observation']), 'Intervention label')
    expected=dict(binary_correctness_payload_bits=1,supplied_edge_value_bits=len(supplied),
        stored_edge_value_bits=len(stored),retrieved_edge_value_bits=sum(q['status']=='hit' for q in queries),
        table_serialized_bytes=len(canonical(stored)),lookup_queries=len(queries),record_comparisons=comparisons,
        prior_measurement_edge_values=len(supplied),new_external_measurement_calls=0,
        original_observation_presentations=1,native_observation_presentations=1,information_gain_bits=None)
    require(row['cost']==expected, 'Separate storage, retrieval and observation counters')


def main(out):
    plan=load(out/'plan.json');spec=load(out/'source/experiments/exp-47-fact-retrieval/frozen_spec.json')
    require(plan==spec,'Frozen plan')
    require(files(out/'source')==load(out/'source_manifest.json')['files'],'Source hash coverage')
    require(files(out/'parent')==plan['parent_files']==load(out/'input_manifest.json')['files'],'Pinned parent hashes')
    require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw coverage')
    world_path=out/'source/experiments/exp-47-fact-retrieval/reference_worlds.json'
    require(sha(world_path.read_bytes().replace(b'\r\n',b'\n'))==plan['worlds_sha256'],'Frozen private worlds')
    worlds=load(world_path); facts=expected_facts(out,plan); rows=[]; identities=set(); sample=None
    require(set(worlds)=={c['id'] for c in plan['cases']},'Exact private-world coverage')
    for channel,arm,gate,case in product(plan['channels'],plan['arms'],(False,True),plan['cases']):
        identity=f"{channel}-{arm}-{'on' if gate else 'off'}-{case['id']}";identities.add(identity)
        where=out/'evaluation'/identity; inp=load(where/'input.json');check_input(inp,facts,case,channel,arm)
        r=unseal(load(where/'inference.json'),'hcc-r066-inference-v1');e=r['execution']
        require(r==dict(schema='hcc-r066-inference-v1',identity=identity,channel=channel,arm=arm,use_circuits=gate,
            case=case['id'],plan_sha256=fingerprint(plan),input_sha256=sha((where/'input.json').read_bytes()),execution=e),'Inference binding')
        memory=load(out/'parent/memory'/f"{plan['channels'][channel]}.json")
        verify_execution(plan,e,dict(observation=inp['actual_input']),memory,gate,'frozen_eval','r066-'+identity)
        truth=worlds[case['id']]
        require(set(truth)=={'e0','e1'} and all(type(v) is bool for v in truth.values()),'Two-edge Boolean truth')
        obs=inp['actual_input']
        require([(x['id'],x['source'],x['target']) for x in obs['edges']]==[('e0','v0','v1'),('e1','v1','v2')]
            and (obs['start'],obs['goal'])==('v0','v2'),'Fixed-chain construct')
        target=truth['e0'] and truth['e1'];m=candidate_measures(e,target)
        external=None
        if e['candidate'] is not None:
            external=codec.plain(assess(codec.adaptive_decision_from(e['candidate']['decision']),codec.observation_from(obs),truth))
            if m['accepted']:require(external['correct'] is m['adopted_correct'],'Reference formula agreement')
        if sample is None and e['candidate'] is not None:sample=(e,inp,case,channel,arm,gate,memory,identity)
        rows.append(dict(identity=identity,channel=channel,arm=arm,use_circuits=gate,case=case['id'],
            input_sha256=r['input_sha256'],memory_sha256=fingerprint(memory),truth=truth,target=target,
            explicit_input_intervention=inp['explicit_input_intervention'],table_cost=inp['cost'],
            measures=m,native_cost=counter_values(e),external_assessment=external))
    require({p.name for p in (out/'evaluation').iterdir()}==identities and len(rows)==60,'Complete 60-cell matrix')
    rejected=[]
    base_case=plan['cases'][0]
    base=load(out/'evaluation'/f"edge_correction-lookup-off-{base_case['id']}"/'input.json')
    changes=[('scope',lambda x:x['scope'].update(epoch=99)),
        ('provenance',lambda x:x['stored_facts'][0]['provenance'].update(sha256='0'*64)),
        ('fact_value',lambda x:x['stored_facts'][1].update(value=True)),
        ('native_input',lambda x:x['actual_input']['edges'][1].update(score=1.0)),
        ('hidden_intervention',lambda x:x.update(explicit_input_intervention=False)),
        ('cost',lambda x:x['cost'].update(new_external_measurement_calls=1))]
    for name,mutate in changes:
        bad=deepcopy(base);mutate(bad)
        try:check_input(bad,facts,base_case,'edge_correction','lookup')
        except (ValueError,AssertionError):rejected.append(name)
        else:raise AssertionError('Undetected input mutation: '+name)
    if sample is not None:
        e,inp,case,ch,arm,gate,memory,identity=sample
        rejected += ['native_'+n for n in mutation_checks(plan,e,dict(observation=inp['actual_input']),memory,gate,'frozen_eval','r066-'+identity)]
    cells={(r['channel'],r['arm'],r['use_circuits'],r['case']):r for r in rows}
    comparisons=[]
    for ch,gate,case in product(plan['channels'],(False,True),plan['cases']):
        a,b,c=[cells[(ch,arm,gate,case['id'])] for arm in plan['arms']]
        require(a['memory_sha256']==b['memory_sha256']==c['memory_sha256'],'Matched native memory within channel')
        comparisons.append(dict(channel=ch,use_circuits=gate,case=case['id'],
            recording_only_same_native_measures=a['measures']==b['measures'],
            recording_only_same_native_cost=a['native_cost']==b['native_cost'],
            current_correct=a['measures']['adopted_correct'],lookup_correct=c['measures']['adopted_correct']))
    def correct(ch,arm,case):return [cells[(ch,arm,g,case)]['measures']['adopted_correct'] for g in (False,True)]
    predictions=dict(
        matching_retrieval_corrects=all(x is True for x in correct('edge_correction','lookup','same'))
            and all(x is False for x in correct('edge_correction','record_only','same')),
        binary_has_no_fact_intervention=all(not r['explicit_input_intervention'] for r in rows if r['channel']=='binary_feedback'),
        scope_mismatch_preserves_input=all(not r['explicit_input_intervention'] for r in rows if r['case'] in ('other_context','new_epoch')),
        silent_change_can_make_retrieval_wrong=all(x is False for x in correct('edge_correction','lookup','silent_change'))
            and all(x is True for x in correct('edge_correction','current','silent_change')),
        truthful_observation_suffices=all(x is True for x in correct('binary_feedback','current','truthful')))
    require(not (FORBIDDEN|{'hcr.learning','hcr.compiler','tools.r066_facts.worker','tools.r063_formation.worker'}) & set(sys.modules), 'Verifier imported producer')
    dump(out/'summary.json',dict(rows=rows,comparisons=comparisons,predictions=predictions,
        native_evaluations=60,new_learning_executions=0,independent_samples=False,
        information_gain_bits=None,actual_energy_joules=None,peak_memory_bytes=None))
    dump(out/'verification.json',dict(verified=True,native_formula_replays=60,rejected_mutations=rejected,
        independent_logic=True,independent_process=True,independent_researcher=False,
        missing_candidate_count=sum(r['measures']['raw_decision'] is None for r in rows)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
