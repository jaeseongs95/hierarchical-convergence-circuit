# R0.2 개념 대응 / 실행 기록 관찰

이 보고서는 기존 capture의 재분석이며 새 추론 표본·원인 규명·독립 수치 검산이 아니다.

| 조건 | 판단 | 시도 | 수렴 상태 | 정답 | 관측 label | proof D |
|---|---|---:|---|---|---|---:|
| training/full | r02-d-1-7f4b31acd000d549 | 1 | stable_decision | True |  | 3 |
| training/full | r02-d-56-2a3332621f47bbb8 | 1 | stable_decision | True |  | 3 |
| training/full | r02-d-111-77b61a2c6e44aea5 | 1 | stable_decision | True |  | 3 |
| training/full | r02-d-166-85f9413b91cb3706 | 1 | stable_decision | True |  | 3 |
| training/full | r02-d-254-64e75141600a2dd3 | 1 | stable_decision | True |  | 3 |
| training/full | r02-d-341-64f04cf25ef1fbde | 1 | stable_decision | True |  | 3 |
| familiarity/cold | r02-d-430-b9150af78bbb52fc | 1 | stable_decision | True |  | 3 |
| familiarity/warm | r02-d-484-b9150af78bbb52fc | 1 | stable_decision | True |  | 3 |
| familiarity/cold | r02-d-570-07e8d7bf0af89723 | 1 | stable_decision | True |  | 2 |
| familiarity/warm | r02-d-616-07e8d7bf0af89723 | 1 | stable_decision | True |  | 2 |
| familiarity/cold | r02-d-732-ec838764dfe81ab3 | 1 | stable_decision | True |  | 3 |
| familiarity/warm | r02-d-786-ec838764dfe81ab3 | 1 | stable_decision | True |  | 3 |
| novelty/graph_only | r02-d-872-28dbe8221f4b2730 | 1 | stable_decision | True |  | 4 |
| novelty/full | r02-d-928-28dbe8221f4b2730 | 1 | stable_decision | True |  | 4 |
| novelty/graph_only | r02-d-1053-2b49811915fa301a | 1 | stable_decision | True |  | 2 |
| novelty/full | r02-d-1098-2b49811915fa301a | 1 | stable_decision | True |  | 2 |
| misconvergence/full | r02-d-1174-d77a981fac668ae7 | 1 | stable_decision | False | misconvergence, assumption_reality_mismatch | 3 |
| misconvergence/full | r02-d-1265-c0e3e4890f19bbef | 2 | stable_decision | True |  | 2 |
| misconvergence/no_reexpansion | r02-d-1311-d77a981fac668ae7 | 1 | stable_decision | False | misconvergence, assumption_reality_mismatch | 3 |
| retention/reload | r02-d-1401-a2b67d430736225d | 1 | stable_decision | False | misconvergence, assumption_reality_mismatch | 3 |
| tradeoff_training/training_3 | r02-d-1506-fcd98f136790d9ad | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_3 | r02-d-1561-c2c086299d45fa72 | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_3 | r02-d-1616-0fffab8fd76dcb19 | 1 | stable_decision | True |  | 3 |
| tradeoff/training_3 | r02-d-1672-046b1a5012c9b675 | 1 | stable_decision | False | misconvergence, assumption_reality_mismatch | 3 |
| tradeoff/training_3 | r02-d-1780-2f487e9d3e1ea8f6 | 2 | stable_decision | True |  | 2 |
| tradeoff_training/training_9 | r02-d-1825-1b6aed4b7a199d7e | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-1880-032a1fcbeee74a5d | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-1935-46dd6f4942e0ad7a | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-1990-63ba80c48641d91b | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-2078-5414b0460bf86b24 | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-2165-c6e55fc1cd73c967 | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-2252-92d2768a9af6359c | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-2339-3ccd7175f367b762 | 1 | stable_decision | True |  | 3 |
| tradeoff_training/training_9 | r02-d-2426-82062b7ce62b4b2a | 1 | stable_decision | True |  | 3 |
| tradeoff/training_9 | r02-d-2514-357571e2d41761d8 | 1 | stable_decision | False | misconvergence, assumption_reality_mismatch | 3 |
| tradeoff/training_9 | r02-d-2602-39b6cedb832f2f4a | 2 | stable_decision | True |  | 2 |

## 설명 비교의 범위

review.json에서 assumption_ids_outside_public_observation, assumption_ids_outside_last_program_paths, proof_paths_outside_last_program을 확인한다. 공집합은 포함 관계에 이상이 없다는 뜻이며 설명이 실제 원인 경로와 동일하다는 증명이 아니다.

- 정당화 포함 관계와 기록 상태를 읽는다. 독립 numerical audit를 대체하지 않는다.
- R0.2에는 독립 readout/explanation 이벤트·개별 시간값이 없다. 과거 기록에 추가하지 않는다.
- no_candidate는 activation failure, 오답은 over-compression의 확정 근거가 아니다.
- 현상 분류는 중첩 가능하므로 label 합계는 고유 실패 수가 아니다.
