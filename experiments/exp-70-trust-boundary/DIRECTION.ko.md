# r24 방향성 토론 — 정확 전이 재사용 후보의 선별

2026-10-19 KST. 기준 main `2175fb7b67fc3e6bde504fc7597c52e4e4247702`. 연구 실행 전 토론을 마쳤으며 아직 census 결과는 없다.

## 1. Executive Verdict

**실제 계산 절감 경로로 돌아가되, 먼저 기존 저장 전이에서 완전 입력의 정확한 반복이 있는지 확인한다.** 새 추론·학습·센서 측정 없이 AI Research SSH에서 작은 선별 분석을 한다. 독립 판정자의 결론은 `conditional_consensus`다. 구현 최종 감사나 SSH 실행 승인은 아니다.

## 2. Consensus Proposal

프로그램·전체 설정·전체 현재 state·drive·top_down이 같은 저장 tick 전이를 실제 순서로 분석한다. 원래 입력별 프로세스 수명의 `case_local`과 더 긴 수명을 가정한 `arm_stream`을 나눠 집계한다. 비교 arm 사이에는 캐시를 공유하지 않는다. 결과는 관측한 중복과 계산 생략의 가능한 상한이며 실제 속도·총비용 개선으로 해석하지 않는다.

## 3. Strong Consensus

r23은 기존 정답을 보존한 계산 절감 근거를 주지 못했다. tick 차이592→539는 eval_05의 정답→보류에서−56, eval_06에서+3으로 분해되며 나머지8입력은 동률이다. 새 신뢰 장치를 계속 늘리기 전에 큰 목표인 실제 계산 재사용의 가능성을 작게 판별할 필요가 있다. 같은 ON/OFF 또는 같은 식별 불가능성의 반복은 새 연구로 세지 않는다.

## 4. Material Disagreements

초기 권고는 연구 가치·비용 관점이 C, 구현 관점이 A의 제한된 적격 중단, 평가 관점이 B의 안정 결과 추가 측정이었다. C를 저장 전이 선별로 구체화한 뒤 교차반박에서 A/B보다 먼저 할 수 있다는 조건부 판단으로 모였다. A/B가 불가능하다는 합의가 아니다.

| 후보 | 남는 가치 | 이번 우선순위에서의 제약 |
|---|---|---|
| A 최근 오류에 따른 출처 중단·회복 | 오류의 후속 전파 제한 | 오류 증거의 취득·진위·도착 시점·비용 계약이 먼저 필요하다. 합성 oracle 상태기계와 운영 안전성을 구분해야 한다. |
| B 안정된 초기 결과도 추가 측정 | 교정과 기존 정답 손상의 교환 | 같은 공개 입력에서 오답만 골라 요청할 근거가 없다. 수행한다면 모든 stable 결과 점검의 비용·손상을 새 완전교차 조건으로 비교해야 한다. |
| C 정확 전이의 재사용 기회 | 실제 계산 절감 후보를 낮은 비용으로 배제/선별 | hit는 속도 개선이 아니다. 수명·완전 입력 중복·관리 부담을 분리해야 한다. |

## 5. Decision by Axis

연구 가치 축은 C의 음성 결과도 큰 구현을 피하는 선별 가치가 있다고 판단했다. 평가 축은 과거만 조회하고 비교 arm을 분리하며 bit exact와 허용오차 재생을 혼동하지 않는 조건을 요구했다. 구현 축은 tick 수치 출력과 settle 종료·Cost 부작용을 분리했다. 비용 축은 key/hash/조회/복사/저장·남는 제어와 trace 비용을 빠뜨리지 않는 상한 해석만 허용했다. fresh Judge는 네 축 모두 이 조건 아래 C 우선으로 판정했다.

## 6. Evidence

- r23 입력별 품질·비용: `evidence/source-qualification-20261019-r23/raw/summary.json`, `experiments/exp-69-source-qualification/RESULTS.ko.md`.
- 재사용의 expansion 감소와 비용 증가: `experiments/exp-64-pre-reuse-gate/RESULTS.ko.md`.
- 경계 생략형 대체만 기각한 r19와 저장 재생 한계: `experiments/exp-65-substitution-cross-level/RESULTS.ko.md`, `evidence/substitution-cross-level-20261019-r19/replay-receipt.json`.
- tick 의존 입력과 settle 종료 상태: `src/hcr/dynamics.py:7`, `:32`; 저장 필드와 case별 subprocess 순서: `tools/r19_cross_level/probe.py:46`, `:219`.

Coordinator는 위 코드·보고서·원자료 집계와 수신된18case 해시를 직접 확인했다. reviewer 주장을 그 자체로 증거로 세지 않았다. r19 원격 run은 FAILED_AT_AUDIT였으며 수정된 저장 재생과 구별한다. 실행 후 전체 source 재해시도 미완료였다.

## 7. Required Actions

입력과 실제 순서·수량·해시를 먼저 고정한다. current는 저장 initial/직전 tick에서 가져온다. 프로그램 순서와 숫자 타입·부호 있는0·float bit를 보존하며 근사 key를 금지한다. 같은 완전 key의 next-state가 다르면 중단한다. 동일 settle/동일 case 다른 settle/교차 case와 전체 kernel 입력 반복의 기여를 교차 분리한다. 별도 수식 재생의1e-15를 hit 허용오차로 쓰지 않는다. 원 Cost·convergence를 바꾸거나 복사해 생략하지 않는다. 이후 설계는 `design.ko.md`에 고정한다.

## 8. Optional Optimizations

이번에는 없다. 실제 캐시 엔진, 회복 상태기계, threshold 탐색, 반복 timing·native 재실행·새 의존성은 추가하지 않는다.

## 9. Unresolved

실제 hit 수·구성·case_local의 유효 기회·관리 부담은 실행 전 미확인이다. 실제 배포 캐시의 속도 순이득·현실 입력의 반복률·학습 포함 손익분기는 이번 분석에서 관측할 수 없다. 원수명에서 반복 fixture 외 기회가 없거나 모두 가상 cross-process 수명에 의존하면 큰 구현으로 승격하지 않는다. 기회가 남아도 별도의 작은 native 대조가 필요하다.

## 10. Method / Run Summary

`independent-deliberation-panel` HIGH를 적용했다. `fork_turns:none`의 blind reviewer4명(연구 가치·평가 타당성·구현 경계·비용), 주장별 교차반박3건, 새 컨텍스트의 fresh Judge1명이 실제 완료했다. 모든 worker는 재위임·수정·새 실험·외부 메시지를 금지받았다. specialist reserve와 adaptive 재숙고는 사용하지 않았다. configured model은 모두 gpt-6.1-sol/xhigh이며 collaboration에 선호 Terra가 노출되지 않아 지원되는 Sol을 썼다. 관측한 프로토콜 수행 수준은 `independent`이며 provider 내부 격리를 증명하는 표시는 아니다. raw reviewer 출력·대화·내부 추론은 이 문서나 dossier에 저장하지 않았다. 판정자는 V5~V8의 관련 코드/보고서/receipt를 읽었고 V1~V4는 Coordinator의 검증 요약에 의존했다. 실제 토큰 사용량은 관측하지 못했다.
