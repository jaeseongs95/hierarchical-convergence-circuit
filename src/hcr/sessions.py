"""동일 R0.2 엔진을 generation 단위로 진행한다. snapshot/restore 비용은 추론 비용 밖이다."""
from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from uuid import uuid4
from pathlib import Path
from . import codec, session_io
from .model import AdaptiveConfig, Mode, ContractError, fingerprint, identifier
from .state import engine_document, restore_engine

SCHEMA = 'hcr-session-checkpoint-r021-v1'


def verify_packet(packet, *, check_source=True, expected_ref=None, expected_observation=None,
                  expected_memory_hash=None, expected_program_digest=None):
    try:
        return _verify_packet(packet, check_source=check_source, expected_ref=expected_ref,
                              expected_observation=expected_observation, expected_memory_hash=expected_memory_hash,
                              expected_program_digest=expected_program_digest)
    except ContractError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        raise ContractError('malformed session checkpoint: ' + str(exc)) from exc


def _verify_packet(packet, *, check_source=True, expected_ref=None, expected_observation=None,
                   expected_memory_hash=None, expected_program_digest=None):
    """기본 복원에서는 source 검사를 끌 수 없다. 검산 CLI에서만 과거 문서 범위를 제한해 읽는다."""
    from .evaluation.session_audit import verify_document
    if (not isinstance(packet, dict) or set(packet) != {'schema','document','sha256'}
            or packet['schema'] != SCHEMA or fingerprint(packet['document']) != packet['sha256']):
        raise ContractError('R0.2.1 checkpoint schema/checksum')
    doc = packet['document']
    if check_source and doc['source_hashes'] != session_io.source_hashes():
        raise ContractError('checkpoint/source differs; keep original source, do not rewrite old hashes')
    result = verify_document(doc)
    last = doc['transitions'][-1]
    ref = dict(session_id=doc['session_id'], generation=last['generation'], state_hash=last['after_state'],
               transition_hash=last['sha256'])
    if expected_ref is not None and expected_ref != ref:
        raise ContractError('unexpected/stale generation reference')
    core, pending = doc['engine'], doc['engine']['pending']
    if expected_memory_hash is not None and expected_memory_hash != fingerprint(core['memory']):
        raise ContractError('resume memory mismatch')
    if expected_observation is not None:
        raw = codec.plain(expected_observation)
        if pending is None or pending['observation'] != raw:
            raise ContractError('resume observation/revision mismatch')
    if expected_program_digest is not None:
        program = None if pending is None else pending['program']
        if program is None or fingerprint(program) != expected_program_digest:
            raise ContractError('resume program mismatch')
    return dict(result, source_checked=check_source, reference=ref, checkpoint_sha256=packet['sha256'])


class AdaptiveSession:
    """단일 writer 세션. 성공한 전이만 한꺼번에 반영하며 반환 데이터는 복사본이다.

    generation 0=init; begin/advance/finish/feedback/request_revision마다 +1.
    save/load는 generation도 기존 engine event ID도 바꾸지 않는다.
    """
    def __init__(self, config=None, memory=None, *, session_id=None, use_circuits=True,
                 top_down=True, allow_reexpansion=True):
        from .runtime import AdaptiveEngine
        self.session_id = session_id or 'session-' + uuid4().hex
        if not identifier(self.session_id):
            raise ContractError('session identity')
        self._sources = session_io.source_hashes()
        self._engine = AdaptiveEngine(config or AdaptiveConfig(), deepcopy(memory), use_circuits=use_circuits,
                                      top_down=top_down, allow_reexpansion=allow_reexpansion)
        self._transitions = []
        self._append('init', {}, 0, None)
        self.last_io = None

    @property
    def generation(self):
        return len(self._transitions) - 1

    @property
    def reference(self):
        t = self._transitions[-1]
        return dict(session_id=self.session_id, generation=self.generation,
                    state_hash=t['after_state'], transition_hash=t['sha256'])

    @property
    def phase(self):
        p = self._engine._pending
        return 'idle' if p is None else 'readout_ready' if p.ready else 'running'

    @property
    def memory_document(self):
        return self._engine.memory.document()

    @property
    def current(self):
        return engine_document(self._engine)

    @property
    def events(self):
        return self._engine.trace.records

    def _append(self, operation, arguments, start, before):
        p = self._engine._pending
        body = dict(generation=len(self._transitions), session_id=self.session_id,
            operation=operation, arguments=arguments, event_start=start, event_end=self._engine.trace.count,
            previous=self._transitions[-1]['sha256'] if self._transitions else '0'*64,
            before_state=before, after_state=fingerprint(engine_document(self._engine)),
            active_seconds=p.active_seconds if p else None)
        self._transitions.append(dict(body, sha256=fingerprint(body)))

    def _apply(self, operation, arguments, *args, **kwargs):
        before = fingerprint(engine_document(self._engine))
        if before != self._transitions[-1]['after_state'] or self._engine.trace._closed:
            raise ContractError('session mutated outside a committed generation')
        start = self._engine.trace.count
        # 세션 엔진은 외부 stream을 갖지 않는다. 실패는 원래 memory/workspace/trace에 반영하지 않는다.
        if self._engine.trace._stream is not None:
            raise ContractError('session requires an in-memory engine trace')
        candidate = deepcopy(self._engine)
        result = getattr(candidate, operation)(*args, **kwargs)
        if candidate.trace.count > 100000 or len(self._transitions) >= 10000:
            raise ContractError('session event/generation budget')
        old = self._engine
        self._engine = candidate
        try:
            self._append(operation, arguments, start, before)
        except BaseException:
            self._engine = old
            raise
        return deepcopy(result)

    def begin(self, observation, mode=Mode.FROZEN_EVAL, *, revision_of=None):
        if not hasattr(observation, 'digest') or not isinstance(mode, Mode):
            raise ContractError('typed observation/mode required')
        return self._apply('begin', dict(observation_digest=observation.digest, mode=mode.value, revision_of=revision_of),
                           observation, mode, revision_of=revision_of)

    def advance(self):
        return self._apply('advance', {})

    def finish(self):
        return self._apply('finish', {})

    def complete(self):
        if self.phase == 'idle':
            raise ContractError('no active attempt')
        while self.phase == 'running':
            self.advance()
        return self.finish()

    def feedback(self, feedback):
        return self._apply('feedback', dict(feedback_digest=fingerprint(codec.plain(feedback))), feedback)

    def request_revision(self, decision_id):
        return self._apply('request_revision', dict(decision_id=decision_id), decision_id)

    def packet(self):
        if fingerprint(engine_document(self._engine)) != self._transitions[-1]['after_state']:
            raise ContractError('uncommitted session state')
        doc = dict(session_id=self.session_id, source_hashes=dict(self._sources), engine=engine_document(self._engine),
                   events=self.events, transitions=deepcopy(self._transitions))
        return dict(schema=SCHEMA, document=doc, sha256=fingerprint(doc))

    def save(self, path: Path):
        started = perf_counter()
        path = session_io.new_output(path)
        packet = self.packet()
        audit = verify_packet(packet)
        raw = (codec.dumps(packet)+'\n').encode('utf-8')
        session_io.publish(path, raw)
        self.last_io = dict(operation='save', bytes=len(raw), wall_seconds=perf_counter()-started,
                            checkpoint_sha256=packet['sha256'], reference=self.reference)
        return dict(self.last_io, verified=audit['verified'])

    @classmethod
    def from_packet(cls, packet, **expected):
        if 'check_source' in expected:
            raise ContractError('restore cannot disable or replace source validation')
        audit = verify_packet(packet, **expected)
        doc = codec.loads(codec.dumps(packet['document']))
        obj = cls.__new__(cls)
        obj.session_id, obj._sources = doc['session_id'], doc['source_hashes']
        obj._engine = restore_engine(doc['engine'], doc['events'])
        obj._transitions = doc['transitions']
        obj.last_io = None
        return obj

    @classmethod
    def load(cls, path: Path, **expected):
        started = perf_counter()
        raw = session_io.read_bytes(path)
        obj = cls.from_packet(codec.loads(raw), **expected)
        obj.last_io = dict(operation='load', bytes=len(raw), wall_seconds=perf_counter()-started,
                           reference=obj.reference)
        return obj
