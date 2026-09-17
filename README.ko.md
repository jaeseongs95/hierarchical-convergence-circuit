# 현재 상태 — R0.2.1 Session / Snapshot / Restore / Resume

기준 commit: `2e67f71804b172673212822291b15885ca64f729`. R0.2의 실제 동작을 보존하면서 dependency 단위 중단·복원을 추가했다.
EXP-09 요약 오류 복구는 이미 완료된 연구 기준선이며, R0.2.1은 prior/학습/효율 정책을 변경하지 않는다.

- [적용·실행 명령](docs/R021_USAGE.ko.md)
- [설계·검산 범위](architecture/r021-session.ko.md)
- [EXP-10 동작 보존 실험](experiments/exp-10-session-continuity/design.md)
- [작성 환경 검증과 Windows 실행 상태](docs/R021_ACCEPTANCE.ko.md)

새 결과는 저장소 내부 `HCR-Evidence/exp10/새폴더`에 누적할 수 있다. 기존 run/capture/recovery와 배포 이력은 수정하지 않는다.
`hcr.py session`으로 새 기능을 선택하며 기존 `hcr.py demo --engine r02`와 R0.1 기본 명령은 유지한다.

---

## 아래는 앞 단계의 기록

# 현재 상태 — R0.2 + 기준선 캡처 + 개념 추적 보강

사용자 실행 보고에서 R0.2 `136/136` 테스트·demo·audit 통과, 기준선 보조 도구 `16/16` 테스트와 capture 생성 완료가 확인됐다. 아래 '소스 작성·정적 검사'는 **배포 당시 기록**이며 현재 실행 상태를 되돌리지 않는다.

- 최신 전체 계획: [HCR Master Roadmap](docs/HCR_MASTER_ROADMAP.ko.md)
- 24개 개념/구현/명세 연결: [개념 대조](docs/CONCEPT_COVERAGE.ko.md)
- 이번 수정 근거·한계: [소스 검토](docs/CONCEPT_PATCH_REVIEW.ko.md)
- 새 도구: [사용법](docs/CONCEPT_PATCH_USAGE.ko.md)

이번 개념 보강은 `src/hcr`, `configs`, 기존 회귀시험을 변경하지 않는다. R0.2.1이나 물리 하드웨어를 구현한 패치가 아니다. 원격 HEAD는 연결에서 확인되지 않았으므로 적용기는 적용 완료가 보고된 로컬 기준 파일과 비교한다. 실행·커밋·push는 사용자가 수행한다.

---

## 아래는 R0.2 최초 배포와 R0.1의 보존 기록

# R0.2 추가 — Adaptive Graph/Circuit Engine

이 배포는 기존 R0.1을 보존하면서 `--engine r02`로 선택하는 D-expansion/부분회로 경로를 추가한다. **소스 작성·정적 검사 상태이며, 배포 세션에서 테스트나 실험을 실행하지 않았다.**

```powershell
python -X utf8 -B hcr.py check
python -X utf8 -B hcr.py demo --engine r02 --config configs/r02.toml --out runs/r02_first
python -X utf8 -B hcr.py verify --run runs/r02_first
```

[적용·실행](docs/R02_USAGE.ko.md) · [R0.2 구조](architecture/r02-engine.ko.md) · [수용 기준](docs/R02_ACCEPTANCE.ko.md) · [개발 protocol](experiments/exp-08-r02-adaptive-integration/design.md)

기존 R0.1 API/설정/시험은 유지한다. 아래 R0.1 설명과 과거 실행 기록은 R0.2 실행 결과가 아니다. 부분 컴파일 범위는 길이2·3 directed path motifs이며, dependency 탐색 감소와 총 연산 감소를 분리해서 측정한다.

---

# Hierarchical Convergence Circuit — HCR R0.1

**상태: 실행 가능한 소규모 CPU reference.** 이론·증거·실험을 분리한 연구 저장소에, 두 A 수준에서 graph↔circuit 학습 순환을 수행하는 하나의 `src/hcr` 엔진을 추가했다. 실제 뇌/LLM/뉴로모픽 구현이나 가설의 실증으로 주장하지 않는다.

## 바로 실행

Python 3.12 이상만 필요하다. NumPy·PyTorch·Ollama·모델 파일·API key·인터넷 연결이 필요 없다. ZIP은 원래 프로젝트 위에 덮지 말고 새 빈 디렉터리에 풀어 `hcr.py`가 있는 곳으로 이동한다.

```powershell
python -X utf8 -B hcr.py check
python -X utf8 -B hcr.py demo --config configs/r01.toml --out runs/r01_first
python -X utf8 -B hcr.py verify --run runs/r01_first
```

`runs/r01_first`가 이미 있으면 덮어쓰지 않는다. 새 이름을 지정한다. `demo`가 실패하면 불완전 기록을 보존하고, verifier는 complete인 결과만 받아들인다. verify 영수증을 파일로 남길 때는 `--out`으로 run 폴더 밖을 지정한다.

Windows PowerShell 진입점도 있다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Run-HCR.ps1 -CheckOnly
powershell -NoProfile -ExecutionPolicy Bypass -File .\Run-HCR.ps1
```

두 번째 명령은 자체시험→demo→verify를 수행하고 새 timestamp 폴더를 만든다. 기존 Python을 못 찾으면 `-PythonPath "C:\...\python.exe"`로 지정한다. 자동 설치·git 초기화·모델 다운로드를 하지 않는다. 스크립트는 프로젝트 파일과 함께 두어야 하며 단독 내장 ZIP 실행기가 아니다.

## 공개 관측만으로 추론

```powershell
python -X utf8 -B hcr.py infer --input configs/example_observation.json --out runs/input_01
python -X utf8 -B hcr.py infer --input configs/example_observation.json --memory runs/r01_first/memory_after_training.json --out runs/input_02
```

`infer`는 truth/label/scenario 필드를 허용하지 않으며 정답을 판정하지 않는다. `verify --run`은 전체 demo 기록용이고 단독 infer 폴더에 대한 평가기를 실행하지 않는다. 프로그램 API는 `hcr.runtime.Engine`, `hcr.model.Observation`, `hcr.circuits.Memory`다.

## 구조 결정

첨부안의 연구 저장소 바깥 틀을 채택했고, 이전 HCR R0.1 계획의 작은 단일 엔진을 안에 배치했다. 초깃단계부터 공통 엔진을 src에 두며, 실험/시뮬레이션별로 복제하지 않는다.

```text
hierarchical-convergence-circuit/
├─ theory/                 # 원 가설과 변경 없는 원문 snapshot
├─ formalism/              # 정의·불변식·R0.1 구체 수식
├─ evidence/               # 원 주장 목록 + 별도 구현 상태
├─ architecture/           # 이전 설계와 최종 실행 경계
├─ docs/decisions/         # 두 구조의 비교·선택 근거
├─ experiments/exp-00-.../ # 지금 실행하는 개발 통합 fixture
├─ experiments/exp-01~07/  # 기존 draft 연구 계획, 완료 처리하지 않음
├─ src/hcr/                # 한 공통 kernel과 한 실행 엔진
├─ tests/                  # 단위·경계·학습순환·감사/위변조 검사
├─ configs/                # 개발 설정과 공개 관측 예시
├─ scripts/                # selftest·calibration·기존 저장소 도구
├─ simulations/            # 향후 탐색 연구 구획; 별도 엔진 없음
├─ related-work/, papers/  # 원 제안의 후속 연구 구획
├─ hcr.py, Run-HCR.ps1     # 로컬 실행 진입점
└─ runs/                   # 실행 출력. Git 기본 제외
```

상세 비교: [ADR-001](docs/decisions/ADR-001-project-structure.ko.md)  
실제 아키텍처: [architecture/r01-engine.ko.md](architecture/r01-engine.ko.md)  
범위·조건: [EXP-00](experiments/exp-00-r01-integration/design.md)

## 실제 구현한 최소 순환

cold 입력에서 후보 관계 graph를 만들고 같은 kernel로 두 수준이 경쟁한다. 반복된 외부 검증 이후 role Program을 circuit memory로 저장한다. 새로운 이름·edge 순서에서도 binding으로 회로를 불러와 현재 관측을 새로 계산한다. 학습된 편향 prior로 안정된 오답이 발생할 수 있으며, feedback 뒤 회로 신뢰를 약화하고 추가 측정·새 graph 실행으로 판단을 다시 만든다. 최초 오답과 새 판단은 모두 남는다.

학습한 것은 Program의 재사용 구조·recall strength·outcome-frequency prior다. feature encoder·공개 topology·AND/OR 문법과 학습 정책은 수작업이다. 작은 whole-graph 프로그램 재사용을 일반 subgraph mining이나 인간의 직관과 동일시하지 않는다. primitive proof D는 재사용 후에도 같은 기준으로 계산한다.

## 검증 경계

`check`는 네트워크를 차단한 공학시험이다. `scripts/calibrate.py`는 46개의 명확한 합성 boolean 환경을 cold/warm·순서 조건에서 184번 점검한다. demo는 단일 엔진의 상태 전이/학습/영속성 증거다. 연구 데이터의 새 독립 표본이나 모델 규모 비교는 아니다.

```powershell
python -X utf8 -B scripts/calibrate.py --out runs/calibration_result.json
```

실행 감사는 파일 hash와 event chain을 확인하고, 생산 kernel을 import하지 않는 별도 식으로 모든 tick을 계산한다. proof·외부 채점은 같은 독립 reference를 재실행하며, 핵심 집계·비용은 별도로 집계한다. 모든 구현이 서로 독립됐다고 말하지 않는다. 내부 기록 일관성 검산이지 외부 실행 인증은 아니다.

## 주장·기존 자산

`theory/source/...`와 `evidence/claims.yaml`은 첨부본 그대로다. 기존 LLM 관찰을 여기서 재실행했다고 하지 않는다. 이번 구현점검은 `evidence/implementation/r01_status.json`에 별도로 기록한다. 실험을 돌렸다는 이유만으로 HCC-H 가설 상태를 변경하지 않는다.

`thought-graph-simulator`와 v0xx evidence는 별도 프로젝트다. 이 실행에 가져오거나 변경하지 않는다. 과거 전체 source/evidence를 실행마다 재귀적으로 복사하지 않는다.

## 라이선스

첨부안에서 라이선스를 임의 선택하지 않은 방침을 유지했다. 게시·재배포 정책을 자동으로 결정하거나 외부 저장소에 push하지 않는다.
