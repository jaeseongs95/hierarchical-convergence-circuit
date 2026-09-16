# R0.2 수용 기준 — 실행 전

배포 상태: 소스 작성 및 정적 검사. **실제 check/demo/verify 결과 없음.** R0.1의 과거 72개 통과 기록은 R0.2 통과 증거가 아니다.

## 필수 사용자 실행

1. 안전 적용기의 기준/신규 경로 검사가 통과해야 한다. 다른 소스에 강제로 덮어쓰지 않는다.
2. `python -X utf8 -B hcr.py check`의 failures/errors가 모두 0이어야 한다. Windows에서는 기존 및 새 PowerShell parser 시험의 skipped 사유도 확인한다.
3. R0.2 demo가 새 경로에서 `complete=true`를 반환해야 한다. 실패 폴더를 지우고 성공한 것처럼 재사용하지 않는다.
4. R0.2 verify가 `verified=true`, `differences=[]`여야 한다. 판정 및 수치, binding scan, graph step, memory update가 실제 재검산돼야 한다.
5. 기존 R0.1 demo/verify도 새 출력 경로에서 정상 동작해야 한다. 이전 결과를 대신 제시하지 않는다.

## 연구적 수용 기준

| 항목 | 확인할 관측 | 실패 또는 한계 |
|---|---|---|
| Familiarity | 같은 공개 입력의 cold/warm dependency nodes/expansions, 정답/근거/D | graph 축소가 없거나 정확도가 떨어지면 그대로 보고 |
| 부분 구조 재사용 | chain3 학습 후 chain4/분기 구조에서 현재 역할에 바인딩한 motif 사용 | 전체 답 캐시, 실험 label 분기, 미탐색 분기 삭제는 허용 안 함 |
| 경쟁 | 복수 c:i 후보가 같은 tick/settle 및 상호 억제 link로 계산 | 단순 첫 lookup을 경쟁으로 부르지 않음 |
| 오수렴 | 약한 충돌 입력의 실제 initial wrong_stable 및 correction attempts | 발생하지 않으면 그 설정에서 관측되지 않았다고 보고 |
| 재확장 | 오류 feedback → strength 변화 → 허용된 측정 → 새 revision의 primitive 재계산 | 최초 실패 덮어쓰기, feedback bit를 답으로 복사하면 실패 |
| 지속성 | save/load hash 일치, 다음 episode에서 유지되는 learned state | 새 엔진을 매번 재학습해서 persistence를 대체하지 않음 |
| 비용 분리 | dependency/signal/binding/proof/learning/storage/wall time 각각 | aliases 이중합산, macro 호출수로 proof D 축소 금지 |
| trade-off | training3/9의 실제 비용과 오류 수정 비교 | 더 강한 학습이 항상 수정 비용을 높인다고 미리 결론내리지 않음 |

신규 단위·통합 시험에는 정상 경로 외에 binding stale revision, 잘못된 parent/역할, 중복 feedback, budget fallback/abstention, macro 내부 측면 분기 보존, 부정 coverage, frozen memory, schema 분리, append-only 보존, 변조 후 재해시한 tick/학습/집계 탐지를 포함한다.

현재 개발 protocol은 소수의 의도적으로 설계한 사례다. 외부 holdout corpus, 통계적 일반화, 사람 감각의 설명, GPU/뉴로모픽 효율은 별도 검증 대상이다.
