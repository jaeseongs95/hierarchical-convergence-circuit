"""외부 feedback 뒤에만 지속 상태를 바꾼다. 안정성/자기 확신을 정답으로 사용하지 않는다."""
from .model import Config,Observation,Decision,Feedback,Cost,ContractError,fingerprint
from .binding import Topology,bind
from .circuits import Memory,Pending
from .compiler import compile_pending,validate_structure
from .codec import plain


def update(memory:Memory,obs:Observation,decision:Decision,feedback:Feedback,topology,program,config:Config,cost:Cost) -> dict:
    if feedback.id in memory.consumed_feedback:raise ContractError('feedback replay')
    before=memory.digest;previous_version=memory.version;changed=[]
    target=next((c for c in memory.circuits if c.id==decision.circuit_id),None)
    if feedback.correct is False:
        if target is not None:
            old=target.strength;target.strength*=config.weakening;target.failures+=1;target.version+=1
            if target.failures>=3 and target.strength<0.05:target.active=False
            target.feedback_ids.append(feedback.id)
            changed.append({'kind':'weaken','circuit':target.id,'before_strength':old,'after_strength':target.strength,'active':target.active})
    elif feedback.correct is True and feedback.proof_valid and decision.value is not None and program is not None:
        if target is not None:
            old=target.strength;target.strength+=config.learning_rate*(1-target.strength);target.version+=1
            if obs.episode_id not in target.evidence_episodes:
                target.evidence_episodes.append(obs.episode_id)
                if decision.value:target.positive+=1
                else:target.negative+=1
            target.feedback_ids.append(feedback.id);target.proof_digests.append(fingerprint(plain(decision.proof)))
            changed.append({'kind':'reinforce','circuit':target.id,'before_strength':old,'after_strength':target.strength})
        else:
            # 기존 circuit 재사용을 끈 그래프 실행도 동일 구조에 대한 새 학습 증거가 될 수 있다.
            matched=memory.recall(obs,config,cost)
            if matched:
                c,binding=matched
                if obs.episode_id not in c.evidence_episodes:
                    c.evidence_episodes.append(obs.episode_id)
                    if decision.value:c.positive+=1
                    else:c.negative+=1
                    # 추가 측정으로 구조가 검증돼도 실패한 recall prior를 즉시 복원하지 않는다.
                    if decision.attempt == 1:
                        c.strength+=config.learning_rate*(1-c.strength)
                    c.version+=1
                    c.feedback_ids.append(feedback.id)
                    c.proof_digests.append(fingerprint(plain(decision.proof)))
                    changed.append({'kind':'validated_after_reopen' if decision.attempt > 1 else 'reinforce_from_expansion',
                                    'circuit':c.id,'after_strength':c.strength})
            else:
                item=None
                for q in memory.pending:
                    if bind(q.topology,obs,config,cost) is not None:item=q;break
                if item is None:
                    validate_structure(topology,program,config,cost)
                    if len(memory.pending)>=config.max_circuits:memory.pending.pop(0)
                    item=Pending(topology,program,[],[],[],0,0);memory.pending.append(item)
                if obs.episode_id not in item.episodes:
                    item.episodes.append(obs.episode_id);item.feedback_ids.append(feedback.id)
                    item.proof_digests.append(fingerprint(plain(decision.proof)))
                    if decision.value:item.positive+=1
                    else:item.negative+=1
                changed.append({'kind':'validated_graph','distinct_episodes':len(item.episodes)})
                if len(item.episodes)>=config.min_valid_episodes:
                    circuit=compile_pending(item,config,cost)
                    if len(memory.circuits)>=config.max_circuits:
                        removable=min(memory.circuits,key=lambda c:(c.active,c.strength,c.id))
                        changed.append({'kind':'prune','circuit':removable.id});memory.circuits.remove(removable)
                    memory.circuits.append(circuit);memory.pending.remove(item)
                    changed.append({'kind':'compile','circuit':circuit.id,'groups':len(circuit.program.groups),'links':len(circuit.program.links)})
    memory.consumed_feedback.append(feedback.id);memory.version+=1
    patch={'previous_version':previous_version,'version':memory.version,'before_hash':before,
           'feedback_id':feedback.id,'decision_id':decision.id,'changes':changed}
    memory.patches.append(patch);cost.memory_write_items+=len(changed)+1
    return patch
