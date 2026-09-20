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


def update_adaptive(memory, obs, decision, feedback, config, cost):
    """외부 검증을 받은 뒤 원자적으로 부분회로 memory를 갱신한다."""
    from copy import deepcopy
    from .circuits import AdaptiveMemory, PatternCircuit, PatternPending
    from .compiler import SubgraphCompiler
    if feedback.id in memory.consumed_feedback:
        raise ContractError('R0.2 feedback replay')
    working = deepcopy(memory)
    before = memory.digest
    changes = []
    if feedback.correct is False:
        for circuit in working.circuits:
            if circuit.id not in decision.circuit_ids:
                continue
            old = circuit.strength
            circuit.strength *= config.kernel.weakening
            circuit.failures += 1
            circuit.version += 1
            circuit.feedback_ids.append(feedback.id)
            if circuit.failures >= 3 and circuit.strength < .05:
                circuit.active = False
            changes.append(dict(kind='weaken', circuit=circuit.id,
                                before_strength=old, after_strength=circuit.strength, active=circuit.active))
    elif feedback.correct is True and feedback.proof_valid and decision.value is True:
        for pattern in SubgraphCompiler.extract(obs, decision, config, cost):
            circuit = next((c for c in working.circuits if c.id == pattern.id), None)
            if circuit is not None:
                if obs.episode_id not in circuit.evidence_episodes:
                    circuit.evidence_episodes.append(obs.episode_id)
                    circuit.feedback_ids.append(feedback.id)
                    circuit.proof_digests.append(fingerprint(plain(decision.proof)))
                    old = circuit.strength
                    # 오류 뒤 추가 측정은 검증 증거지만, 방금 약화한 prior를 즉시 되돌리지 않는다.
                    if decision.attempt == 1:
                        circuit.strength += config.kernel.learning_rate * (1 - circuit.strength)
                        circuit.active = True
                    circuit.version += 1
                    changes.append(dict(kind='validated_after_reopen' if decision.attempt > 1 else 'reinforce',
                                        circuit=circuit.id, before_strength=old, after_strength=circuit.strength))
                continue
            item = next((p for p in working.pending if p.pattern.id == pattern.id), None)
            if item is None:
                if len(working.pending) >= config.kernel.max_circuits:
                    changes.append(dict(kind='pending_capacity_reached', circuit=pattern.id))
                    continue
                item = PatternPending(pattern)
                working.pending.append(item)
            if obs.episode_id not in item.evidence_episodes:
                item.evidence_episodes.append(obs.episode_id)
                item.feedback_ids.append(feedback.id)
                item.proof_digests.append(fingerprint(plain(decision.proof)))
            changes.append(dict(kind='validated_subgraph', circuit=pattern.id,
                                distinct_episodes=len(item.evidence_episodes)))
            if len(item.evidence_episodes) >= config.kernel.min_valid_episodes:
                if len(working.circuits) >= config.kernel.max_circuits:
                    raise ContractError('R0.2 circuit capacity; no silent destructive pruning')
                working.circuits.append(PatternCircuit(pattern, .55, list(item.evidence_episodes),
                                                       list(item.feedback_ids), list(item.proof_digests)))
                working.pending.remove(item)
                changes.append(dict(kind='compile_subgraph', circuit=pattern.id, primitive_length=pattern.length))
    working.consumed_feedback.append(feedback.id)
    previous = working.version
    working.version += 1
    patch = dict(previous_version=previous, version=working.version, before_hash=before,
                 feedback_id=feedback.id, decision_id=decision.id, changes=changes)
    working.patches.append(patch)
    # 모든 구조/이력 계약을 통과한 새 문서만 원래 memory 객체에 반영한다.
    validated = AdaptiveMemory.from_document(working.document(), config)
    memory.__dict__.update(validated.__dict__)
    cost.learning_updates += 1
    cost.memory_write_items += len(changes) + 1
    cost.storage_bytes += len(codec_for_adaptive(memory.document()))
    return patch


def codec_for_adaptive(document):
    from .codec import dumps
    return dumps(document).encode('utf-8')
