"""초기화·checkpoint 시간을 요약 전에 append-only로 보존한다. 실측 시간 재현은 하지 않는다."""
from __future__ import annotations
import math
import os
from pathlib import Path
from collect import canonical, require, sha


class MeasurementJournal:
    def __init__(self, path: Path):
        self.stream = path.open('xb')
        self.count = 0
        self.head = '0' * 64

    def append(self, kind: str, payload: dict) -> None:
        require(not self.stream.closed, '닫힌 측정 journal')
        body = dict(seq=self.count, previous=self.head, event=kind, payload=payload)
        record = dict(body, sha256=sha(canonical(body)))
        self.stream.write(canonical(record) + b'\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.count += 1
        self.head = record['sha256']

    def close(self) -> None:
        self.stream.close()


def validate_measurements(records: list[dict], events: list[dict], persistence: dict) -> dict:
    previous = '0' * 64
    initialized, seen = [], set()
    io = {}
    finished = None
    for seq, record in enumerate(records):
        require(set(record) == {'seq', 'previous', 'event', 'payload', 'sha256'}, 'journal 필드')
        body = {k: record[k] for k in ('seq', 'previous', 'event', 'payload')}
        require(type(record['seq']) is int and record['seq'] == seq and record['previous'] == previous and sha(canonical(body)) == record['sha256'],
                'journal chain 불일치')
        previous = record['sha256']
        kind, p = record['event'], record['payload']
        expected_fields={
            'engine_initialized': {'key','memory_digest','trace_start_seq','trace_end_seq','memory_copy_seconds','engine_init_seconds'},
            'memory_saved': {'checkpoint','memory_digest','elapsed_seconds'},
            'memory_loaded': {'checkpoint','memory_digest','elapsed_seconds'},
            'probe_records_finished': {'inferences','elapsed_seconds'},
        }
        require(kind in expected_fields and set(p)==expected_fields[kind], '측정 event 필드 누락/추가')
        require(finished is None, '종료 뒤 측정 기록')
        for key, value in p.items():
            if key.endswith('_seconds'):
                require(type(value) in (int, float) and math.isfinite(value) and value >= 0, '잘못된 실측 시간')
        if kind == 'engine_initialized':
            require(p['key'] not in seen, '초기화 키 중복')
            seen.add(p['key'])
            a, b = p['trace_start_seq'], p['trace_end_seq']
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(events), '초기화 trace 경계')
            group = [e for e in events[a:b] if e['event'] == 'r02_engine_created']
            require(len(group) == 1 and group[0]['payload']['memory_hash'] == p['memory_digest'], '초기화 memory 연결')
            initialized.append(p)
        elif kind in ('memory_saved', 'memory_loaded'):
            require(kind not in io and p['memory_digest'] == persistence['memory_digest'], 'checkpoint 측정 중복/digest')
            require(p['checkpoint'] == 'live_after_adaptation.json', '측정 checkpoint')
            io[kind] = p
        elif kind == 'probe_records_finished':
            finished = p
            require(type(p['inferences']) is int and p['inferences'] == sum(e['event']=='r02_decision' for e in events),
                    '종료 inference 수')
        else:
            require(False, '알 수 없는 측정 event: ' + str(kind))
    require(len(initialized) == sum(e['event']=='r02_engine_created' for e in events), '초기화 기록 누락')
    require(set(io) == {'memory_saved','memory_loaded'} and finished is not None, 'checkpoint/종료 측정 누락')
    require(persistence['save_seconds'] == io['memory_saved']['elapsed_seconds']
            and persistence['load_seconds'] == io['memory_loaded']['elapsed_seconds'], '직렬화 시간 집계')
    return dict(initializations=initialized, finished=finished, time_values_replayed=False,
                chain_verified=True, recorded_values_and_aggregation_checked=True)
