# EXP-33 / R052 — 배열 순서와 구조 역할 분리

계약: `r052-array-role-controls-v1`. 기준 checkout: `b1d4525039f94c22f8aa2233aa6d6db616d9282c`.

## 결정과 근거

R051은 같은 edge 위치에서도 TD OFF/ON 채택 차이가 남고, 위치별 수치·비용 차이가
존재함을 확인했다. 그러나 edge 배열 index와 start/goal 방향의 구조 역할은 분리하지 않았다.
후속 선택지는 배열/binding 대조와 선택적 feedback-link 분리다. 전자는 기존 core와 native
검산을 유지하며 representation 교란을 확인할 수 있고, 후자는 기제에 직접적이지만
새 kernel/config와 독립 replay 계약을 요구한다. 이번에는 전자를 먼저 수행한다.
이는 R051 결과 토론의 Coordinator 선택을 구현한 것이며, 그 토론의 우선순위 이견을 지우지 않는다.

## 동결 조건과 예측

길이 2, 관계 ++, 초기 score 0.02, 고정 ID a-edge(v0→v1), z-edge(v1→v2), 빈 memory,
기본 AdaptiveConfig, legacy prior, frozen_eval, use_circuits/allow_reexpansion=True를 유지한다.
path 배열과 swapped 배열 × TD OFF/ON의 4기준선이며 identity는 하나로 고정한다.

| arm | revision | score 조작 | 추가 session |
|---|---:|---|---:|
| hold | 0 | 없음 | 0 |
| revision_only | 1 | 없음 | 1 |
| start_edge | 1 | source=start인 edge만 1.0 | 1 |
| goal_edge | 1 | target=goal인 edge만 1.0 | 1 |

총 16 paired record, 고유 기준선 4회, 추가 session 12회다. 각 session은 최대 8 advance,
1,280 kernel ticks이며 사전 예약 검사를 유지한다. 결과에 따른 arm 선택·retry는 없다.
모든 조건의 episode ID는 provenance 구분용으로 다르며, 그 차이를 수치 상태 차이로 취급하지 않는다.

- P1: hold와 revision_only의 수치 상태·궤적은 같다.
- P2: 같은 TD·구조 역할 개입에서 배열을 바꿔도 역할 대응 후 상태·궤적·proof/support·채택이 같다.
- P3: 구조 역할을 맞춘 TD 및 start/goal 강화 대비를 각각 보고한다.

P2 위반은 유효한 연구 결과일 수 있으며 audit 실패와 다르다. 대응이 불가능하거나
candidate가 없는 조건은 비교 불가/실패 유형을 남기며, 성공으로 보간하지 않는다.

## 비교의 계약

실행기는 입력 배열을 그대로 native에 전달하고 ID·path·proof·상태를 수정하지 않는다.
비교기는 먼저 각각의 packet을 독립적으로 replay한 뒤 평가용 투영에서만 array slot과
edge 역할을 대응한다. e:0/e:1이 바뀌었다는 이유만으로 실제 동역학 차이라고 판단하지 않는다.
반대로 goal/prefix 값이나 tick 수, residual, proof 가정 차이를 지워서 같게 만들지 않는다.
program과 path/binding의 역할 대응을 검증하고 원자료의 raw index 비교와 구분한다.
수치 허용오차는 abs_tol=rel_tol=1e-12다. 원자료와 비교 투영은 서로 대체하지 않는다.

현재 chain의 각 frontier에는 outgoing 하나뿐이고 kernel은 동기 갱신이다.
따라서 배열 대조는 scheduling 경쟁 조작이 아니라 index/binding 불변성 검사다.
같으면 이 입력에서 array-index 의존 설명이 약화되고, 다르면 먼저 표현·binding 구현을 진단한다.
어느 결과도 특정 feedback link나 일반적 계층 수렴 원인을 확정하지 않는다.

## 보존·검증·종료

core/src, core/tests, R048/R049/R050/R051 소스·manifest, 과거 evidence를 변경하지 않는다.
기존 R050 native session adapter와 독립 NativeVerifier를 재사용하고 R052를 별도 추가한다.
native session ID의 r050- prefix는 어댑터 재사용 흔적이며, r052-cNNN case와 R052 schema로 구분한다.
기본 dispatcher는 EXP-30 그대로다. 새 의존성 설치·네트워크 데이터·학습·측정·state continuation은 없다.

`Run-HCR-R052.cmd`: preflight/source·plan 동결 → R052 selftest → 별도 native smoke 및 독립 audit
→ 최종 core regression 1회 → 본 연구 1회 → 독립 audit → 집계/ZIP.
smoke는 c000/c002(TD OFF의 두 배열), 2기준선·8기록이며 연구 집계에 합산하지 않는다.
`--validate-only`는 연구를 실행하지 않고 별도 r052-validation 경로에 구현 검증을 남긴다.

개발 단계에는 계약을 유지하는 구현 결함 수정과 관련 검증을 허용한다. 최초 실패를 보존하고
원인이 확인된 뒤 수동으로 새 고유 run을 만든다. 자동 retry는 없다. 본 연구 시작 후에는
예측·조건·판정 기준을 변경하지 않으며, 조건 추가나 기준 완화가 필요하면 이 페이즈를 중단한다.
수용 기준은 정확한 조작·원자료 보존·독립 검산·필수 회귀 통과다. 예측의 일치가 완료 조건은 아니다.
완료 시 결과와 후속 질문을 기록하고 로컬 main에 커밋·병합한다. 원격 push는 이번 요청에 포함하지 않는다.

## 주장과 비용 경계

raw decision, 가정하 proof validity, 관측 support, terminal adoption을 각각 보고한다.
정답은 synthetic ++ reference=True이며 관측 support 자체가 외부 진실을 측정하지 않는다.
16분기는 독립 표본이 아니고 같은 입력 재실행은 독립 반복이 아니다.
ticks, signal transmissions, proof reconstruction, restart 수를 단위별로 집계한다.
실제 에너지·프로세스 memory는 미측정이다. Graph→Circuit 형성·재사용이나 인간 인지로 일반화하지 않는다.

## 오케스트레이션 기록

development-orchestration과 ponytail을 적용했다. 실행기/파이프라인/동결 조건은 메인이,
독립 입력 재구성·역할 대응 평가기와 tamper test는 r052_auditor가 소유한다.
공유 인터페이스를 먼저 고정했으며 평가기는 producer를 import하지 않는다.
위임은 구현 분리와 동시 진행을 위한 것으로, 구현자가 자기 평가기의 최종 독립 감사자라는 뜻은 아니다.
요청 구성은 gpt-5.6-sol/high, fork_turns=none이며 관찰된 생성 응답은 task_name뿐이다.
따라서 실제 모델·추론 적용은 unverified로 기록한다. 재위임과 worker의 전체 연구 실행은 금지했다.
별도 r052_contract_review는 gpt-5.6-terra/high, fork_turns=none으로 읽기 전용 계약·통합 검토를
맡는다. 이 호출 역시 task_name만 반환되어 actual은 unverified다. 전체 결과 토론 패널을
반복하는 대신 기존 토론 근거를 재사용하고 새 구현의 위험에 검토를 한정한다.
