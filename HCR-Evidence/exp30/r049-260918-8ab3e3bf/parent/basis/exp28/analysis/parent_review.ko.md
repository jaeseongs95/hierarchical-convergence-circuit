# EXP-27 독립 재검산 및 보고 보완

이 문서는 원래 EXP-27의 raw/summary/가설 기준을 수정하지 않는 별도 addendum입니다.
원자료 88개와 선언된 source 51개를 원래 해시로 확인했습니다.
A 2개 / B 24개 및 이벤트 1086개를 원래 독립 evaluator로 재생했습니다.

## 원래 H_ID 전체 판정

| 상황 | 처리 | 원래 판정 | 연산 수 동일 |
|---|---|---|---|
| extend | cold | supported | True |
| extend | state_carry | supported | True |
| extend | proof_memo | supported | True |
| extend | relation_carry | supported | True |
| different_subject | cold | supported | True |
| different_subject | state_carry | supported | True |
| different_subject | proof_memo | supported | True |
| different_subject | relation_carry | supported | True |
| premise_changed | cold | supported | True |
| premise_changed | state_carry | falsified | False |
| premise_changed | proof_memo | falsified | False |
| premise_changed | relation_carry | falsified | False |

원래 H_ID는 전체 연산 수를 포함했습니다. premise_changed의 세 carry 처리에서 실패한 판정을 유지합니다.
ID순 assumed_edges → 같은 순서의 dependency validation → 첫 불일치 즉시 종료로 검사 수가 달라집니다. 이는 native ticks 변화와 별개입니다.
새 EXP-28의 H_ID_native는 사전에 더 좁게 고정한 별도 질문이며, 원래 H_ID를 성공으로 바꾸지 않습니다.
누락된 로그의 재생성, raw 변경, 기존 manifest 축소는 수행하지 않았습니다.
