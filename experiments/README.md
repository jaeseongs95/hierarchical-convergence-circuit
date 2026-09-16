# 실험·개발 검증·분석의 상태

| 구획 | 현재 상태 | 해석 |
|---|---|---|
| EXP-00 / EXP-08 | 개발 fixture 구현; 사용자 R0.1/R0.2 실행 보고 | 전체 연구가설 검증과 구별 |
| EXP-01~07 | 원래부터 있던 연구 draft; 이번에 EXP-03/04/05/06을 구체화 | 새로 발명한 실험 ID가 아님; 미실행 상태 유지 |
| EXP-09 | `docs/R02_BASELINE_PROTOCOL.ko.md`의 비교 명세 및 probe 도구 | capture 완료와 새 paired 실험 완료는 다름 |
| 개념/trace 검토 | `tools/r02_concepts` | 정적 연결 검사·기존 capture 관찰; 새 inference 없음 |
| B0/B1/B2 | substrate 계약/후속 backend gate | 물리 구현·효율 우월성을 주장하지 않음 |

공통 구현은 `src/hcr`에 두고 실험별 엔진 복제는 하지 않는다. 동일 primitive의 A-level 반복, Decision/Explanation, 오류 taxonomy는 마지막 버전까지 미룰 항목이 아니라 관련 단계의 횡단 검증이다. 실제 원시 run은 변경하지 않는다.

명세와 claim의 상태는 별개다. `evidence/claims.yaml`은 원문 기록을 유지하고, 현재 구현 대응은 `evidence/concept_coverage.json`에 분리한다.
