# HCR R0.4.1 / EXP-22

## 목적

EXP-21에서 frontier의 ID-min 선택은 입력 순열별 경로·비용 격차를 제거했다.
이번에는 **일정한 실행 순서와 적은 계산 비용이 같은 성질인지** 구별한다.
`edge_id_max`를 추가하며, 기존 `input_order`와 `edge_id_min`은 원자료 회귀 대조로 유지한다.

| scheduler | 다음 작업 선택 |
|---|---|
| input_order | 기존 frontier head |
| edge_id_min | 기존 ID 경로 tuple 중 최소값 |
| edge_id_max | 기존 ID 경로 tuple 중 최대값 |

6 입력 순열 × 2 prior × 3 채택 방식 × 3 scheduler = 108회.
기존 두 scheduler 72회는 EXP-21 원 raw와 대조한다. 단일 topology의 paired 조작이다.

## 실행

프로젝트 루트에 `HCR_R041_EXP22_OneClick.cmd`를 놓고 더블클릭한다.
별도 ZIP을 적용했다면 루트의 `Run-HCR-R041.bat`를 실행한다.
원자료 기준선: `HCR-Evidence/exp21/r040-20260917T204742_957648Z`.
코드 기준선: `37bb3c19f27dfbd73de7519fc8cad399395bcf3a`.

## 구조

`tools/r041_scheduler_direction/`에는 역방향 scheduler, 독립 검산, parent provenance,
단회 실행·보고 모듈이 있다. `scripts/`의 R041 설치/CLI/검증은 별도 진입점이며 기존 파일은 바꾸지 않는다.
`docs/R041_DESIGN.ko.md`는 동결 설계, `docs/R041_USAGE.ko.md`는 적용·실행 안내다.
`validation/r041/`의 self-test는 합성 장치 검증이며 본 실험 결과와 합산하지 않는다.

## 결과 해석

`invariance_efficiency.csv`에서 순열별 범위 폭과 min/max의 평균 비용을 각각 본다.
`scheduler_contrasts.csv`는 세 방향 대조를, `paired.csv`는 각 scheduler 안의 채택 시점 비교를 담는다.
같은 정답을 유지한 비용 차이인지 별도 확인한다. 불변하지만 더 느리거나 결과가 나빠져도 삭제하지 않는다.
기존 원 proof와 adoption, native ticks와 scheduler/selector 비용을 분리하고, 미계측 비용은 null로 유지한다.
