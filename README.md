# 현재 상태 — R0.3.2 근거 진단·명시적 readout 대조

EXP-12 분석 이후 부분 결측의 과도한 확정을 진단하는 계층을 추가했다.
기존 판단/proof를 보존하고 선택 proof의 관측 지지와 외부 정확도를 분리한다.
진단 전용과 두 보류 정책은 별도 view이며 내부 정답 수정이나 새 학습이 아니다.

- [R0.3.2 설계](docs/R032_DESIGN.ko.md) · [실행](docs/R032_USAGE.ko.md)
- [EXP-13](experiments/exp-13-evidence-grounding/design.md)
- 실행: `python -X utf8 -B Run-HCR-R032.py --out HCR-Evidence/exp13/r032-first`

---

# 현재 단계 — R0.3.1: prior 역할 분리 (2026-09-17)

회로 선택용 prior는 유지하고, 최종 relation/goal 판단에 전달하는 learned prior만 독립 조작한다.
기본 API는 기존 legacy 동작이다. `route_only`와 `graph_only`는 EXP-12의 명시적 대조 조건이다.
- [구현·검증 범위](docs/R031_DESIGN.ko.md) · [적용 후 실행](docs/R031_USAGE.ko.md)
- Windows에서는 `python -X utf8 -B Run-HCR-R031.py --out HCR-Evidence/exp12/r031-first`를 사용한다.
- 기존 실험 증거는 유지한다. rigidity·부정 예외 학습·pool 최적화는 이 변경에 포함하지 않는다.

이하 본문은 사용자의 기존 내용을 보존한 기록이다.

---

# 현재 상태 — R0.3 Method Interleaving / Typed Route Hints

R0.2.1 상태 보존 기반 위에 제한된 M 전문화와 중간 경로 교환을 추가한다.
[적용·실행](docs/R03_USAGE.ko.md) · [설계](architecture/r03-methods.ko.md) · [개발 검증](docs/R03_ACCEPTANCE.ko.md).
결과는 `HCR-Evidence/exp11/`의 새 폴더에 누적한다. 기존 학습·prior 규칙은 변경하지 않는다.
아래 내용은 사용자가 관리한 기존 본문과 이전 버전의 기록이다.

---

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

## 현재 프로젝트 구조

아래 구조는 **현재 `main` 브랜치에 실제로 추적되어 올라가 있는 항목**을 기준으로 정리한다. 실행 시 생성되는 `runs/`는 `.gitignore` 대상이므로 현재 저장소 트리에는 포함하지 않는다.

```text
hierarchical-convergence-circuit/
├─ .github/
│  ├─ ISSUE_TEMPLATE/             # 실험 제안·이론 변경용 이슈 템플릿
│  └─ pull_request_template.md     # PR 검토 템플릿
├─ theory/
│  ├─ source/                     # 변경하지 않는 원 가설/source snapshot
│  ├─ core-hypothesis.md          # 현재 파생된 핵심 가설 정리
│  └─ versioning.md               # 이론 문서 버전 관리 원칙
├─ formalism/                     # 변수·불변식·실패 분류·계산 정의
├─ architecture/                  # HCR 계산/실행 아키텍처와 substrate 계약
├─ evidence/
│  ├─ claims.yaml                 # 주장 상태의 기준 registry
│  ├─ concept_coverage.json       # 개념↔구현/명세 대응 상태
│  └─ implementation/             # R0.1/R0.2 구현·실행·baseline 상태 기록
├─ experiments/
│  ├─ exp-00-r01-integration/     # R0.1 개발 통합 fixture
│  ├─ exp-01-... ~ exp-07-...     # 연구 가설별 실험 설계 draft
│  └─ exp-08-r02-adaptive-integration/ # R0.2 통합 개발 protocol
├─ src/
│  └─ hcr/
│     ├─ evaluation/              # 독립 reference·protocol·audit 계층
│     ├─ tasks/                   # 합성 task/world 정의
│     └─ *.py                     # activation/binding/circuit/graph/runtime 등 공통 엔진
├─ tests/                         # 공통 엔진, R0.1/R0.2, trace/audit 회귀시험
├─ configs/                       # R0.1/R0.2 설정과 공개 관측 입력 예시
├─ scripts/                       # selftest·calibration·구조/릴리스 검증·초기화 보조
├─ tools/
│  ├─ r02_baseline/               # R0.2 baseline/EXP09 측정·probe·audit·복구 도구
│  │  └─ tests/                   # baseline/EXP09 도구 자체 검증과 fixture
│  └─ r02_concepts/               # 개념 coverage 정적 검사·review 도구와 시험
├─ simulations/
│  ├─ cognitive/                  # 추상 candidate/graph/circuit dynamics 탐색 구획
│  └─ neural-circuit/             # 향후 sparse recurrent/event-driven 대응 탐색 구획
├─ related-work/                  # 선행연구 비교·차이·판별 실험 기록 구획
├─ papers/
│  └─ working-paper/              # 논문 초안/working paper 작성 구획
├─ docs/
│  ├─ AI chat/                    # 연구 대화 기반 정리·통합가설·설계검토 원자료
│  ├─ decisions/                  # 구조 선택 등 ADR
│  ├─ reference/                  # 초기 문서·과거 release/roadmap snapshot 보존
│  └─ *.md                        # 사용법·acceptance·baseline·EXP09·master roadmap
├─ HCR-Evidence/
│  ├─ exp09/                      # EXP09 복구 결과, 재검산·분석, 원자료 묶음
│  ├─ hcr-r02-baseline-capture-20260916/ # R0.2 baseline capture와 분석 산출물
│  ├─ hcr-r02-concept-review-20260916/    # 개념 추적 review 산출물
│  ├─ hierarchical-convergence-circuit-before-r02-*/ # 단계별 변경 전 snapshot
│  └─ r02-diagnostic-01/          # 원 진단 run과 도구 source 보존
├─ hcr.py                         # Python CLI 진입점
├─ Run-HCR.ps1                    # 기본 실행 PowerShell 진입점
├─ Run-HCR-R02.ps1                # R0.2 실행 PowerShell 진입점
├─ pyproject.toml                 # Python 프로젝트/패키지 설정
├─ RELEASE_MANIFEST.json          # 현재 release 파일 manifest
├─ ROADMAP.md                     # 저장소 수준 roadmap
├─ HCR_통합_개발연구_로드맵_R02이후_2026-09-16.md # 통합 개발·연구 계획 원문
├─ CHANGELOG.md                   # 변경 이력
├─ CONTRIBUTING.md                # 기여/연구 작업 규칙
├─ README.md / README.ko.md       # 프로젝트 진입 문서
└─ .editorconfig / .gitattributes / .gitignore
```

### 폴더별 역할과 담는 자료

| 경로 | 역할 | 주로 담는 자료 |
|---|---|---|
| `.github/` | GitHub 협업 절차 표준화 | 실험 제안·이론 변경 이슈 템플릿, PR 템플릿 |
| `theory/` | HCC/HCR 가설 자체와 그 버전 경계 관리 | 핵심 가설, 버전 규칙, 변경하지 않는 원문 snapshot |
| `formalism/` | 서술적 가설을 측정 가능한 계산 정의로 변환 | A/D/M/B, 상태전이, 불변식, 실패 taxonomy, R0.1 계산 정의 |
| `architecture/` | 이론을 실행 구조로 옮긴 설계 경계 정의 | R0.1/R0.2 엔진 구조, 최소 계산 아키텍처, substrate 계약, 원 설계안 |
| `evidence/` | **무엇을 주장하고 현재 어디까지 지지되는지** 관리하는 증거 메타 계층 | `claims.yaml`, 현재 경계, concept coverage, 구현/실행/baseline 상태 JSON |
| `experiments/` | 실험 조건과 판별 논리를 고정하는 protocol 구획 | EXP-00~08의 `design.md`; 개발 fixture와 아직 미실행인 연구 draft를 구분 |
| `src/hcr/` | 모든 실험이 공유하는 단일 HCR 실행 엔진 | graph expansion, binding, activation, dynamics, circuit memory/compile, learning, runtime, trace, evaluation |
| `tests/` | 공통 엔진과 감사 경계의 회귀 검증 | 계약·학습순환·R0.2 runtime·audit/trace CLI 테스트와 helper |
| `configs/` | 실행 조건과 공개 입력 정의 | `r01.toml`, `r02.toml`, `example_observation.json` |
| `scripts/` | 저장소 전반의 개발/검증 보조 | selftest, calibration, release/structure 검증, 초기화 스크립트 |
| `tools/r02_baseline/` | R0.2 baseline 및 EXP09 계측을 생산 엔진과 분리 | collect/probe, 독립 audit, cost 분석, measurement journal, memory equivalence, 실패 run 복구 도구와 자체 테스트 |
| `tools/r02_concepts/` | 가설 개념과 현재 코드/명세의 연결 상태를 정적으로 점검 | concept check/review 코드와 회귀시험 |
| `simulations/` | 동결된 실험 계약 이전의 탐색적 시뮬레이션 구획 | cognitive 추상 모델과 향후 neural-circuit mapping용 문서/코드 |
| `related-work/` | 기존 연구와 HCC의 중복·차이·판별 가능성 관리 | predictive coding, attractor, binding, neuromorphic 등 선행연구 비교 기록 |
| `papers/` | 연구 결과를 논문화하는 작업 공간 | working paper 초안과 논문 구성 자료 |
| `docs/` | 실행법·설계결정·로드맵·분석 문서의 중앙 문서 구획 | acceptance/usage/baseline/EXP09 문서, ADR, master roadmap, 초기 snapshot, AI 대화 기반 연구 정리 |
| `HCR-Evidence/` | **실제 실행에서 나온 원시·가공 evidence bundle과 복구/분석 산출물을 보존** | run/event/episode, memory snapshot, 비용 CSV, audit/receipt/manifest, source snapshot, EXP09 복구 결과와 재검산 자료 |

`evidence/`와 `HCR-Evidence/`는 역할이 다르다. 전자는 **claim·구현 상태·증거 경계를 구조화해서 관리하는 계층**이고, 후자는 **실제 실행 및 분석에서 생성되어 보존한 evidence artifact**를 담는다. EXP09 역시 현재 `experiments/exp-09-*` 폴더로 존재하는 것이 아니라, 비교 명세는 `docs/`, 측정·복구 코드는 `tools/r02_baseline/`, 실제 결과는 `HCR-Evidence/exp09/`에 분리되어 있다.

상세 구조 결정: [ADR-001](docs/decisions/ADR-001-project-structure.ko.md)  
현재 구조 원칙: [docs/repository-structure.md](docs/repository-structure.md)  
실제 아키텍처: [architecture/r01-engine.ko.md](architecture/r01-engine.ko.md), [architecture/r02-engine.ko.md](architecture/r02-engine.ko.md)  
최신 전체 계획: [HCR Master Roadmap](docs/HCR_MASTER_ROADMAP.ko.md)

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
