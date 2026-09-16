#!/usr/bin/env python3
"""개념→소스·시험 정의·명세·로드맵의 연결을 검사한다. HCR/시험을 실행하지 않는다."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

CATALOG = 'evidence/concept_coverage.json'
STATUSES = {'implemented_scoped', 'partial', 'planned'}


class CoverageError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise CoverageError(message)


def normalized_sha(raw: bytes) -> str:
    raw.decode('utf-8')
    return hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    require(isinstance(name, str) and bool(name), '빈 경로')
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and rel.as_posix() == name and '..' not in rel.parts
            and '\\' not in name and ':' not in name and rel.parts[0] not in {'.git', 'runs'},
            '허용하지 않는 경로: ' + name)
    path = root
    for part in rel.parts:
        path = path / part
        require(not path.is_symlink() and not (hasattr(path, 'is_junction') and path.is_junction()),
                '링크/junction을 따라가지 않음: ' + name)
    require(path.resolve().is_relative_to(root.resolve()), '저장소 경계 이탈')
    return path


def load_json(path: Path):
    require(path.stat().st_size <= 8 * 1024 * 1024, 'catalog 크기 한도')
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, '중복 JSON key: ' + key)
            obj[key] = value
        return obj
    def finite(value):
        result = float(value)
        require(math.isfinite(result), '비유한 JSON 숫자')
        return result
    def bad(value):
        raise CoverageError('비유한 JSON 값: ' + value)
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=bad, parse_float=finite)


def find_symbol(tree: ast.AST, symbol: str):
    node = tree
    for part in symbol.split('.'):
        matches = [n for n in getattr(node, 'body', ())
                   if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == part]
        require(len(matches) == 1, '소스 정의 누락/중복: ' + symbol)
        node = matches[0]
    return node


def check_registry(root: Path, catalog: dict) -> dict:
    require(root.is_dir() and not root.is_symlink()
            and not (hasattr(root, 'is_junction') and root.is_junction()), '기존 저장소 필요')
    require(catalog.get('schema') == 'hcr-concept-coverage-v1', 'catalog schema')
    require(catalog.get('assessment_basis') == 'source_review_not_research_proof', '판정 범위 누락')
    sources = catalog['sources']
    require(isinstance(sources, list), 'source 배열 필요')
    source_ids = {s['id'] for s in sources}
    require(len(source_ids) == len(sources), 'source ID 중복')
    for source in sources:
        require(isinstance(source['title'], str) and bool(source['title']), 'source 제목 필요')
        require(bool(re.fullmatch('[0-9a-f]{64}', source['sha256'])), 'source SHA-256 필요')
    concepts = catalog['concepts']
    ids = [c['id'] for c in concepts]
    require(len(ids) == len(set(ids)), 'concept ID 중복')
    require(set(ids) == set(catalog['required_concepts']), '필수 concept 누락/추가')
    require(len(catalog['required_concepts']) == len(set(catalog['required_concepts'])), '필수 ID 중복')
    anchors = []
    cache = {}
    for concept in concepts:
        require(concept['status'] in STATUSES, '허용하지 않는 구현 상태')
        require(bool(concept['scope']) and bool(concept['remaining']), '범위/남은 작업 필요')
        require(bool(concept['stages']) and all(isinstance(s, str) and s for s in concept['stages']), '담당 단계 필요')
        require(bool(concept['sources']) and set(concept['sources']) <= source_ids, '원문 source 연결 오류')
        require(bool(concept['anchors']), '근거 anchor 필요')
        code_seen = False
        for anchor in concept['anchors']:
            name = anchor['path']
            if name not in cache:
                path = safe_path(root, name)
                require(path.is_file() and path.stat().st_size <= 8 * 1024 * 1024, '파일 누락/크기: ' + name)
                raw = path.read_bytes()
                cache[name] = (raw, raw.decode('utf-8'))
            raw, text = cache[name]
            require(anchor['kind'] in {'code', 'test_definition', 'design', 'theory'}, 'anchor 종류')
            if 'normalized_sha256' in anchor:
                require(normalized_sha(raw) == anchor['normalized_sha256'], '검토 뒤 변경된 근거 파일: ' + name)
            if 'symbol' in anchor:
                require(name.endswith('.py'), 'Python 정의 anchor의 확장자')
                node = find_symbol(ast.parse(text, filename=name, feature_version=(3, 12)), anchor['symbol'])
                line = node.lineno
            else:
                token = anchor['contains']
                require(isinstance(token, str) and bool(token) and token in text, '문서 anchor 누락: ' + name)
                line = text[:text.index(token)].count('\n') + 1
            code_seen |= anchor['kind'] == 'code'
            anchors.append(dict(concept_id=concept['id'], path=name, line=line, kind=anchor['kind']))
        if concept['status'] == 'implemented_scoped':
            require(code_seen, '구현 범위 표시에 실제 code anchor 필요')
    return dict(schema='hcr-concept-coverage-check-v1', state='complete',
                concepts=len(concepts), files_checked=len(cache), anchors_checked=len(anchors),
                status_counts=dict(Counter(c['status'] for c in concepts)), anchors=anchors,
                anchor_consistency_checked=True, semantics_proved=False,
                project_imported=False, tests_executed=False, inference_executed=False)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    try:
        report = check_registry(args.repo, load_json(safe_path(args.repo, CATALOG)))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (CoverageError, OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        print(json.dumps(dict(state='failed', error=str(error)), ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
