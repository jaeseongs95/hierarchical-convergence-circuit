# 실행 전 결과별 판단

| 관측 | 얻는 정보 | 다음 판단 |
|---|---|---|
| joint 중간/최종/eligibility·16서명·불변성 모두 정확, marginal native개입이 closure에 정확하며 same-marginal query 정보손실 관측 | 이번2×2문법에서 joint tuple 보존이 주변곱보다 강하다 | 이 유한 인터페이스만 채택. 더 큰/부분 domain 또는 관계 조합은 별도 계약 |
| 역할 일치 또는 pair/OR부터 오류 | tuple 필드/합성/native수렴 경계 | 첫 실패 source·drive·trace 보존, 원인 판별을 다음 과제로 |
| membership은 정확하지만 joint승격/T/불변성 오류 | joint packet·분류·독립T소비 경계 | 해당 경로 채택 보류, 실패를 보존 |
| marginal 개입이 closure oracle와 다름 | 정보손실 대조군 구현 또는 native projection 오류 | full oracle 손실을 순수 상관관계 소실의 증거로 채택하지 않음 |
| exact와 별도 set oracle 불일치 | baseline 결함 | 해당 비교 판정 보류 |
| source/SHA/trace/protocol/resource 실패 | 엔지니어링·증거 부족 | 이론 음성으로 세지 않음. 동일입력 맹목재실행·사후상한확대 없음 |

최종 정답이 맞아도 중간값·eligibility가 틀리면 joint 보존 채택을 보류한다. marginal의 full-oracle 실패는 의도한 개입의 결과이지 자동으로 harness 실패가 아니다. 새 실행은 관측한 원인과 새 정보를 얻는 별도 계약으로만 수행한다.
