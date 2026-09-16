# 현재 저장소 구조

R0.1 결정 문서는 `docs/decisions/ADR-001-project-structure.ko.md`다. 원 제안 문서는 `docs/reference/initial_docs_repository-structure.md`로 보존했다.

연구 구획은 theory/formalism/evidence/experiments/architecture/related-work/papers/simulations로 유지한다. 실제 공통 실행 코드는 성숙도와 관계없이 `src/hcr` 한 곳에 두고 experimental 상태를 버전과 문서에 표시한다. 실험 폴더에는 데이터·조건·명세를 두고 별도 kernel 복제본을 만들지 않는다.

API·GPU·LLM·plugin backend는 현재 구현하지 않는다. 미래 구획의 README는 구현 완료 표시가 아니다. tests는 폴더 존재뿐 아니라 실제 학습순환과 원응답 trace를 검사한다. generated run은 별도 경로에 저장하고 source hash로 출처를 식별한다.
