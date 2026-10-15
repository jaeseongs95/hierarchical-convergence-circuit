# 같은 graph의 6셀 종료정책 비교 — 2026-10-15

고정 비교기로 계획한 여섯 셀을 각각 한 번 시도했다. 아래 결과는 하나의 알려진 graph와 모든 edge가 열린 새 합성 world에 대한 **진단 후보** 평가다. 실제 Engine 채택·전체 문제 정확도·일반화 성능은 측정하지 않았다.

1,800초 구간의 결과는 C 정답, F 정답, L 오답이다. C는 5,168 tick, F는 6,144 tick에서 끝났지만, C의 wall은 F보다 4.6% 길었다. 180초에서는 2/3셀이 집계 가능한 후보를 남겼고 정답은 0/2였다.

## 결론과 관찰

| 정책 예산 | 정책 | 실행 상태 | 마지막 완료 tick | 종료 이유 | 진단 후보 | 후보 정오 | 고정점 거리 | 정책 wall(s) | 트리 CPU(s) | peak committed(MiB) |
|---|---|---|---:|---|---|---|---|---:|---:|---:|
| 180s | L | MEASUREMENT_FAILURE | 386 | MEASUREMENT_FAILURE | False | 오답 / 집계 제외 | OUTSIDE | 84.703 | 77.891 | 18.76 |
| 180s | F | BUDGET_INCOMPLETE | 847 | BUDGET_INCOMPLETE | False | 오답 | OUTSIDE | 180.000 | 166.500 | 18.79 |
| 180s | C | BUDGET_INCOMPLETE | 676 | BUDGET_INCOMPLETE | False | 오답 | OUTSIDE | 180.000 | 162.703 | 18.53 |
| 1800s | C | COMPLETE | 5168 | CERTIFIED | True | 정답 | INSIDE | 1311.329 | 1222.312 | 18.35 |
| 1800s | F | COMPLETE | 6144 | TICK_CAP | True | 정답 | INSIDE | 1253.453 | 1168.703 | 18.13 |
| 1800s | L | COMPLETE | 1856 | stable_decision | False | 오답 | OUTSIDE | 377.735 | 355.203 | 18.54 |

L은 매 tick의 잔차·patience를 갱신하고 16 tick마다 판단하는 실수 모델 heuristic이다. F는 자원 또는 tick 6144 상한에서 종료한다. C는 현재 구간의 잔차·수축률 인증을 16 tick마다 시도한다. L을 실제 native cap160이나 과거 매 tick 종료1848과 동일시하지 않는다.

| 집계 | 계획 분모 | 집계 가능 | 응답 | 정답 | 조건부 정확도 | 후보 커버리지 | 정답/계획 |
|---|---:|---:|---:|---:|---|---|---|
| 전체 | 6 | 5 | 5 | 2 | 2/5 | 5/6 | 2/6 |
| 180s | 3 | 2 | 2 | 0 | 0/2 | 2/3 | 0/3 |
| 1800s | 3 | 3 | 3 | 2 | 2/3 | 3/3 | 2/3 |

정확도는 응답한 집계 가능 후보 중 정답 비율이다. 커버리지는 집계 가능 응답/계획 셀 수다. 평가가 끝난 BUDGET_INCOMPLETE는 포함하고, MEASUREMENT_FAILURE·CLEANUP_NOT_CONFIRMED·NOT_RUN·INCONCLUSIVE는 제외한다. 제외 셀도 전체6·예산별3 분모에 남긴다. 예산별 표는 세 정책을 섞은 기술통계이며 독립 표본의 성공률이 아니다.

## 예측과 대안 설명

| 동결 예측 | 실제 판정 |
|---|---|
| P1: 작은 변화+patience가 원래 초기값의 목표 고정점 근접을 보장 | 해당 graph에서 반례 관측: 1800/L heuristic 종료가 검증된 목표 anchor에 대해 OUTSIDE. 모든 고정점과의 거리를 새로 증명한 것은 아니며, 알려진 입력의 재현이다. |
| P2: C 인증의 근접 타당성 | CERTIFIED 1셀, 거리 INSIDE 1셀. 별도 evaluator의 공유 수치 helper 재검산을 함께 확인. 일반 타당성 증명으로 확대하지 않음. |
| P3 180s C 대 L | 비교 불완전: 집계 제외/결측 포함 |
| P4 180s C 대 L | 판정불가 |
| P3 180s C 대 F | 후보 정오 차이 없음 |
| P4 180s C 대 F | 정답 품질과 더 낮은 wall을 함께 뒷받침하지 못함; C 180.000s / F 180.000s |
| P3 1800s C 대 L | 이 예산에서 C 정답, 상대는 오답/보류 |
| P4 1800s C 대 L | 정답 품질과 더 낮은 wall을 함께 뒷받침하지 못함; C 1311.329s / L 377.735s |
| P3 1800s C 대 F | 후보 정오 차이 없음 |
| P4 1800s C 대 F | 정답 품질과 더 낮은 wall을 함께 뒷받침하지 못함; C 1311.329s / F 1253.453s |

C의 생성 tick 수가 적어도 검사 비용·파일 봉인·자식 획득이 정책 wall 예산에 포함된다. wall 차이의 원인을 수치 연산과 파일 I/O로 분해하는 별도 프로파일은 수행하지 않았다. 실행 순서가 고정돼 있어 호스트 부하·열 상태가 비용 차이와 얽힐 수 있다. 이를 정책의 보편적 우열로 해석하지 않는다.

## 검증

정책 간 공통 tick의 full7 구간 8,938건이 정확히 일치했다. 고유 tick은 초기값0부터6144까지 6,145개다. 저장 구간의 진단 후보·목표 anchor 거리·L의 매 tick 잔차/카운터/종료 상태·world BFS·봉인 해시·고정 분모를 별도 Fraction 구현으로 확인했다. 비선형 궤적 자체를 다시 실행한 검사는 아니다.

사후 두 검토자는 수치·집계·예산·해석이 원자료와 맞는다고 확인했고, 인증 미요청을 미인증으로 표시한 원장 오류1건을 지적했다. 이전 파생 산출물을 보존한 뒤 L/F는 NOT_REQUESTED, 중단된 C는 NO_FINAL_CERTIFICATE로 정정했으며 다른 모든 원장 값이 동일함을 검산했다. 검토자는 기존 reviewer의 후속 재사용이며 새 독립 Judge가 아니다.

## 예산과 중단

전체 watchdog 관측 wall은 3391.688s, study 요약 wall은 3391.391s다. 6900초 물리 상한 초과 관측은 False다. 상위 전체 트리 CPU와 셀 CPU는 중복되므로 합산하지 않는다.

정책은 180/1800초, 평가기는 셀당120초, 정리는 셀당10초, setup180초, 전체6900초로 동결했다. 셀별 Windows Job은 committed virtual memory512MiB 제한이며 RSS가 아니다. 상위 Job은 종료만 담당한다. 종료 지연은 숨기지 않으며 hard real-time 보장은 없다. 중단된 수치 카운터는 마지막 봉인 상태까지의 하한이고 미완료 연산은 미측정이다. 별도 단위는 comparison.json에 그대로 보존했다.

## 실패와 개입 기록

실행 전 원본 자체시험은 25개 중24개 통과·1개 시간 전제 실패다. 합성 pending-C가0.8초 안에 tick16에 도달할 것이라는 가정에서 tick4가 관측됐다. 격리 복사본에서 그 합성 단계만5초로 두자 같은 생산 코드·단언으로 pending/종료 검사가 통과했다. 원본 실패를25PASS로 바꾸지 않았고, 실제 실험 예산·정밀도·정책 코드는 바꾸지 않았다. 첫 격리 fixture의 누락 dependency 오류도 보존했다.

180/L은 tick386 뒤 ack 파일의 원자적 이름 변경이 WinError5로 실패했다. 일반 읽기로 대상 파일을 열어 두면 같은 rename 실패가 나는 메커니즘을 격리 검사에서 확인했다. 실행 초반 관측기가 가변 ack를 읽은 점은 개입 가능성이며, 정확한 충돌 핸들은 계측되지 않아 다른 reader/AV는 배제하지 못한다. 이후 관측기는 가변 ack/progress를 열지 않고 파일명·이미 봉인된 결과만 읽도록 바꿨다. share-delete만으로 해결된다는 초기 가정도 검사에서 실패해 보존했다. 해당 셀은 재실행하지 않았다. 이 실패를 L의 과학적 오답으로 세지 않는다.

## 현재 주장 가능한 범위

모든 edge가 열린 합성 world의 정답은 True이며 처리한 첫 path도 True다. 진단 False는 coverage_required이고 실제 채택은 NOT_MEASURED다. proof validity·support gap·D_DAG·실제 controller frontier·에너지·RSS는 미측정이다. 고정점 거리 평가는 신뢰된 과거6144 anchor enclosure와 공유 수치 helper를 사용하며, 새 궤적 전체를 별도 수치 구현으로 다시 계산하지 않았다.

이번 결과는 종료정책과 진단/수렴을 분리하는 구성요소 실험이다. Thought-Graph 전체 정확도, 음성 문제 성능, A/D/M 조작성, Circuit 학습·재사용, native Engine이나 LLM 내부 계산에 대한 직접 증거가 아니다. 측정 실패가 있는180초 L 대비와 고정 순서에 따른 교란을 먼저 고려해야 한다. 다음 원인을 구별할 후보는 관측기와 atomic snapshot의 충돌을 제거한 별도 고정 재현 및 다른 truth/graph에 대한 사전 등록 비교다. 이 보고서에서는 추가 실험을 실행하지 않았다.

## 재현 자료

[동결 실행 계약](execution-contract.json) · [토론 요약](deliberation-summary.json) · [실행 전 검증](pre-execution-verification.json) · [비교 원장](comparison.json) · [raw manifest](raw-manifest.json) · [원자료 묶음](raw.zip)

raw.zip은 원본 stdout/stderr·setup·world·각 단계의 supervision·모든 상태·ack·봉인·평가·자체시험·최초 실패·관측기 개입과 실행 스크립트를 보존한다. manifest의 SHA256·크기와 archive 내부 전체 바이트를 검산했다. 원래 절대 경로를 봉인 기록에서 재작성하지 않았으므로 다른 경로에서의 재현은 별도 새 실행으로 취급해야 한다.

dot의 원답변은 실행 전 최근 총괄 두 turn에서 관측되지 않았다. 최근 turn 조회만으로 전체 이력의 부재를 증명하지 않는다. 관련 없는 ACK를 연구 조언으로 해석하지 않는다. 원답변이 확인되면 출처를 검증한 별도 날짜의 추가 기록으로 반영하며 동결된 실행을 바꾸지 않는다.
