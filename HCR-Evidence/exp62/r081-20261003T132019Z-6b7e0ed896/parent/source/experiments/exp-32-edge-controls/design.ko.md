# EXP-32 / R051 — 고정 edge 위치와 top-down 대조

계약: `r051-fixed-edge-controls-v1`

## 이어받은 관찰과 미확인 문제

EXP-31의 실제 재시작 비교는 강도 0.02, 관계 ++의 4조건이었다.
동일 입력과 revision-only는 상태·궤적이 같았다. score 한 개를 1.0으로 바꾸면
4조건 모두 상태가 달라졌으나, top-down OFF의 2조건만 synthetic reference truth에 맞게 채택됐다.
OFF는 slot0, ON은 slot1을 조작했으므로 기존 대비에는 top-down과 조작 위치가 혼재한다.
근거와 반론은 `DISCUSSION.ko.md`에 기록한다.

## 동결된 최소 조건

관계 ++, 두 score=0.02인 길이 2 chain을 고정한다.
identity 배치 2종 × top-down OFF/ON = 4개 기준선이다.
빈 memory, 기존 기본 config, use_circuits=True, allow_reexpansion=True,
judgment_prior=legacy, frozen_eval을 유지한다. 기존 core와 R050 실행기를 수정하지 않는다.

| arm | revision | 관측 score | 추가 실행 |
|---|---:|---|---|
| hold | 0 | (0.02, 0.02) | 없음 |
| revision_only | 1 | (0.02, 0.02) | 새 session 1회 |
| edge0 | 1 | (1.0, 0.02) | 새 session 1회 |
| edge1 | 1 | (0.02, 1.0) | 새 session 1회 |

slot은 observation 배열에 고정된 경로상의 구조 위치다. literal ID나 진단의 추천으로 선택하지 않는다.
16개 paired record는 16개 독립 표본이 아니다. 기준선은 4회만 계산하고 12회 추가 session을 분기한다.
arm 실행 여부는 최초 결과나 성공 여부에 따라 바뀌지 않는다. 실패 후 두 번째 edge를 추가하지 않는다.
각 session은 최대 8 advance, 1,280 kernel ticks이며 advance 전에 최대 tick 예약을 검사한다.

## 개입과 대조의 경계

직접 공개 score를 바꾸는 실험자 개입이다. 측정 요청/응답, consume_measurement,
native choose_action, 독립 센서, 학습, 상태 이어가기를 실행하지 않는다.
모든 재시작은 동일 실행 함수를 사용하며, target/request/response 객체를 native에 전달하지 않는다.
따라서 공통 revision-only가 대조군이다. 측정 경로를 후속에 포함한다면 slot별 echo를 다시 설계해야 한다.
native session ID는 재사용한 어댑터의 `r050-` prefix 뒤에 `r051-cNNN` case ID를 붙인다.
이를 R050 연구 run으로 집계하지 않으며 R051 schema, plan, evidence 위치로 구분한다.

## 사전 비교와 판정

- hold 대 revision_only: bookkeeping과 fresh session만으로 수치 상태·궤적이 달라지는지 확인한다.
- 같은 TD·identity에서 edge0 대 edge1: 변경 score 수와 총 강도 증가를 맞춘 위치 대비다.
- 같은 slot·identity에서 TD OFF 대 ON: 설정에 따른 반응 차이를 본다. 특정 내부 기제를 단독 원인으로 확정하지 않는다.
- 같은 TD·arm에서 identity 반전: 구조 slot 기준의 수치·채택 대칭을 확인한다. 표본 수를 늘리는 반복실험이 아니다.

비교 허용오차는 abs_tol=rel_tol=1e-12다. 구조나 tick 수가 다르면 궤적 차이로 남긴다.
proof 유효성, support gap, internal edge conflicts, raw decision, terminal adoption을 별도로 기록한다.
synthetic reference truth는 고정된 ++ chain의 True이며 auditor만 채점에 사용한다.
채택=False를 오답이나 정답으로 합산하지 않는다. budget/native/proof/support 실패를 구분한다.
가설이 틀려도 원자료·개입 계약이 지켜지면 실행은 유효하다. 기대 정답을 강제로 만들지 않는다.

## 무엇을 추가하지 않는가

both arm은 위치 수와 총 강도 증가를 함께 바꾸므로 이번 위치 대비에 필수적이지 않다.
강도 1.0 기준선은 EXP-31에서 이미 TD ON/OFF 모두 채택됐다. 새 단위 테스트의 native sanity로만 확인한다.
관계 +-, 다른 길이·강도, 학습된 memory, prior나 kernel 수정은 이번 계약 밖이다.

## 비용·증거·검증

baseline native counters는 기준선당 한 번, 추가 counters는 arm별로 집계한다.
kernel ticks, signal transmissions, proof 노드 재구성, restart 수, 실제 변경 slot 수를 분리한다.
measurement_calls=0이며 에너지·프로세스 memory는 미측정이다. 원 packet의 timing은 보존한다.

`Run-HCR-R051.cmd --validate-only`는 별도 `HCR-Evidence/r051-validation` 아래
소스/조건 동결, unit tests, 2개 기준선·8개 arm native smoke와 독립 audit,
최종 core regression 1회, evidence ZIP을 수행한다. 연구 결과로 합산하지 않는다.

`Run-HCR-R051.cmd`는 같은 검증 후 4개 기준선·16개 arm 본실험을 1회 실행하고,
독립 상태 재생·raw/hash/개입 검산, CSV·Markdown 집계, evidence ZIP을 만든다.
원자료와 source는 새 고유 run 경로에 배타적으로 기록하며 실패 자료를 덮어쓰거나 자동 retry하지 않는다.
독립 auditor는 producer나 그 개입 함수를 import하지 않는다. 기존 R050 검산만 재사용한다.
기본 dispatcher와 EXP-30은 유지한다. 소스 검증 성공은 연구 가설 성공으로 보고하지 않는다.
