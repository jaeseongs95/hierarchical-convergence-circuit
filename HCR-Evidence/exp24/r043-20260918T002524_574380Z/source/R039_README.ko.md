# R0.3.9 / EXP-20

고정된 identity·관측·학습 memory 아래에서, 분기 배열 순서만으로 지지 경로 형성 시점과 온라인 채택의 비용이 달라지는지 조사한다.

기준선: `8713f17eedf684b8392f3d07d9d67a3b8f8f61cd`.
기준 raw: `HCR-Evidence/exp19/r038-20260917T121349_552337Z`.
기존 `src/hcr`, R035/R037/R038, 과거 evidence를 수정하지 않는다.

**원클릭 설치:** 별도 제공한 `HCR_R039_EXP20_OneClick.cmd` 한 파일을 루트에서 더블클릭.
**소스가 이미 적용됨:** 루트의 `Run-HCR-R039.bat` 더블클릭.

1개 topology × 6개 분기 배열 × 2개 prior × 3개 실험군 = 36회 fresh native 실행이다. 지지 경로/미탐색 frontier의 기회 발생이나 개선을 성공 조건으로 강제하지 않는다.

| 경로 | 역할 |
|---|---|
| `tools/r039_order_isolation/spec.py` | 배열 순열과 실행 계획 생성 |
| `tools/r039_order_isolation/input_audit.py` | 생성기와 독립적인 입력 불변성 검산 |
| `tools/r039_order_isolation/protocol.py` | 조건 동결·단회 실행·원문 보존 |
| `tools/r039_order_isolation/audit.py` | 기존 독립 native audit 연결·stream 검산 |
| `tools/r039_order_isolation/trajectory.py` | 평가 전용 slot→고정 edge ID 대응과 경로 형성 시점 |
| `tools/r039_order_isolation/reporting.py` | 순열 내부/순열 간 비교, 비용 단위 분리 |
| `tools/r039_order_isolation/sources.py` | EXP-19 parent capsule과 소스 fingerprint |
| `tools/r039_order_isolation/tests/` | 합성·단위·배포 검증; native 결과 아님 |
| `tools/r039_order_isolation/native_tests/` | 기존 대조 입력의 native 연결 검사 |
| `scripts/install_r039.py` | 기존 파일을 덮어쓰지 않는 추가 설치기 |
| `scripts/bootstrap_r039.ps1` | Windows Python 탐색과 실행 연결 |
| `docs/R039_DESIGN.ko.md` | 실험 정의·예측·판별 범위 |
| `docs/R039_USAGE.ko.md` | 설치·실행·출력 위치 |
| `validation/r039/` | 실제 수행한 검사 기록과 미실행 범위 |

실험군 실행은 R038 `TimingTrial`을 그대로 사용한다. 신규 native kernel·selector를 구현한 버전이 아니다. 따라서 원 실행 내부 schema는 R037/R038을 유지하고, EXP-20의 plan/raw/analysis schema만 새로 부여한다.
