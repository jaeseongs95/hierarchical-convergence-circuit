# R0.4.0 / EXP-21 — Frontier 스케줄링 원인 분리

`ef074f7991733ba0a73d870780d4873718caf1ca` 기준 추가형 소스다.
원클릭 CMD 한 파일을 기존 루트에 두고 실행하면 설치·검사·72회 본 실험·독립 검산·bundle을 수행한다.
기존 엔진을 바꾸지 않고, 기존 `prioritize_frontier` API로 입력 순서 의존성을 분리한다.

| 경로 | 역할 |
|---|---|
| tools/r040_frontier_schedule/scheduler.py | 공개 ID/등록 경로만 받는 두 scheduler |
| runtime.py | R037 loop/R038 사후 경계와 공개 priority API 연결 |
| schedule_audit.py, control_audit.py | 독립 선택·priority 상태 변경·비용 검산 |
| native_audit.py, trial_audit.py | 기존 native 상태/proof/선택 audit 연결 |
| baseline_audit.py | input_order 대조와 EXP20 원 raw의 회귀 대조 |
| sources.py, protocol.py, spec.py | 기준선·72개 조건·원문 보존 |
| reporting.py | 선택 효과·스케줄러 효과·잔존 격차 보고 |
| tests/ | 합성 단위/파일/설치 경계 검사 |
| native_tests/ | 실제 native API/제어 검산, 본 실험과 별도 |
| scripts/install_r040.py | 기존 파일 비덮어쓰기 설치 |
| Run-HCR-R040.py | 검증·동결·실행·audit·verify·bundle 순차 실행 |

설계: [docs/R040_DESIGN.ko.md](docs/R040_DESIGN.ko.md)
실행: [docs/R040_USAGE.ko.md](docs/R040_USAGE.ko.md)
배포 검증 범위: [validation/r040/검증보고서.md](validation/r040/검증보고서.md)

연구 대상은 한 topology의 6개 배열 × 2 prior × 3 arm × 2 scheduler이다.
새 scheduler의 정확도/효율 향상이나 배열 격차 제거를 audit 통과 조건으로 요구하지 않는다.
