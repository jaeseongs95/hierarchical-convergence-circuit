# 계층적 수렴-회로 가설

> 감각·직관·추론·학습이 서로 다른 알고리즘의 집합이 아니라, 여러 추상화 수준에서 반복되는 공통 수렴 primitive로 설명될 수 있는지를 검증하는 연구 프로젝트.

**상태:** 작업 가설 / 검증 진행 중  
**기준 원문:** `theory/source/2026-09-16-integrated-hypothesis-ko.md`

## 핵심 가설

```text
Input
  ↓
Candidate activation
  ↓
Binding / dynamic routing
  ↓
Competition / inhibition / recurrence
  ↓
Convergence
  ├─ adequate → learning → reusable circuit
  └─ mismatch → graph expansion → A/D/M adaptation
```

강한 형태의 작업 가설은 다음과 같다.

- 새로운 문제에서는 동적인 Thought-Graph가 확장된다.
- 반복적으로 성공한 graph는 재사용 가능한 circuit으로 압축될 수 있다.
- 익숙한 문제의 직관은 compiled circuit의 빠른 재활성화일 수 있다.
- novelty/error가 발생하면 기존 circuit을 다시 graph로 풀어 추가 탐색할 수 있다.
- 착시와 잘못된 직관은 서로 다른 A 수준에서 발생하는 `stable misconvergence`라는 공통 오류 형태일 수 있다.

## 이 저장소가 구분하는 것

이 프로젝트는 다음 세 범주를 섞지 않는다.

1. **관찰된 결과** — 기존 LLM 실험에서 직접 보고된 현상.
2. **작업 가설** — 통합 모델이 제안하지만 아직 별도 검증이 필요한 메커니즘.
3. **도출 예측** — 이후 실험으로 반증 가능해야 하는 예측.

현재 LLM 실험만으로 뇌의 신경 회로나 전체 인지 구조를 증명했다고 취급하지 않는다. 주장별 상태는 [`evidence/claims.yaml`](evidence/claims.yaml)에서 관리한다.

## 핵심 구성요소

- **A — Abstraction:** 무엇을 어떤 표현 수준에서 다루는가.
- **D — Decomposition / Dependency Depth:** 결과를 지지하기 위해 필요한 실제 의존 구조의 깊이.
- **M — Modality / Method:** 후보 생성·비교·보정·검증·수렴 방식.
- **B — Binding Continuity:** 실행 중 의미·identity·relation이 안정적으로 유지되는 기반 조건.
- **Graph ↔ Circuit:** 새 문제의 동적 확장과 익숙한 문제의 압축·재사용.
- **Misconvergence:** 안정적으로 수렴했지만 외부 현실과 맞지 않는 오류.

## 디렉터리 구조

```text
hierarchical-convergence-circuit/
├─ theory/          # 가설, 버전별 원문
├─ formalism/       # 기호, 수식, 계산 모델
├─ evidence/        # 주장-증거 추적
├─ experiments/     # 반증 가능한 실험 프로그램
├─ simulations/     # 인지/신경회로 시뮬레이션
├─ architecture/    # 계산/뉴로모픽 아키텍처
├─ related-work/    # 선행연구 비교
├─ papers/          # 논문 작업 공간
├─ src/             # 안정화된 구현 코드
├─ tests/           # 실행 검증
├─ scripts/         # 저장소 유틸리티
└─ docs/            # 연구/저장소 운영 문서
```

자세한 역할은 [`docs/repository-structure.md`](docs/repository-structure.md) 참고.

## 초기 실험 프로그램

| ID | 실험 | 핵심 질문 |
|---|---|---|
| EXP-01 | Familiarity Compression | 반복 성공 후 실제 계산비용이 정확도 손실 없이 감소하는가? |
| EXP-02 | Novelty-triggered Graph Expansion | mismatch가 graph expansion 및 A/D/M 변화를 유발하는가? |
| EXP-03 | Misconvergence | 학습된 prior가 안정적이지만 외부적으로 잘못된 수렴을 만들 수 있는가? |
| EXP-04 | Binding Continuity | identity/semantic binding이 graph 안정성과 전이에 어떤 영향을 주는가? |
| EXP-05 | Cross-Abstraction Primitive | 같은 convergence primitive가 서로 다른 A 수준에서 작동할 수 있는가? |
| EXP-06 | Decision vs Explanation | 사후 설명 graph가 실제 실행 경로와 분리되는가? |
| EXP-07 | Attractor Strength vs Revisability | 압축·속도·수정 가능성 사이의 trade-off는 무엇인가? |

## `thought-graph-simulator`와의 관계

기존 `thought-graph-simulator`는 별도 저장소로 유지한다. 해당 프로젝트는 고차 reasoning graph의 representation/path/depth/binding에 대한 실험 근거를 제공하는 하위 실험계다. 이 저장소는 그 결과를 포함해 감각·직관·학습·회로 형성까지 확장하는 상위 이론 및 연구 프로그램이다.

## 연구 운영 원칙

중요한 주장은 모두 다음 정보를 가져야 한다.

- 고정 Claim ID
- 현재 상태
- 지지/반대 근거
- 반증 조건
- 상태를 갱신할 실험

[`docs/research-principles.md`](docs/research-principles.md)에서 상세 기준을 관리한다.

## Git 초기화

압축 해제 후:

```bash
git init
git add .
git commit -m "chore: initialize hierarchical convergence-circuit research repository"
```

Windows PowerShell에서는 `scripts/init-repo.ps1`, Linux/macOS에서는 `scripts/init-repo.sh`를 사용할 수 있다.

## 라이선스

현재는 오픈소스 라이선스를 임의로 선택하지 않았다. 라이선스를 명시하기 전까지는 일반적인 저작권 규칙이 적용된다. 외부 기여나 재사용을 허용하기 전에 코드/문서 라이선스를 명시적으로 결정한다.
