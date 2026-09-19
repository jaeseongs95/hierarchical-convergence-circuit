# R051 구현 중 확인한 실패

연구 결과와 별개의 구현 검증 기록이다.

1. 초기 계약 테스트에서 JSON 생성 시 기본 config의 `4.0`이 `4`로 바뀌어
   native memory/config 서명이 맞지 않았다. 원본 config의 숫자 표현을 보존했고,
   정수/실수 표현까지 fingerprint로 검사하는 회귀 테스트를 추가했다.

2. 최초 validate-only run `r051-20260919T131752Z-33818e3861`은
   신규 selftest 13개와 smoke 2개 기준선·8개 분기의 독립 audit를 통과했지만,
   core 회귀의 기존 CLI 테스트에서 실패 1개·오류 1개가 발생했다.
   원인은 checkout의 tests를 실행하면서 import 경로를 동결 source에 연결한 것이다.
   동결 source에는 core·tests·addon만 있어, 기존 R02 검산기가 필수로 요구하는
   repository-level `hcr.py`, `configs/r01.toml`, `configs/r02.toml`이 없었다.
   이 때문에 fixture의 source 목록과 auditor의 필수 inventory가 달랐다.
   기존 R050처럼 회귀검사의 source와 tests를 둘 다 checkout root로 맞췄다.
   core와 기존 tests, 감사 기준은 수정하지 않았다.

최초 실패 evidence와 로그는 해당 `HCR-Evidence/r051-validation` 하위 경로에 보존한다.
수정된 실행기는 새 validation run을 사용하며 실패 run을 성공으로 변경하지 않는다.
원클릭 실행 자체에는 자동 retry를 넣지 않았다. 후속 검증 결과는 해당 run receipt로 판단한다.
