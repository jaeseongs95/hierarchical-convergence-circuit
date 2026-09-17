# R0.3.2 — 근거 진단·명시적 readout 대조

- 기존 runtime/학습/pool/세션 동작을 보존하고 별도 grounding 진단 추가.
- 선택 proof의 결측·0·방향충돌과 actual drive/binding 출처 기록.
- diagnostic-only/dependency gate/blanket unknown gate를 별도 정책 view로 보존.
- EXP-13과 독립 진단 검산·위변조·원본 보존 시험 추가.
- Python 실행기 사용, 프로젝트 내부 HCR-Evidence 누적 출력 유지.

---

# 0.3.1 — Judgment prior scope

- legacy 기본 동작 유지, route_only의 최종 judgment drive 분리.
- policy-bound checkpoint와 별도 expected-drive 검산.
- EXP-12: 학습 3/6/9, 13개 공개 입력, 3조건, fixed network 진단.
- 후보 단계·결측·관측 0점·외부 truth 대응·비용 분해 기록.
- PowerShell 정책 변경 없는 Python 실행기.

# 0.3.0 — 제한된 M 전문화

- 기존 R0.2.1 기본 계산·학습·prior 보존.
- breadth-first primitive / depth-first macro 처리기와 fixed/adaptive memory interleaving.
- 실제 sender 경로만 전달하는 typed hint; 기존 receiver frontier 우선순위 변경.
- 합계 advance/tick/message 상한, 충돌/미완료 보류, 독립 replay 및 EXP-11.
- 프로젝트 내부 HCR-Evidence/exp11의 새 폴더로 결과 누적. 기존 결과는 변경하지 않음.

---

# 0.2.1 — 2026-09-17

- AdaptiveEngine.infer를 단일 begin/advance/finish 실행으로 분해. prior·학습 정책은 유지.
- AdaptiveSession의 generation·원자적 전이·JSON snapshot·독립 복원 검산 추가.
- session CLI와 EXP-10, Windows fail-fast 실행기, 79개 신규 계약/동작 시험 추가.
- 결과는 HCR-Evidence 하위 새 폴더 허용. 기존 원시 증거는 읽기 전용.
- 작성 환경 검증과 사용자 Windows 검증을 구분. 세부 결과는 docs/R021_ACCEPTANCE.ko.md.

---

# 0.2.0 — 2026-09-16 (실행 전 소스)

- 기존 src/hcr 구조에 deterministic ExpansionPolicy, 부분 경로 compiler, common-kernel CircuitActivationPool을 추가했다.
- Node/Semantic/Role binding과 revision 분리, 독립 비용 카운터, primitive proof 보존을 추가했다.
- 별도 R0.2 memory schema와 feedback/re-expansion/persistence 경로를 추가했다.
- R0.2 개발 protocol, 독립 수치/경로/학습/집계 audit 및 신규 시험을 추가했다.
- R0.1의 72개 시험과 기존 알고리즘 정의는 보존했다. 실제 R0.2 테스트/실험/커밋은 수행하지 않았다.

---

# Changelog

All notable theory, evidence, experiment-design, and architecture changes should be recorded here.

## [Unreleased]

### Added
- Initial repository structure.
- 2026-09-16 integrated Korean hypothesis source document.
- Initial claim registry.
- Seven experiment program directories.

## 0.1.0 — 2026-09-16

원 첨부 연구 구획을 유지하고 단일 src/hcr 기능적 엔진을 추가했다. 모드 경계, 역할 binding, 두 수준 recurrence, Program memory, feedback 이후 재확장, source/trace audit와 개발 fixture를 추가했다. 원 가설 source 및 claims.yaml의 과학적 상태는 변경하지 않았다. 기존 연구 프로그램과 좁은 구현 결과를 구분했다.
