# R044 / EXP-25 — 회로 재사용의 실제 계산 기여

학습 memory는 유지하면서 기존 native `use_circuits`를 ON/OFF하는 24조건 대조다. 새 scheduler나 학습 규칙을 추가하지 않는다. `route_only`, `online_support`, `input_order`는 양군에서 고정한다.

실행은 `HCR_R044_EXP25_OneClick.cmd`를 기존 R043 저장소 루트에 놓고 더블클릭한다. 독립 실행 CMD에는 필요한 추가 소스 ZIP이 내장돼 있다. 이 ZIP만 검토할 때는 기존 파일을 삭제하지 않는다.

설계: `docs/R044_DESIGN.ko.md`.
실행·결과: `docs/R044_USAGE.ko.md`.
검증 범위: `validation/r044/검증보고서.md`.

주 보고서는 `analysis/paired_reuse.csv`, `network_costs.csv`, `expansion_actions.csv`, `summary.ko.md`다. expansion 감소와 native ticks 감소를 별도 판정하며, 출력이 달라진 경우 같은 품질의 효율 향상으로 표시하지 않는다.

단위·오류 주입 검사 100개 통과. 생성 환경에서 실제 native 통합·24조건 본 실험·Windows 실행은 미수행이며, 원클릭 실행은 native 검증 실패를 건너뛰지 않는다. Git commit/push, 네트워크, 의존 패키지 자동 설치·retry·host correction은 없다.
