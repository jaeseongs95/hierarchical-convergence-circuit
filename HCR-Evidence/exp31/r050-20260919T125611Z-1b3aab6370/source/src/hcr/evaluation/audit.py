"""실행 후 감사: 파일/이벤트, 매 tick의 별도 수치 재계산, proof·외부 채점과 집계.

runtime/dynamics/protocol/learning 구현을 import하지 않는다. Memory의 구조
역직렬화 검사는 공유한다. 이 감사는 보존 자료의 내부 일관성 검사이지
외부 실행의 인증이나 전체 학습 알고리즘의 독립 구현은 아니다.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from collections import Counter, defaultdict
from copy import deepcopy
from math import exp, isfinite
import hashlib
from ..model import Config, ContractError, fingerprint
from ..circuits import Memory
from .. import codec
from ..trace import check_chain
from .reference import assess, public_paths


def require(condition: bool, message: str) -> None:
    if not condition: raise ContractError('audit: '+message)


def independent_step(program: dict, state: dict, drives: dict, c: Config, top_down: bool) -> dict:
    """생산 kernel과 다른 루프 순서로 각 목표 노드의 입력을 모아 재계산한다."""
    out={}
    for group in program['groups']:
        key=group['id'];drive=group['bias']+drives.get(key,0.0)
        for link in program['links']:
            if link['target']==key and (top_down or link['kind']!='top_down'):
                drive+=link['weight']*(2*state[link['source']]-1)
        old=state[key]
        difference=(2*drive+(c.self_excitation+c.inhibition)*(2*old-1))/c.temperature
        probability=1/(1+exp(-difference)) if difference>=0 else exp(difference)/(1+exp(difference))
        out[key]=old+c.damping*(probability-old)
    return out


def validate_program(program: dict, observation, order: list, config: Config) -> None:
    require(set(order)==set(range(len(observation.edges))) and len(order)==len(observation.edges),'binding bijection')
    require(program['edge_count']==len(observation.edges),'program edge coverage')
    paths=program['paths']
    mapped={tuple(observation.edges[order[i]].id for i in path) for path in paths}
    require(len(mapped)==len(paths) and mapped==public_paths(observation),'all public candidate paths')
    expected_groups=[{'id':'e:'+str(i),'level':0,'bias':0.0} for i in range(len(order))]
    expected_links=[];ends=[];gain=config.relation_gain
    for i,path in enumerate(paths):
        prev=None
        for j,slot in enumerate(path):
            name=f'p:{i}:{j}';parents=['e:'+str(slot)] if prev is None else ['e:'+str(slot),prev]
            expected_groups.append({'id':name,'level':1,'bias':-gain*(len(parents)-1)})
            for parent in parents:
                expected_links += [dict(source=parent,target=name,weight=gain,kind='support'),
                                   dict(source=name,target=parent,weight=config.top_down_gain,kind='top_down')]
            prev=name
        ends.append(prev)
    expected_groups.append(dict(id='goal',level=1,bias=gain*(len(ends)-1)))
    for name in ends:
        expected_links += [dict(source=name,target='goal',weight=gain,kind='support'),
                           dict(source='goal',target=name,weight=config.top_down_gain,kind='top_down')]
    require(program['groups']==expected_groups and program['links']==expected_links,'authored signal grammar')


def independent_counts(rows: list[dict]) -> dict:
    result=dict(attempts=len(rows),correct=0,incorrect=0,unresolved=0,strict_correct=0,
                proof_valid_under_assumptions=0,wrong_stable=0,circuit_reuse=0)
    for row in rows:
        a=row['assessment'];key='unresolved' if a['correct'] is None else 'correct' if a['correct'] else 'incorrect'
        result[key]+=1
        result['strict_correct']+=a['correct'] is True and a['proof_valid'] and a['assumption_correct'] is True
        result['proof_valid_under_assumptions']+=a['proof_valid']
        result['wrong_stable']+=a['wrong_stable']
        result['circuit_reuse']+=row['decision']['method']=='circuit_reuse'
    return result


def verify_run(root: Path, *, check_source: bool=True) -> dict:
    root=Path(root).resolve()
    manifest=codec.loads((root/'manifest.json').read_bytes())
    require(manifest['schema']=='hcr-run-manifest-r01' and manifest['state']=='complete','run not complete')
    expected=manifest['files']
    actual=set()
    for p in root.rglob('*'):
        require(not p.is_symlink(),'symlink in run')
        if p.is_file() and p!=root/'manifest.json':actual.add(p.relative_to(root).as_posix())
    require(actual==set(expected),'missing or extra files')
    for name,digest in expected.items():
        rel=PurePosixPath(name)
        require(not rel.is_absolute() and '..' not in rel.parts and '\\' not in name,'unsafe manifest path')
        require(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,'file hash '+name)
    plan=codec.loads((root/'plan.json').read_bytes());config=Config(**plan['config'])
    require(config.signature==plan['config_signature'],'config hash')
    if check_source:
        project=Path(__file__).resolve().parents[3]
        for name,digest in plan['source_hashes'].items():
            require(name.startswith('src/hcr/') or name in ('hcr.py','configs/r01.toml'),'unsafe source path')
            require('..' not in PurePosixPath(name).parts,'unsafe source traversal')
            path=project/name
            require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest,'source differs '+name)
    require(plan['source_hash']==hashlib.sha256(codec.dumps(plan['source_hashes']).encode()).hexdigest(),'source map hash')
    status=codec.loads((root/'status.json').read_bytes())
    events=[codec.loads(line) for line in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    rows=[codec.loads(line) for line in (root/'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
    require(status['state']=='complete' and status['episode_records']==len(rows),'status coverage')
    check_chain(events,status['event_count'],status['event_head'])
    starts={};networks={};decisions={};assessments={};recalls={};feedbacks={};requests={};fulfilled=set();checkpoints=[]
    current=None;memory=None;steps=0;mem_updates=0;readouts={};explanations={};external_cost=Counter()
    for event in events:
        name,p=event['event'],event['payload']
        require(name in {'engine_created','attempt_started','circuit_recalled','expansion_started','graph_expanded',
            'expansion_exhausted','network_instantiated','tick','decision','external_assessment','feedback',
            'memory_updated','observation_requested','measurement_delivered','memory_checkpoint','circuit_reopened',
            'revision_unavailable','expansion_unavailable','decision_readout','explanation_reconstructed'},'unknown event type')
        if name=='engine_created':
            require(p['config']==plan['config'],'engine/config mismatch')
            memory=Memory.from_document(p['memory_document'],config)
            require(memory.digest==p['memory_hash'],'initial engine memory hash')
            current=p
        elif name=='attempt_started':
            require(current is not None,'attempt before engine')
            did=p['decision_id'];require(did not in starts,'duplicate attempt')
            observation=codec.observation_from(p['observation'])
            require(p['memory_hash']==memory.digest and p['memory_version']==memory.version,'memory changes without feedback')
            if p['revision_of'] is not None:
                previous=p['revision_of'];require(previous in requests,'revision not requested')
                request=requests[previous];require(previous in fulfilled,'revision has no public measurement')
                require(observation.episode_id==request['episode_id'] and observation.revision==request['revision'],'revision identity')
                old=starts[previous]['observation'];permitted=set(request['edge_ids'])
                require([(e.id,e.source,e.target) for e in observation.edges]==[(e.id,e.source,e.target) for e in old.edges],'revision changed topology')
                require(all(e.id in permitted or e.score==o.score for e,o in zip(observation.edges,old.edges)),'unrequested revision data')
            starts[did]=dict(event=p,observation=observation,engine=deepcopy(current),memory=deepcopy(memory))
        elif name=='circuit_recalled':
            did=p['decision_id'];require(did in starts,'recall before attempt')
            candidates=[c for c in starts[did]['memory'].circuits if c.id==p['circuit_id']]
            require(len(candidates)==1 and candidates[0].active,'unknown/inactive recalled circuit')
            c=candidates[0];obs=starts[did]['observation']
            required=config.prior_gain*c.strength*c.balance*max(1-abs(e.score or 0) for e in obs.edges)
            require(c.version==p['version'] and c.program.digest==p['program_digest'],'circuit version/program')
            require(c.strength==p['learned_strength'] and c.balance==p['learned_balance'] and abs(required-p['prior_drive'])<1e-12,'prior not from learned memory')
            recalls[did]=p
        elif name=='network_instantiated':
            did=p['decision_id'];require(did in starts and did not in networks,'network identity')
            obs=starts[did]['observation'];order=p['binding']['edge_order']
            require(p['binding']['observation_digest']==obs.digest and p['binding']['revision']==obs.revision,'stale binding')
            require(fingerprint(p['program'])==p['program_digest'],'program hash')
            validate_program(p['program'],obs,order,config)
            require(p['fresh_state'] is True and p['top_down']==starts[did]['engine']['top_down'],'fresh state/ablation')
            prior=recalls[did]['prior_drive'] if did in recalls else 0.0
            expected_drives={g['id']:prior if g['level']==1 else config.evidence_gain*(obs.edges[order[int(g['id'].split(':')[1])]].score or 0) for g in p['program']['groups']}
            require(p['drives']==expected_drives,'observation drives')
            networks[did]=dict(payload=p,state={g['id']:.5 for g in p['program']['groups']},ticks=0,stable=0,prior=prior)
        elif name=='tick':
            did=p['decision_id'];require(did in networks and did not in decisions,'tick order')
            n=networks[did];actual=independent_step(n['payload']['program'],n['state'],n['payload']['drives'],config,n['payload']['top_down'])
            require(set(actual)==set(p['state']),'tick state keys')
            require(all(isfinite(v) and abs(actual[k]-v)<2e-12 for k,v in p['state'].items()),'independent recurrence mismatch')
            residual=max(abs(actual[k]-n['state'][k]) for k in actual)
            require(abs(residual-p['residual'])<2e-12 and p['tick']==n['ticks']+1,'residual/tick')
            stable=n['stable']+1 if residual<=config.residual_tolerance else 0
            require(stable==p['stable_steps'],'stable persistence')
            n.update(state=dict(p['state']),ticks=p['tick'],stable=stable,residual=p['residual']);steps+=1
        elif name=='decision_readout':
            did=p['decision_id'];require(did in starts and did not in readouts and did not in decisions,'readout order');readouts[did]=p
        elif name=='explanation_reconstructed':
            did=p['decision_id'];require(did in readouts and did not in explanations and did not in decisions,'explanation order');explanations[did]=p
        elif name=='decision':
            did=p['id'];require(did in starts and did not in decisions,'decision order')
            require(did in readouts and did in explanations and p['value'] is readouts[did]['value'],'readout changed after explanation')
            require(p['proof']==explanations[did]['proof'] and explanations[did]['is_execution_trace'] is False,'reconstructed proof')
            origin=starts[did];obs=origin['observation']
            require(p['observation_digest']==obs.digest and p['mode']==origin['event']['mode'] and p['memory_version']==origin['memory'].version,'decision scope')
            if did in networks:
                n=networks[did];require(dict(p['state'])==n['state'] and p['convergence']['ticks']==n['ticks'],'decision state')
                require(abs(p['convergence']['residual']-n['residual'])<1e-12 and p['convergence']['stable_steps']==n['stable'],'decision stability observation')
                require(p['program_digest']==n['payload']['program_digest'],'decision program identity')
                expected_method='circuit_reuse' if did in recalls else 'graph_expansion'
                require(p['method']==expected_method and p['circuit_id']==(recalls[did]['circuit_id'] if did in recalls else None),'decision computation method')
                group_count=len(n['state']);link_count=len(n['payload']['program']['links'])
                require(p['cost']['dynamic_groups_created']==(0 if did in recalls else group_count),'dynamic group allocation')
                require(p['cost']['dynamic_links_created']==(0 if did in recalls else link_count),'dynamic link allocation')
                require(p['cost']['circuit_groups_instantiated']==(group_count if did in recalls else 0),'recall instantiation')
                margin=abs(2*n['state']['goal']-1)
                require(abs(margin-p['convergence']['margin'])<1e-12,'margin')
                if n['stable']>=config.patience:
                    wanted='stable_decision' if margin>=config.margin_threshold else 'stable_ambiguous'
                    value=n['state']['goal']>=.5 if wanted=='stable_decision' else None
                    if n['prior']==0 and all(e.score in (None,0) for e in obs.edges):wanted='unsupported';value=None
                    require(p['value'] is value and p['convergence']['status']==wanted,'decision readout')
                else:
                    require(p['value'] is None and p['convergence']['status'] in ('oscillating','budget_exhausted'),'unstable decision')
                links=[l for l in n['payload']['program']['links'] if n['payload']['top_down'] or l['kind']!='top_down']
                require(p['cost']['signal_transmissions']==len(links)*n['ticks'],'transmission counting')
                require(p['cost']['group_updates']==len(n['state'])*n['ticks'] and p['cost']['kernel_ticks']==n['ticks'],'update counting')
                require(p['cost']['normalization_ops']==p['cost']['group_updates'],'normalization counting')
            else:require(p['value'] is None,'answer without network')
            require(p['cost']['proof_nodes_reconstructed']==len(p['proof']['nodes']),'proof reconstruction cost')
            decisions[did]=p
        elif name=='external_assessment':
            require(p['decision_id'] in decisions and p['decision_id'] not in assessments,'external assessment order')
            assessments[p['decision_id']]=p['assessment']
        elif name=='feedback':
            did=p['decision_id'];require(did in assessments and did not in feedbacks and decisions[did]['mode']!='frozen_eval','feedback permission')
            aa=assessments[did];require(p['correct'] is aa['correct'] and p['proof_valid'] is (aa['proof_valid'] and aa['assumption_correct'] is True),'unauthorized feedback content')
            require(p['observation_digest']==decisions[did]['observation_digest'],'feedback binding')
            feedbacks[did]=p
        elif name=='memory_updated':
            patch=p['patch'];did=patch['decision_id'];require(did in feedbacks,'memory update before feedback')
            require(patch['before_hash']==memory.digest and patch['previous_version']==memory.version,'memory mutation outside safe boundary')
            new=Memory.from_document(p['memory_document'],config)
            require(new.version==memory.version+1 and new.digest==p['memory_after'],'memory version/hash')
            require(new.patches[-1]==patch and patch['feedback_id']==feedbacks[did]['id'],'memory provenance')
            if feedbacks[did]['correct'] is False:
                old_circuit=next((c for c in memory.circuits if c.id==decisions[did]['circuit_id']),None)
                if old_circuit:
                    nc=next(c for c in new.circuits if c.id==old_circuit.id)
                    require(abs(nc.strength-old_circuit.strength*config.weakening)<1e-12,'failure weakening')
            external_cost.update(p['cost']);memory=new;mem_updates+=1
        elif name=='observation_requested':
            did=p['decision_id'];require(did in feedbacks and feedbacks[did]['correct'] is False and decisions[did]['mode']=='adapt','observation requested too early')
            require(starts[did]['engine']['allow_reexpansion'] and did not in requests,'reexpansion denied/duplicate')
            obs=starts[did]['observation']
            allowed=[e.id for e in sorted(obs.edges,key=lambda e:(abs(e.score or 0),e.id)) if e.score is None or abs(e.score)<.9]
            require(p['edge_ids']==allowed and p['revision']==obs.revision+1,'measurement request contract')
            requests[did]=p
        elif name=='measurement_delivered':
            request=p['request'];did=request['decision_id']
            require(did in requests and request==requests[did] and did not in fulfilled,'measurement authorization')
            fulfilled.add(did)
        elif name=='memory_checkpoint':
            path=root/p['path'];mem=Memory.load(path,config)
            require(mem.digest==p['memory_hash'] and mem.version==p['memory_version'] and path.stat().st_size==p['bytes_written'],'checkpoint changed')
            checkpoints.append(p)
    require(len(decisions)==len(rows)==status['episode_records'],'decision/episode accounting')
    require(set(decisions)=={r['decision']['id'] for r in rows}==set(assessments),'decision/assessment IDs')
    proof_count=0;costs=defaultdict(Counter)
    for row in rows:
        d=codec.decision_from(row['decision']);obs=codec.observation_from(row['observation']);origin=starts[d.id]
        require(row['decision']==decisions[d.id] and codec.plain(origin['observation'])==row['observation'],'rewritten decision/observation')
        aa=codec.plain(assess(d,obs,row['external_truth']))
        require(aa==row['assessment']==assessments[d.id],'independent external/proof assessment')
        require(row['memory_before']==row['memory_after_inference']==origin['event']['memory_hash'],'frozen inference state')
        costs[row['phase']+'/'+row['arm']].update(row['decision']['cost'])
        costs[row['phase']+'/'+row['arm']]['verification_checks']+=aa['verification_checks']
        proof_count+=1
    summary=codec.loads((root/'summary.json').read_bytes())
    require(summary['training']==independent_counts([r for r in rows if r['phase']=='train']),'training summary')
    for arm in summary['frozen_eval']:
        require(summary['frozen_eval'][arm]==independent_counts([r for r in rows if r['phase']=='frozen_eval' and r['arm']==arm]),'group summary '+arm)
    require(summary['retention']==independent_counts([r for r in rows if r['phase']=='retention']),'retention summary')
    for arm,a in summary['adaptation'].items():
        rr=[r for r in rows if r['phase']=='adapt' and r['arm']==arm]
        require(a['attempts']==len(rr) and a['initial']==rr[0]['assessment'] and a['final']==rr[-1]['assessment'],'adaptation summary')
    require(summary['costs']=={k:dict(v) for k,v in costs.items()},'computation cost summary')
    require(summary['learning_costs']==dict(external_cost),'learning cost summary')
    require(summary['event_counts']==dict(Counter(e['event'] for e in events)) and summary['persistence_io']==checkpoints,'event/checkpoint summary')
    require(status['llm_calls']==summary['new_llm_calls']==0,'unexpected LLM scope')
    return {'schema':'hcr-run-verification-r01','verified':True,'state':'complete','file_hashes':len(expected),
            'events':len(events),'scalar_ticks_replayed':steps,'decisions_reassessed':proof_count,
            'memory_updates_checked':mem_updates,'checkpoints':len(checkpoints),'differences':[],
            'shared_components':['data serialization','memory schema/compiled-structure loader','external reference'],
            'independent_of_runtime':['tick numerical calculation','trace sequencing','core summaries','cost aggregation'],
            'limitations':'내부 일관성 검산이다. 외부 실행 인증/생물학 가설 증명/학습 전체의 독립 구현이 아니다.',
            'source_checked':check_source,'new_model_calls':0}
