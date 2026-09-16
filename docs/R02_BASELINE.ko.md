# HCR R0.2 기준선 정리 결과

작성일: 2026-09-16 KST  
대상: HCR 0.2.0 Adaptive Graph/Circuit Engine  
구분: **사용자 실행 수용 + 실제 배포 소스 검토 + 후속 평가 명세**

## 1. 현재 결론

R0.2는 사용자 환경에서 실행·회귀·통합 검산이 끝난 기준선이다. 이번 단계는 그 사실을 고정하고 성능·학습 효과의 해석 경계를 정리한다. 엔진의 동작, 파라미터, 학습 규칙, 기존 테스트를 바꾸지 않는다. R0.2.1의 상태 지속·resume은 아직 구현하지 않았다.

로드맵 §6의 문서·평가 명세 정리를 완료했다. 원본 `runs/r02_first`는 이 작성 환경에 없으므로, 원시 증거 동결과 미계측 비용을 이번에 실행한 것으로 보고하지 않는다. 이를 사용자 환경에서 수행할 읽기 전용 수집기와 별도 paired probe를 함께 제공한다. [S1, S2]

## 2. 수용한 기존 실행 결과

| 항목 | 사용자 로그의 결과 | 판정 범위 |
|---|---|---|
| 적용 | `state=applied`; 기준 38개 검사; 38개 파일 기록 | 안전 적용 성공 |
| selftest | 136/136 통과; failures/errors/skipped=0 | R0.1 regression + R0.2 adaptive |
| 환경 | Windows 11; Python 3.12.10 | 사용자가 실행한 환경 |
| demo | `complete=true`; engine=r02 | 통합 protocol 완료 |
| audit | `verified=true`; `differences=[]`; `source_checked=true` | 사용자 측 독립 검산 통과 |
| audit 크기 | 판단 36; event 2646; scalar tick 2006; graph step 84; binding scan 355; memory update 25; checkpoint 4 | 감사 로그에 보고된 처리량 |

이 숫자는 이번 작성 세션에서 다시 실행한 결과가 아니다. 원문 위치는 [S2]의 286–294행이며, 기계 판독용 추출은 `evidence/implementation/r02_execution_acceptance_20260916.json`이다. 별도 수동 `r01_after_r02` 실행 로그는 첨부되지 않았지만 R0.1 CLI/demo/audit 관련 회귀 테스트의 통과가 로그에 있다. 둘을 같은 실행 이력으로 세지 않는다.

## 3. 관찰 결과를 고정한다

### 3.1 익숙한 입력

`familiarity/cold`: 3회 모두 정답, 회로 사용 판단 0회. `familiarity/warm`: 같은 쌍의 3회 모두 정답, 회로 사용 판단 3회다. 이는 **회로 사용 여부가 바뀌었고, 그 3개 개발 사례에서 정확도가 유지됐다**는 결과다. [S2:292]

콘솔에는 원시 비용표가 없다. 따라서 총 연산량 감소율·지연 감소율은 아직 채우지 않는다. 현재 소스는 부분회로 macro 뒤에도 판단용 primitive signal graph를 만든다. dependency 확장 감소와 signal/matching/proof 비용을 분리해야 한다. [C6, C8]

### 3.2 오수렴과 그 episode의 수정

`misconvergence/full`은 최초 `correct=false`, `wrong_stable=true`에서 두 번째 시도의 `correct=true`, `wrong_stable=false`로 바뀌었다. `no_reexpansion`은 1회 시도에서 오답을 유지했다. [S2:292]

다만 full의 재판단에는 **외부 오류 feedback, memory 약화, 새 측정, revision 경로에서 회로 재사용을 끈 primitive 계산**이 함께 들어간다. 이 결과를 “graph 확장만의 단독 효과”로 해석하지 않는다. 무엇이 실제 기여했는지는 EXP-09에서 분리한다. [C1, C2]

### 3.3 다음 episode의 재오답

`retention/reload`는 새 episode에서 `correct=false`, `wrong_stable=true`로 기록됐다. **memory를 저장·복원할 수 있다는 구현 성과와, 수정 효과가 새 약한 입력의 오답을 막았다는 성과는 다르다.** 전자는 audit가 확인한 범위에 속하고, 후자는 해당 개발 조건에서 달성되지 않았다. [S2:292–294]

이전 대화에서 이를 “의도된 오답이므로 문제없다”고 설명했던 분류는 기준선에 사용하지 않는다. 반대로 재오답만으로 직렬화 결함이라고 단정하지도 않는다. **재오답은 확인된 결과이고, 원인은 분리 실험 대상으로 남긴다.**

### 3.4 학습 강도와 수정비용

training3과 training9는 모두 초기 오답 이후 두 번째 시도에 정답이 됐다. 따라서 attempt 수만으로 수정비용 증가가 관측됐다고 할 수 없다. 원 trace의 tick·확장·관측 요청·feedback 비용과, 같은 입력을 쓰는 training3/6/9 대조를 별도로 남긴다. [S2:292]

## 4. 소스가 설명하는 구조 — 원인 후보와 구분

| 소스에서 직접 확인한 규칙 | 이 규칙으로부터 아직 결론낼 수 없는 것 |
|---|---|
| 오류 feedback은 실제 `decision.circuit_ids`에 포함된 회로만 약화한다 | 재오답 때 선택된 회로가 정확히 무엇인지 |
| 부정 정답(`value=False`)은 positive subgraph 학습 분기에 들어가지 않는다 | 이것이 재오답의 단독 원인인지 |
| R0.2의 balance는 양의 검증 경험 수에서 계산한다 | 충분한 약화가 있어도 항상 오답이 반복되는지 |
| prior는 강도·경험 balance·관측 불확실성에 함께 의존한다 | 강도 한 값만으로 candidate 승자를 판정하는 것 |
| revision 추론은 회로 재사용을 끄고 새 관측으로 계산한다 | 수정 성공을 memory 학습만의 성과로 돌리는 것 |

[C1–C9]는 `r02_baseline_source_review.json`의 실제 경로·행 범위다. 위 규칙을 바꾸어 새 결과를 만들지는 않았다. 먼저 baseline의 회로 선택·prior·학습 patch를 연결한 뒤, 필요한 변경은 후속 버전에서 별도 비교한다.

## 5. 다섯 평가 질문의 현재 상태

| 질문 | 현재 확보한 근거 | 다음 증거 |
|---|---|---|
| save/load가 행동을 보존하는가 | memory checkpoint digest와 사용자 audit 통과 | 같은 live memory의 direct vs save/load 결과·proof·cost |
| 수정이 새 약한 입력에도 남는가 | retention 재오답 1회 | before/after memory × 같은 새 weak 입력 |
| 수정은 새 정보에 의존하는가 | 허가된 측정과 primitive 재판단 후 정답 | memory × weak/measured × circuit on/off |
| 압축은 어디서 생기는가 | cold/warm 정답 유지·재사용 차이 | 기존 run의 항목별 실제 비용과 pool/decision 신호 분해 |
| 경험 강도에 따라 수정비용이 바뀌는가 | 3/9 모두 2 attempts | 기존 상세비용 + 같은 conflict의 3/6/9 checkpoint 대조 |

첫 세 질문의 결과를 서로 대신 사용하지 않는다. 특히 save/load의 두 결과가 모두 오답이어도 행동 동등성은 성립할 수 있다.

## 6. 비용 기준

`signal_events=signal_transmissions`, `convergence_ticks=kernel_ticks`, `proof_reconstruction_cost=proof_nodes_reconstructed`, `storage_cost=storage_bytes`는 별칭이다. 수집기는 일치 여부를 확인하고 한쪽만 집계한다. `binding_checks`와 `binding_operations` 역시 세부 의미 없이 서로 더해 새 점수를 만들지 않는다. [C8, model.py:174–188,302–326]

비용 벡터는 dependency·matching·pool·decision signal·proof·외부 검증·learning·storage·시간으로 분리한다. pool/decision 신호 분해는 전체 신호 카운터의 내역이며 추가 비용이 아니다.

기존 `decision.cost.wall_seconds`는 `infer()` 내부 구간이다. engine constructor, 이전 memory load, 전체 experiment 시간, 입력 획득 비용이 모두 들어 있는 end-to-end latency가 아니다. 원래 계측되지 않은 항목은 0이 아니라 `unmeasured`다. 새 probe는 복사·engine 생성·save/load·외부 평가의 wall time을 별도 계측하지만, 그것을 과거 run의 측정값으로 소급하지 않는다. [C7]

## 7. 이번에 보존·변경한 것

기준 배포 snapshot의 release 등록 **114개 파일을 전부 hash 대조**했다. 핵심 실행 범위는 `src/hcr/*.py` 27개와 진입점·설정 3개다. 신규 package에서도 이 30개 실행 파일, 기존 tests/ 전체, 배포 당시 정적 기록은 그대로 유지한다.

현재 상태 안내용 `ROADMAP.md`와 배포 manifest만 갱신하고, 기준선 문서·실행 수용 기록·보조 도구를 추가한다. engine 버전은 **0.2.0**이다. `docs/R02_ACCEPTANCE.ko.md`와 `r02_status.json`의 배포 당시 상태를 역사적 기록으로 남긴다. 변경 전 roadmap/release manifest도 별도로 보존한다.

GitHub HEAD는 이 단계에서 조회하지 않았다. source와 run의 정확한 연결은 로컬 `plan.json.source_hashes`와 수집된 원본 bytes로 확인하며, 저장소 커밋 SHA를 추정하지 않는다.

## 8. 완료·보류 판정

**완료:** 기존 실행 수용 기록, 기준선 해석, 소스 상태 대조, EXP-09 명세, 기록 보존·짝지음 도구 작성, 정적 검사.

**사용자 실행이 남은 것:** 원본 run 동결·비용 추출, 새 EXP-09 비교 실행, 새 보조 도구의 실제 테스트. 기존 136개 통과 사실은 보존하되 신규 도구가 그 136개에 포함되어 통과했다고 표현하지 않는다.

현재 엔진에 대해 새로운 성능 개선을 달성했다고 주장하지 않는다. 이 단계의 성과는 이후 비교의 출발점과 증거 수준을 고정한 것이다.

## 근거

- [S1] `HCR_통합_개발연구_로드맵_R02이후_2026-09-16.md`, §6·§17. 보존본: `docs/reference/R02_PLUS_ROADMAP_20260916.ko.md`.
- [S2] `붙여넣은 텍스트 (1)(20260916-130428).txt`, 56–145, 286–294행. 원문 SHA-256: `48e1cb3b443d810dc9577873fa6fc8421815ca66bf42cd4377172443872603cd`.
- [C1–C9] `evidence/implementation/r02_baseline_source_review.json`. 행 번호는 변경하지 않은 R0.2 배포 snapshot 기준.
- R0.2 업데이트 ZIP SHA-256: `1ef93af88705bb16c134eafb6ee6e98673d59065d9d9b8d6259c8c61c916fc66`.
