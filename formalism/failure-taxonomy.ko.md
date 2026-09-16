# 오류·보류 분류 — 관측 상태와 원인을 분리한다

## 적용 범위

S06 §33의 7개 작업 개념을 보존한다. 아래 표는 엔진의 새 예외 클래스를 대량 추가하는 것이 아니라 **진단 계약**이다. 기존 `Status` enum과 run schema를 변경하지 않는다. 개념의 source ID는 `evidence/concept_coverage.json`을 따른다.

| 원문 개념 | 지금 확인 가능한 현상 | 원인으로 확정하려면 필요한 근거 |
|---|---|---|
| Activation Failure | no_candidate, 후보·활성 목록 | 필요한 후보가 허용된 후보 문법에 있고 생성/활성 단계에서 사라졌다는 추적. 유효 경로가 없는 입력은 이 실패가 아님 |
| Binding Failure | 계약 거부, 현재 node/role/revision | 어느 참조에서 어떤 의미·identity·revision 불일치가 났는지 직접 기록 |
| Competition Failure | 후보가 경쟁한 기록·선택 결과 | 올바른 후보가 실제 가용했고 선택 단계가 원인이었는지의 대조. 오답만으로 단정 금지 |
| Misconvergence | stable_decision이며 external correct=false | 안정된 오답이라는 관측 분류. 왜 오수렴했는지는 별도 |
| Non-convergence | oscillating 또는 아직 미안정 상태 | 진동의 관측과 유한 예산 만료를 분리. budget_exhausted만으로 영원히 수렴하지 않는다고 판정 금지 |
| Over-compression | 회로 사용 + 예외 누락 의심 | 같은 정보/예산에서 압축 해제·강도 통제로 오류가 사라지는지; 단순 회로 사용+오답은 불충분 |
| Graph Expansion Failure | 미해결, 확장 중단, 요청 불가 | 확장이 금지된 대조군·예산 부족·관측 없음과 알고리즘상의 전환 실패를 분리 |

`stable_ambiguous`, `unsupported`, `budget_boundary`, `no_candidate_observed`는 정상적인 보류/제약 결과일 수 있다. 원인 후보와 버그 판정을 자동으로 연결하지 않는다.

## 단계별 기록

각 attempt의 `decision_id`, observation revision, memory version, 최초 관측 label, 사건 seq, 근거 위치를 남긴다. 수정된 attempt는 별도 행이다. 실패의 최초 발생과 후속 전파를 구별한다. 근거가 부족하면 cause는 `not_identified`다. 진단 label은 중첩 가능하므로 총합을 고유 실패 수로 세지 않는다.

## 이번 도구

`tools/r02_concepts/review.py`는 기존 capture의 Status·외부 assessment·proof 포함 관계만 읽는다. causal_failure를 새로 추정하지 않고 `causes_not_diagnosed`에 남긴다. assertion 실패/파손된 capture는 분석 실패로 종료하며 행동 실패 통계로 합치지 않는다. 엔진 입력으로 오류 정답 label을 되돌려 보내지 않는다.

## 완료 gate

R0.2.1 이후 stage별 원인 증거가 추가될 때 본 분류와 evaluator·trace schema를 함께 확장한다. 단위시험의 위변조 거부와 연구 과제의 오수렴을 같은 성공/실패 카운터에 합치지 않는다.
