"""R0.3: 동결 memory를 공유하는 방법별 session의 메모리 내 interleaving.

동일한 총 advance/tick/message 상한. disk checkpoint는 교대 루프에 없다.
새 회로·prior 규칙은 만들지 않으며 RouteHint는 frontier 순서만 바꾼다.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, fields
from time import perf_counter
from . import codec
from .model import AdaptiveConfig, AdaptiveCost, ContractError, Mode, Observation, fingerprint
from .circuits import AdaptiveMemory
from .sessions import AdaptiveSession
from .integration import METHODS, RouteHint, hints_from_expansion, integrate
from .trace import Trace

ARMS = ('sequential', 'associative', 'fixed', 'adaptive', 'fixed_no_messages', 'adaptive_no_messages')


@dataclass(frozen=True)
class MethodConfig:
    max_advances: int = 12
    max_kernel_ticks: int = 2048
    max_messages: int = 64
    first_method: str = 'associative'

    def __post_init__(self):
        for name, upper in (('max_advances', 256), ('max_kernel_ticks', 100000), ('max_messages', 1024)):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= upper:
                raise ContractError('bounded nonnegative method budget: ' + name)
        if self.first_method not in METHODS:
            raise ContractError('unknown first method')


def canonical_cost(cost):
    return {f.name: cost[f.name] for f in fields(AdaptiveCost)}


def worker_cost(worker):
    current = worker.current
    if current['pending'] is not None:
        cost = canonical_cost(current['pending']['cost'])
        cost['wall_seconds'] = current['pending']['active_seconds']
        return cost
    if current['held']:
        return canonical_cost(next(iter(current['held'].values()))['decision']['cost'])
    return canonical_cost(AdaptiveCost().snapshot())


def prefix_choice(method, frontier, inbox):
    """동일 입력에서 breadth-first / 기존 DFS+macro. peer 힌트는 기존 prefix만 우선."""
    if not frontier:
        raise ContractError('no frontier to prioritize')
    for packet in reversed(inbox):
        path = tuple(packet['path'])
        matches = [p for p in frontier if tuple(p['path']) == path[:len(p['path'])]]
        if matches:
            chosen = min(matches, key=lambda p: (-len(p['path']), tuple(p['path'])))
            return chosen['path'], packet['id'], 'peer_path_hint'
    if method == 'sequential':
        p = min(frontier, key=lambda p: (len(p['path']), tuple(p['path'])))
        return p['path'], None, 'breadth_first_primitive'
    return frontier[0]['path'], None, 'depth_first_macro'


def tick_reservation(worker, config):
    """기존 advance는 pool 1회 + decision 1회 이하. 실행 전의 보수적 상한 예약.

    실제 실행/preview 후 취소하지 않는다. 예약이 부족하면 해당 quantum을 실행하지 않는다.
    """
    core = worker.current
    p = core['pending']
    if p is None or p['ready']:
        return 0
    pool = core['switches']['use_circuits'] and p['revision_of'] is None and bool(core['memory']['circuits'])
    return config.kernel.max_ticks * (1 + int(pool))


def choose_worker(arm, order, feasible, inboxes, views, last, turn):
    if not feasible:
        return None, 'budget_or_completion'
    if arm.startswith('adaptive'):
        # Public mismatch and received route hints only. No correct/world labels.
        chosen = max(feasible, key=lambda k: (bool(inboxes[k]),
            views[k]['pending']['mismatch']['magnitude'], -last[k], -order.index(k)))
        return chosen, 'peer_hint_then_mismatch_then_age'
    for offset in range(len(order)):
        candidate = order[(turn + offset) % len(order)]
        if candidate in feasible:
            return candidate, 'fixed_round_robin'
    raise ContractError('unreachable scheduler state')


class MethodEngine:
    """한 공개 Observation의 동결 비교. 원시 상태·메시지·반응을 evidence로 반환한다."""
    def __init__(self, config=None, memory=None, method_config=None):
        self.config = config or AdaptiveConfig()
        if not isinstance(self.config, AdaptiveConfig):
            raise ContractError('MethodEngine requires AdaptiveConfig')
        self.memory = memory if memory is not None else AdaptiveMemory.empty(self.config)
        if not isinstance(self.memory, AdaptiveMemory):
            raise ContractError('MethodEngine requires AdaptiveMemory')
        AdaptiveMemory.from_document(self.memory.document(), self.config)
        self.method_config = method_config or MethodConfig()
        if not isinstance(self.method_config, MethodConfig):
            raise ContractError('MethodEngine requires MethodConfig')
        self.last_trace = None

    def infer(self, observation: Observation, *, arm='adaptive') -> dict:
        if not isinstance(observation, Observation) or arm not in ARMS:
            raise ContractError('typed public observation and known M arm required')
        started = perf_counter()
        control = Trace(); self.last_trace = control
        cfg = self.method_config
        names = (arm,) if arm in METHODS else METHODS
        order = tuple(k for k in (cfg.first_method, *METHODS) if k in names)
        order = tuple(dict.fromkeys(order))
        enabled = len(names) > 1 and not arm.endswith('_no_messages')
        initial_memory = self.memory.document(); memory_hash = self.memory.digest
        control.emit('r03_start', dict(observation=codec.plain(observation), memory_digest=memory_hash,
            adaptive_config=codec.plain(self.config), method_config=codec.plain(cfg), arm=arm,
            methods=list(names), order=list(order), messages_enabled=enabled))
        workers = {k: AdaptiveSession(self.config, self.memory, session_id='r03-' + k,
                                    use_circuits=k == 'associative') for k in names}
        for name in names:
            workers[name].begin(observation, Mode.FROZEN_EVAL)
        initialization_seconds = perf_counter() - started
        inboxes = {k: [] for k in names}; guidance = {k: [] for k in names}; last = {k: -1 for k in names}
        seen = set(); decisions = {}; turns = used_ticks = messages = 0
        exhausted = False
        while True:
            running = [k for k in order if workers[k].phase == 'running']
            if not running:
                break
            if turns >= cfg.max_advances:
                exhausted = True
                control.emit('r03_stopped', dict(reason='shared_advance_budget', used_advances=turns,
                    used_kernel_ticks=used_ticks, unused_kernel_ticks=cfg.max_kernel_ticks-used_ticks))
                break
            views = {k: workers[k].current for k in names}
            reservations = {k: tick_reservation(workers[k], self.config) for k in running}
            feasible = [k for k in running if reservations[k] <= cfg.max_kernel_ticks - used_ticks]
            chosen, reason = choose_worker(arm, order, feasible, inboxes, views, last, turns)
            if chosen is None:
                exhausted = True
                control.emit('r03_stopped', dict(reason='conservative_tick_admission',
                    used_advances=turns, used_kernel_ticks=used_ticks,
                    unused_kernel_ticks=cfg.max_kernel_ticks-used_ticks, reservations=reservations))
                break
            worker = workers[chosen]
            before_gen = worker.generation
            before_cost = worker_cost(worker)
            frontier = views[chosen]['pending']['workspace']['frontier']
            available_hints = guidance[chosen] + inboxes[chosen]
            path, hint_id, priority_reason = prefix_choice(chosen, frontier, available_hints)
            consumed = [p['id'] for p in inboxes[chosen]]
            for packet in inboxes[chosen]:
                hint = RouteHint.from_packet(packet)
                hint.validate(observation, memory_hash, workers[hint.sender].events)
            default_path = prefix_choice(chosen, frontier, [])[0]
            guidance[chosen] = available_hints
            inboxes[chosen] = []
            control.emit('r03_scheduled', dict(turn=turns, worker=chosen, reason=reason,
                before_generation=before_gen, reservation_ticks=reservations[chosen],
                used_kernel_ticks=used_ticks, selected_path=path, default_path=default_path,
                priority_reason=priority_reason, selected_hint_id=hint_id, consumed_hint_ids=consumed))
            # This operation only reorders already instantiated frontier nodes.
            worker.prioritize_frontier(path)
            event_start = len(worker.events)
            worker.advance()
            hints = []
            if enabled:
                peer = next(k for k in names if k != chosen)
                hints = hints_from_expansion(chosen, peer, observation, memory_hash,
                                             worker.events, worker.generation, event_start)
            if worker.phase == 'readout_ready':
                decisions[chosen] = codec.plain(worker.finish())
            after_cost = worker_cost(worker)
            delta = {k: after_cost[k] - before_cost[k] for k in before_cost}
            if not 0 <= delta['kernel_ticks'] <= reservations[chosen]:
                raise ContractError('quantum exceeded reserved kernel bound')
            used_ticks += delta['kernel_ticks']; turns += 1; last[chosen] = turns - 1
            control.emit('r03_advanced', dict(turn=turns-1, worker=chosen,
                after_generation=worker.generation, phase=worker.phase, cost_delta=delta,
                provisional_value=decisions[chosen]['value'] if chosen in decisions else None))
            for hint in hints:
                key = (hint.sender, hint.receiver, hint.path)
                if key in seen:
                    continue
                seen.add(key)
                if messages >= cfg.max_messages:
                    control.emit('r03_message_dropped', dict(id=hint.id, reason='message_budget'))
                    continue
                messages += 1
                inboxes[hint.receiver].append(hint.packet())
                control.emit('r03_message', hint.packet())
        result = integrate(decisions, names, observation)
        counters = Counter()
        for worker in workers.values():
            counters.update(worker_cost(worker))
            if worker.memory_document != initial_memory:
                raise ContractError('M comparison changed frozen memory')
        if self.memory.digest != memory_hash:
            raise ContractError('caller memory changed')
        packets = {k: s.packet() for k, s in workers.items()}
        control.emit('r03_integrated', dict(result=result, used_advances=turns, used_kernel_ticks=used_ticks,
            messages_sent=messages, budget_boundary=exhausted))
        elapsed = perf_counter() - started
        return dict(schema='hcr-method-result-r03-v1', arm=arm, observation=codec.plain(observation),
            adaptive_config=codec.plain(self.config), method_config=codec.plain(cfg),
            initial_memory=initial_memory, memory_digest=memory_hash, methods=list(names),
            result=result, decisions=decisions, workers=packets, controller=control.records,
            cost=dict(counters), budget=dict(used_advances=turns, used_kernel_ticks=used_ticks,
                max_advances=cfg.max_advances, max_kernel_ticks=cfg.max_kernel_ticks,
                unused_kernel_ticks=cfg.max_kernel_ticks-used_ticks, messages_sent=messages,
                max_messages=cfg.max_messages, budget_boundary=exhausted),
            timing=dict(total_wall_seconds=elapsed, initialization_seconds=initialization_seconds,
                        engine_active_seconds=counters['wall_seconds'],
                        management_seconds=max(0.0, elapsed-counters['wall_seconds']),
                        checkpoint_io_seconds=0.0, timing_is_not_a_resource_limit=True),
            boundaries=dict(memory_updated=False, learning_policy_changed=False, prior_policy_changed=False,
                message_drives_injected=False, disk_checkpoint_in_interleaving=False,
                os_parallelism=False, kernel_tick_preemption=False,
                conservative_reservation_can_leave_unused_budget=True))
