"""원격 기준 소스와 EXP-15 원자료를 읽는다. 기존 source/evidence는 쓰지 않는다."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from . import storage as io
from .contracts import digest, require
from .spec import BASE_COMMIT


def repo_root(): return Path(__file__).resolve().parents[2]


def check_native(root=None):
    root = io.safe(root or repo_root())
    reg = io.load(Path(__file__).with_name('native_baseline.json'))
    require(reg['basis_commit'] == BASE_COMMIT and reg['schema'] == 'hcr-r035-native-baseline-v1', 'native 기준선 레지스트리')
    actual = {p.relative_to(root).as_posix() for p in (root/'src/hcr').rglob('*.py')}
    require(actual == set(reg['files']), 'src/hcr 파일 집합이 EXP-15 기준선과 다릅니다.')
    for name, h in reg['files'].items():
        require(io.text_hash(io.child(root,name)) == h, 'native 소스 불일치: '+name)
    return reg


def source_identity(source_run):
    root = io.safe(source_run); manifest = io.load(root/'manifest.json'); plan = io.load(root/'plan.json')
    require(manifest['schema'] == 'hcr-exp15-raw-manifest-v1' and manifest['state'] == 'raw_complete', 'EXP-15 raw manifest')
    require(plan['schema'] == 'hcr-exp15-plan-v1', 'EXP-15 plan schema')
    require(io.file_hash(root/'plan.json') == manifest['files']['plan.json'], 'EXP-15 plan checksum')
    return root, manifest, plan


def select_population(source_run):
    """정답/회복 여부를 기준으로 고르지 않는다. 8개 입력×2 scope의 expand_only 모두 사용."""
    root, manifest, plan = source_identity(source_run); c = plan['conditions']; cases = {x['name']:x for x in c['cases']}
    expected = {(name, scope): sorted(cases[name]['worlds'])[0] for name in cases for scope in c['scopes']}
    selected = {}
    for path in sorted(manifest['files']):
        if not path.startswith('raw/') or not path.endswith('.json'): continue
        data = io.read(io.child(root,path))
        require(io.sha_bytes(data) == manifest['files'][path], 'EXP-15 raw checksum: '+path)
        raw = io.loads(data.decode('utf-8')); cell = raw['cell']; key = (cell['case'],cell['scope'])
        if cell['group'] != 'main' or cell['arm'] != 'expand_only' or key not in expected or cell['world'] != expected[key]: continue
        require(key not in selected, 'EXP-15 중복 조건')
        basepath = 'baselines/'+cell['baseline_key']+'.json'
        basebytes = io.read(io.child(root,basepath)); require(io.sha_bytes(basebytes) == manifest['files'][basepath], 'EXP-15 baseline checksum')
        baseline = io.loads(basebytes.decode('utf-8'))
        require(raw['result']['schema'] == 'hcr-selection-flow-r034-v1' and raw['result']['arm'] == 'expand_only', 'EXP-15 flow schema')
        require(raw['result']['candidates'] and raw['result']['candidates'][0] == baseline['first'], '최초 응답 보존 불일치')
        selected[key] = dict(path=path, baseline_path=basepath, raw=raw, baseline=baseline,
                             raw_bytes=data, baseline_bytes=basebytes)
    require(set(selected) == set(expected), 'EXP-15 선정할 조건이 누락됐습니다.')
    return [selected[k] for k in sorted(selected)]


def snapshots(population):
    """source provenance는 정책 입력과 분리한다."""
    from .native_bridge import project
    result = []
    for item in population:
        cell = item['raw']['cell']
        for ordinal, candidate in enumerate(item['raw']['result']['candidates']):
            view = project(candidate)
            result.append(dict(id=f'n{len(result):04d}', source_file=item['path'],
                baseline_path=item['baseline_path'], candidate_ordinal=ordinal,
                candidate_id=candidate['candidate_id'], candidate_sha256=digest(candidate),
                case=cell['case'], scope=cell['scope'], baseline_key=cell['baseline_key'],
                phase='first' if ordinal == 0 else f'expanded_{ordinal}',
                native_readout=deepcopy(candidate['readout']), input=view,
                source_kernel_ticks=candidate['decision']['cost']['kernel_ticks']))
    return result


def full_native_audit(source_run):
    """요약 보고서를 신뢰하지 않고 기존 EXP-15 독립 evaluator를 재실행한다."""
    from hcr.evaluation.selection_protocol import verify_raw
    _, audit, _ = verify_raw(io.safe(source_run))
    require(audit['verified'] is True, 'EXP-15 독립 검산 실패')
    return audit
