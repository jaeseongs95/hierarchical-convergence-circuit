# EXP-15: Proof Selection, Restart and Judgment Prior

상위 설계: [R0.3.4 설계](../../docs/R034_DESIGN.ko.md)
실행: [적용·실행](../../docs/R034_USAGE.ko.md)
동결 조건: `src/hcr/evaluation/selection_spec.py`

## 연구 질문

EXP-14의 정보 부족/정책 문제 구분을 이어서, 같은 공개 정보와 memory에서 실패가 경로 미생성, 재시작, judgment prior, proof 선택 중 무엇과 관계되는지 구별한다.

## 가설과 대안

H1: 기존에 생성된 지지 경로가 있으면 proof 선택만으로 지지된 출력이 회복될 수 있다.
대안: 선택 가능한 지지 경로가 아직 없거나, 현재 raw 값/활성 상태가 이를 허용하지 않는다.

H2: 같은 prior로 다시 계산하는 것과 judgment prior를 제거한 재계산은 결과가 다를 수 있다.
대안: 재시작 자체로 충분하거나, 어떤 재시작도 정보 부족을 해소하지 못한다.

H3: 정보가 충분한 running 경계에서는 추가 계산만으로 최초 답을 생성할 수 있다.
이 대조는 최초 판단 이후의 수정과 다르며 main과 분리한다.

## 사전 정의

main 182 rollout + running 8 + 예산 4 = 194. 공유 baseline 18개. 학습 6회, 평가 중 memory 동결. 원 native 참·거짓 값은 sidecar 선택기가 뒤집지 않는다. 최소 관측, 자동 policy 학습, 신경학적 rigidity는 이번 대상이 아니다.

## 성공 및 실패 처리

논리적 정답을 audit 통과의 필수 조건으로 두지 않는다. 계획과 실제 작업이 일치하고 provenance·proof·비용을 독립 검산할 수 있어야 한다. 보류, support가 있어도 외부 정답이 아닌 경우, 예산 부족, 생성 및 측정 계약 실패를 각각 보존한다.

판별 결과가 예상과 다르면 기존 native proof를 강제로 대체해 성공으로 기록하지 않는다. 새 규칙은 명시적 arm의 새 candidate로만 실행한다.
