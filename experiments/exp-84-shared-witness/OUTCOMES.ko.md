# 실행 전 결과별 판단

| 관측 | 얻는 정보 | 다음 판단 |
|---|---|---|
| 공유증인 모든 층/eligibility/분류/96변형 정확, 독립증인이 완화oracle에 정확하나 fulloracle에 거짓 허용 | 같은 변수의 증인 결속이 이 유한 triangle 문법에 필요 | 이 유한 결합 연산의 적합성만 인정; 다음은 투영으로 잃은 Z 상태/후속 질의 경계 |
| role/pair/membership부터 오류 | 원천 역할·표 membership/native 경계 | 첫 실패 trace/drive 보존 후 원인 판별 과제 |
| membership 정확, shared composition 또는 classifier 오류 | 증인 인덱스·연속수치 합성/승격 경계 | 해당 결합 연산 채택 보류; 해당 중간층 반례를 다음 과제로 |
| 독립증인이 완화oracle와 다름 | 개입 구현 또는 native 오류 | full정보 손실의 순수 증거로 채택하지 않음 |
| exact와 별도 triple oracle 불일치 | 기준 구현 결함 | 비교 판정 보류 |
| SHA/출처/trace/resource 실패 | 엔지니어링·증거 부족 | 이론 음성으로 세지 않고 동일입력 재실행·사후상한 확대 없음 |

최종 consistent만 맞아도 eligibility/중간층이 틀리면 공유증인 보존으로 채택하지 않는다. 상한 초과 시 완료된 기록과 inflight 불명확 호출을 구분해 보존한다.
