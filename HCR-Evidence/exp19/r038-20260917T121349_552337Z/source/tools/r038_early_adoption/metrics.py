"""평가 전용 지표. 이 모듈의 기회/world 판정은 생산 controller에서 사용하지 않는다."""
from __future__ import annotations
from .contracts import demand, digest


def assumption_counts(view: dict, proof: dict | None) -> dict:
    edges = {e['id']:e for e in view['observation']['edges']}
    assumptions = [] if proof is None else proof['assumed_edges']
    seen = set(); flags = []
    for eid, truth in assumptions:
        demand(eid in edges and eid not in seen and type(truth) is bool, '가정 inventory의 ID/중복/값 오류')
        seen.add(eid)
        score = edges[eid]['score']
        flags.append(score is not None and abs(score) > view['min_abs_score'] and (score > 0) is truth)
    return dict(assumptions_checked=len(flags), supported_assumptions=sum(flags),
                unsupported_assumptions=len(flags)-sum(flags))


def frontier_at(run: dict, candidate: dict) -> int:
    """독립 검산된 native event prefix에서 frontier 수를 다시 계산한다."""
    document = run['packet']['document']
    generation = candidate['reference']['generation']
    end = document['transitions'][generation]['event_end']
    goal = document['engine']['pending']['observation']['goal']
    count = None
    for event in document['events'][:end]:
        payload = event['payload']
        if event['event'] == 'r02_workspace_created':
            demand(count is None, '하나의 trial에 여러 workspace가 숨겨졌습니다.')
            count = 1
        elif event['event'] == 'r02_expansion':
            demand(count is not None and count > 0, 'frontier 없는 expansion')
            count += -1 + sum(p['visited'][-1] != goal for p in payload['added'])
        elif event['event'] == 'r02_dead_end':
            demand(count is not None and count > 0, 'frontier 없는 retire')
            count -= 1
    demand(type(count) is int and count >= 0, 'frontier 계측 불가')
    return count


def opportunity(view: dict, native_accepted: bool, frontier_count: int) -> dict:
    """전체 topology의 지지 경로 존재와 workspace에 완성된 지지 경로를 구분한다."""
    supported = []
    for i, path in enumerate(view['completed_paths']):
        if all(view['observation']['edges'][s]['score'] is not None and
               view['observation']['edges'][s]['score'] > view['min_abs_score'] for s in path):
            supported.append(i)
    active = [i for i in supported if all(view['state'][f'e:{s}'] >= .5 for s in view['completed_paths'][i])]
    available = view['raw_value'] is True and bool(active)
    timing = available and frontier_count > 0
    return dict(frontier_count=frontier_count, supported_completed=supported,
        activation_eligible_supported=active, supported_positive_available=available,
        supported_frontier_opportunity=timing,
        differential_opportunity=timing and not native_accepted)


def semantic_events(events: list[dict]) -> list[dict]:
    """시간값과 그로부터 변하는 봉인 hash만 제외. 사건/경로/계수/activation은 유지한다."""
    excluded = {'sha256','previous','active_seconds','wall_seconds','capture_seconds','proof_finish_seconds'}
    def clean(value):
        if isinstance(value, dict):
            return {k:clean(v) for k,v in value.items() if k not in excluded}
        if isinstance(value, list): return [clean(v) for v in value]
        return value
    return clean(events)


def correctness(value, world_results: dict) -> str:
    if value is None: return 'abstained'
    return ('correct_in_all_declared_worlds' if
            all(r['external_correct'] is True for r in world_results.values()) else 'incorrect_in_some_declared_world')
