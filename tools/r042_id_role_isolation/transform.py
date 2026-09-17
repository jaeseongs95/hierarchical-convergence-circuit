"""생산 입력 변환: begin 이전에 edge ID와 평가 world key만 일대일 재명명한다."""
from copy import deepcopy
from .contracts import EDGE_IDS, VARIANTS, require


def edge_map(variant: str) -> dict[str, str]:
    require(variant in VARIANTS, '미등록 ID 배치')
    mapping = {eid: eid for eid in EDGE_IDS}
    if variant == 'swap_SD':
        mapping.update(e0='e4', e4='e0', e1='e5', e5='e1')
    return mapping


def observation(source: dict, variant: str) -> dict:
    mapping = edge_map(variant)
    ids = [edge['id'] for edge in source['edges']]
    require(len(ids) == 7 and set(ids) == set(mapping), '기준 edge inventory 불일치')
    result = deepcopy(source)
    # 배열을 정렬하거나 slot, node, score, episode, revision을 변경하지 않는다.
    for edge in result['edges']:
        edge['id'] = mapping[edge['id']]
    return result


def worlds(source: dict, variant: str) -> dict:
    mapping = edge_map(variant)
    result = {}
    for name, truth in source.items():
        require(set(truth) == set(mapping), '평가 world edge inventory 불일치')
        result[name] = {mapping[eid]: value for eid, value in truth.items()}
    return result
