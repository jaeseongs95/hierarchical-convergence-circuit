# R0.3.8 / EXP-19 추가 소스

기준: `jaeseongs95/hierarchical-convergence-circuit`, main `d25f4bd4e3bd8c8aae763e3ee6542dbfd590900f`.

**질문:** proof를 잘 선택한 효과와, 그 선택을 일찍 적용해 미탐색 가지 계산을 생략한 효과를 분리할 수 있는가?

`native`, `posthoc_support`, `online_support`를 같은 입력/prior에서 비교한다. 기존 8개 대조와 미탐색 frontier가 남을 수 있도록 정의한 새 topology 6개, prior 2개를 사용해 84개 fresh native trial을 실행한다. 조기 채택 기회가 실제로 생기는지부터 독립 계측하며 기회 발생이나 성능 개선을 통과 조건으로 강제하지 않는다.

기존 엔진·R037 제어기·R035 selector를 재사용하는 additive overlay다. 원본 source/evidence, 학습 memory, raw 판단값을 고쳐서 성공 처리하지 않는다. 검사 가정 수/지원 가정 수의 혼동은 새 분석 및 선택적인 정정 sidecar에서 분리한다.

저장소 루트에 병합한 다음 `Run-HCR-R038.bat` 또는 `python -X utf8 -B Run-HCR-R038.py`를 실행한다. 기존 결과 `HCR-Evidence/exp18/r037-first`가 필요하다. 모든 Git commit/push는 사용자가 수행한다.

- 설계: `docs/R038_DESIGN.ko.md`
- 실행/결과 해석: `docs/R038_USAGE.ko.md`
- 실제 배포 검증 범위: `validation/r038/검증보고서.md`

## 추가 모듈의 역할

| 위치 | 역할 |
|---|---|
| `tools/r038_early_adoption/spec.py` | 고정 입력 grid, 비교군, 예산, 84개 trial 계획 |
| `runtime.py` | 기존 R037 실행과 분리된 사후 채택 wrapper |
| `audit.py` | native/선택 독립 auditor 연결, terminal·출처·stream 검증 |
| `metrics.py` | frontier, 완성 지지 경로, 차등 기회, 가정 수 재계산 |
| `reporting.py` | paired trio, 별도 비용 단위, 정답/오답/보류 집계 |
| `sources.py`, `protocol.py` | 출처 동결, 소스 보존, 단회 실행과 실패 원문 |
| `errata.py` | 원 EXP18을 보존하는 가정 수 정정 sidecar |
| `tests/` | 합성 경계·I/O·source·보고서 계약 검사 |
| `selector_tests/` | 실제 R035 selector와 합성 Graph의 연결 검사 |
| `native_tests/` | 실제 저장소에서 수행하는 필수 native 통합 검사 |
| `scripts/`, `Run-HCR-R038.*` | 단계별 CLI, 무결성 검사, 단회 실행 진입점 |
