"""Layout-v3 plan builder. A filename move also updates the actual test and catalog references."""
from __future__ import annotations
from pathlib import Path
import ast
import re
from fsops import LayoutError, encode, loads, safe, digest

BASE = 'afb5d5e5b67906b7697f16163e166f59b17e1655'
PREVIOUS_RUN = 'HCR-Evidence/repository-layout/phase2-v2-20260919T020845Z-5406ad54f3a6'
STATE = 'docs/current/LAYOUT_V3.json'
ORIGINALS = 'archive/layout-v3-originals'
LEGACY = {
    'Run-HCR-R02.ps1': 'tests/test_r02_audit_cli.py',
    'Run-HCR-R021.ps1': 'tests/test_r021_cli.py',
    'Run-HCR-R03.ps1': 'tests/test_r03_methods.py',
    'Run-HCR-R031.py': 'tests/test_r031_prior_scope.py',
    'Run-HCR-R032.py': 'tests/test_r032_grounding.py',
    'Run-HCR-R033.py': 'tests/test_r033_review.py',
}
PINS = {
 'Run-HCR-R02.ps1': '3956724defd3b92e842c5f02d793b1a13129f337',
 'Run-HCR-R021.ps1': 'cff7e77307cbe429e59118cd875e4ce5f6bc8db3',
 'Run-HCR-R03.ps1': '4318c0c6de40cb14cb137eb5e8a5bdcb6e60d4a6',
 'Run-HCR-R031.py': '0424790fd504d546666b88ca414b0ed346e4812e',
 'Run-HCR-R032.py': 'e9b00d92faba886dcef5b4de013db42e10561675',
 'Run-HCR-R033.py': '1140f56f1ce7c739eb623b5aa10aa49a18edb78f',
 'tests/test_r02_audit_cli.py': '06161debd6d41cf576b75cb386887c9ed881b66c',
 'tests/test_r021_cli.py': 'b72f7aff1b4ba096f446f487d9a82350b13ae0b5',
 'tests/test_r03_methods.py': '415ef656dc5e83b160a56543c20ece195ea83367',
 'tests/test_r031_prior_scope.py': '5ccfacc85f41a9fa9376749c5d87d195a6634551',
 'tests/test_r032_grounding.py': '4bd74f1f53916ab335066979f8a21528c6480f41',
 'tests/test_r033_review.py': '7c6c002aed896502dbc968c12a31e620543e36e6',
 'scripts/run_indexed_experiment.py': '10506e1f5de681652d2db7de6fc88b42369141a8',
}
CURRENT = {'EXP-29': 'Run-HCR-R048.py', 'EXP-30': 'Run-HCR-R049.py'}


def move_map() -> dict:
    return {name: 'scripts/legacy/' + name for name in LEGACY}


def relocate_launcher(name: str, raw: bytes) -> bytes:
    if name.endswith('.py'):
        old, new, count = b'Path(__file__).resolve().parent', b'Path(__file__).resolve().parents[2]', 2
    else:
        old, new, count = b'= $PSScriptRoot', b'= Split-Path -Parent (Split-Path -Parent $PSScriptRoot)', 1
    if raw.count(old) != count:
        raise LayoutError('Unexpected launcher bootstrap: ' + name)
    result = raw.replace(old, new)
    if name.endswith('.py'):
        ast.parse(result.decode('utf-8-sig'))
    return result


def relocate_test(name: str, raw: bytes) -> bytes:
    old, new = name.encode(), ('scripts/legacy/' + name).encode()
    # Current upstream has exactly one occurrence in each of these six modules.
    if raw.count(old) != 1:
        raise LayoutError('Unexpected test-path occurrence count: ' + name)
    result = raw.replace(old, new)
    ast.parse(result.decode('utf-8-sig'))
    return result


def catalog(root: Path) -> dict:
    result = loads(safe(root, 'experiments/INDEX.json').read_bytes())
    result['layout_schema'] = 'hcc-layout-v3-catalog'
    result['inventory_commit'] = BASE  # NEVER replace the runs' source_commit fields.
    seen = set()
    for row in result['experiments']:
        eid = row['experiment_id']
        if eid in seen:
            raise LayoutError('Duplicate experiment: ' + eid)
        seen.add(eid)
        for field in ('legacy_python_entrypoint', 'release_manifest'):
            path = row.get(field)
            if path in LEGACY:
                row[field] = 'scripts/legacy/' + path
            elif path:
                match = re.fullmatch(r'(?:Run-HCR-R|R)(\d{3})(?:\.py|_MANIFEST\.json)', path)
                if match and 34 <= int(match.group(1)) <= 47:
                    row[field] = 'archive/releases/r' + match.group(1) + '/' + path
        row['current_python_entrypoint'] = CURRENT.get(eid)
        if eid in CURRENT:
            row['execution_status'] = 'installed_current_contract'
        elif row.get('legacy_python_entrypoint'):
            row['execution_status'] = 'historical_requires_original_checkout'
        else:
            row['execution_status'] = 'no_registered_python_driver'
    if not set(CURRENT).issubset(seen) or result['default_experiment'] != 'EXP-30':
        raise LayoutError('Unexpected current/default experiment mapping.')
    return result


def index_markdown(index: dict) -> bytes:
    lines = ['# 실험 색인', '',
             '현재 실행 가능 여부는 `execution_status`, 원자료 존재·연구 판정은 기존 `run_status` 등 별도 필드를 따른다.',
             '과거 실행기의 보관 위치를 현재 실행 가능한 계약으로 표시하지 않는다.', '',
             '| EXP | 실행 상태 | 실행기·보관 위치 | 설계 |', '|---|---|---|---|']
    for r in index['experiments']:
        loc = r.get('current_python_entrypoint') or r.get('legacy_python_entrypoint')
        target = f'[{loc}](../{loc})' if loc else '등록 없음'
        des = r.get('design')
        design = f'[설계](../{des})' if des else '별도 확인'
        lines.append(f"| {r['experiment_id']} | {r['execution_status']} | {target} | {design} |")
    lines += ['', 'R034~R047의 원 manifest도 같은 `archive/releases/rNNN/` 아래에 보존한다.',
              '기존 source_commit과 run_status는 이번 정리로 새 판정하거나 덮어쓰지 않는다.', '']
    return '\n'.join(lines).encode('utf-8')


def guide() -> bytes:
    return '''# 현재 구조와 실행 계약

## 세 종류의 경로

**현재 실험 실행:** `Run-HCR.cmd` → `scripts/run_indexed_experiment.py` → 기존 R049/EXP-30.
R048/EXP-29도 명시적으로 선택할 수 있다. 기본값·실행 인수·작업 디렉터리·실험 소스는 변경하지 않는다.

**구버전 실행기와 회귀 계약:** R02/R021/R03/R031/R032/R033은 `scripts/legacy/`로 이동한다.
실행기가 계산하는 저장소 루트와 여섯 테스트 모듈의 참조 경로를 함께 변경한다.
테스트의 assertion과 테스트 ID는 유지한다. root에 compatibility wrapper를 또 만들지 않는다.
이전 release 검사를 포함하는 역사적 드라이버이며, 현재 전체 checkout에서 과거 실험이
그대로 재현된다고 보증하는 경로가 아니다. 정확 재현에는 원본 commit/source를 사용한다.

**보존 자료:** R034~R047 파일은 기존 `archive/releases/` 위치와 바이트를 유지한다.
색인의 옛 루트 경로를 실제 archive 위치로 갱신하고, 실행 가능한 최신 항목과 구분한다.
`--list`나 `--describe EXP-15`는 조회만 하며, archive를 자동 재설치하거나 실행하지 않는다.

## 사용

```text
Run-HCR.cmd --list
Run-HCR.cmd --check-index
Run-HCR.cmd --describe EXP-30
Run-HCR.cmd
```

위에서 마지막 명령만 기본 연구 실험을 실행한다. 구조 정리 자체는
`scripts/maintenance/layout_v3/ORGANIZE.cmd`를 실행한다.

## 그대로 보존하는 계약

`src/hcr/`, `tools/`, `configs/`, 기존 `HCR-Evidence/`, 기존 archive release,
R048/R049 manifest와 등록 파일은 수정하지 않는다. R049가 R048의 원 manifest blob까지
고정하고 있어 이 부분을 옮기면 경로 수정 이상의 release chain 변경이 되기 때문이다.

과거 `RELEASE_MANIFEST.json`은 배포 시점의 경로·바이트 목록이다. 이번 경로 이전을 반영하려고
그 기대 해시를 다시 만들지 않으며, 이를 새 레이아웃 전체에 대한 인증서로 표시하지 않는다.
기존 manifest나 봉인 결과의 기대 해시를 바꿔서 검증을 통과시키지 않는다.
변경 전 README·실행기·테스트·색인은 `archive/layout-v3-originals/`에 원래 바이트로 보존한다.
현재 레이아웃 변경분은 `LAYOUT_V3.json`과 정리 evidence의 전후 해시로 관리한다.

## 정리 검증

preflight → 원본·plan 동결 → 파일/참조/색인 정리 → 독립 구조 감사 → core 회귀시험 1회 → 최종 해시 감사.
정리 전/중간에 전체 테스트를 실행하지 않는다. 기존 정상 실행의 skip 목록을 읽어
기존 미측정 상태로 유지하며, 새 skip·error·failure는 통과로 바꾸지 않는다.
기존 skip이 실제 pass가 된 경우는 별도 개선으로 기록한다.

실패 시 이번 변경분만 바이트를 확인해 되돌린다. 외부에서 달라진 파일은 강제로 덮어쓰지 않는다.
기존 로그는 수정하지 않고 `HCR-Evidence/repository-layout/layout-v3-*/`에 새 실행을 남긴다.
강제종료 후 복구는 같은 도구 폴더의 `RECOVER.cmd`가 수행한다. 자동 재시도는 없다.
'''.encode('utf-8')


def build(root: Path, package: Path) -> tuple[dict, dict[str, bytes | None]]:
    changes: dict[str, bytes | None] = {}
    transformations = []
    for name, test in LEGACY.items():
        raw = safe(root, name).read_bytes()
        new = 'scripts/legacy/' + name
        if safe(root, new).exists():
            raise LayoutError('Legacy destination already exists: ' + new)
        changes[new] = relocate_launcher(name, raw)
        changes[name] = None
        before_test = safe(root, test).read_bytes()
        changes[test] = relocate_test(name, before_test)
        transformations.append({'source': name, 'destination': new, 'test': test})
    idx = catalog(root)
    changes['experiments/INDEX.json'] = encode(idx)
    changes['experiments/INDEX.ko.md'] = index_markdown(idx)
    changes['docs/current/REPOSITORY_GUIDE.ko.md'] = guide()
    changes['scripts/legacy/README.ko.md'] = b'# Legacy drivers\n\n'
    changes['scripts/legacy/README.ko.md'] += '구버전 실행기와 회귀 계약의 보존 경로다. 현재 실행 상태는 ../../experiments/INDEX.json과 ../run_indexed_experiment.py로 확인한다. 원본은 ../../archive/layout-v3-originals/에 보존한다.\n'.encode('utf-8')
    for dest, src in [('README.md', 'README.md'), ('README.ko.md', 'README.ko.md'),
                      ('START_HERE.ko.md', 'START_HERE.ko.md'),
                      ('scripts/run_indexed_experiment.py', 'run_indexed_experiment.py')]:
        changes[dest] = (package / 'payload' / src).read_bytes()
    backups = {}
    for name in list(changes):
        p = safe(root, name)
        if p.is_file():
            target = ORIGINALS + '/' + name
            if safe(root, target).exists():
                raise LayoutError('Historical backup collision: ' + target)
            raw = p.read_bytes()
            backups[target] = raw
    changes.update(backups)
    changes[ORIGINALS + '/.gitattributes'] = b'* -text -filter -ident !working-tree-encoding\n'
    changes[ORIGINALS + '/.gitignore'] = b'# Preserve every original input byte.\n!*\n'
    meta = {'schema': 'hcc-layout-v3', 'base_commit': BASE,
            'transformations': transformations,
            'regression_receipt': PREVIOUS_RUN + '/regression.json',
            'default_experiment': idx['default_experiment'],
            'expected_immutable': ['src/', 'tools/', 'configs/', 'HCR-Evidence/',
                                   'archive/releases/', 'R048_MANIFEST.json', 'R049_MANIFEST.json'],
            'originals': {p: digest(b) for p, b in backups.items()},
            'installed_outputs': {p: None if b is None else digest(b) for p, b in changes.items()}}
    if safe(root, STATE).exists():
        raise LayoutError('Layout state already exists; verify instead of overwriting.')
    changes[STATE] = encode(meta)
    return meta, changes
