# R0.2 현재 상태 — 소스 작성, 실행 전

D/dependency 확장, bounded partial path compiler, 회로 후보 경쟁, binding identity, 비용 계측과 개발 실험을 추가했다. 실제 수용 여부는 `docs/R02_ACCEPTANCE.ko.md`의 사용자 실행 결과로 결정한다. R0.3 M adaptation / R0.4 A adaptation은 구현하지 않았다.

---

# 현재 개발·연구 로드맵

원 제안은 `docs/reference/initial_ROADMAP.md`에 보존했다.

## R0.1 — 제한된 기능적 통합 원형

두 A 수준의 공통 kernel, graph construction과 role Program 저장/재사용, feedback 권한, 오수렴·재확장·영속성, 외부 proof/reference와 독립 tick 감사를 구현한다. CPU·하나의 toy relational world에 제한한다. 원 가설의 완전한 실증 또는 넓은 EXP-01~07 완료로 처리하지 않는다.

## 다음 연구 gate

1. 개발 fixture와 분리한 입력·노이즈·구조에서 가설별 사전 기준을 고정한다. 학습비용/입력획득비용/검증비용까지 포함한다.
2. learned prior의 효율/오수렴/수정 가능성을 여러 강도와 양·음 경험 분포에서 평가한다.
3. 일반화된 부분그래프의 역할화·공통 subgraph 재사용과 압축/복원 경계를 검증한다.
4. 다른 표현과 다른 A 수준에서도 kernel을 유지할 수 있는지 더 넓은 EXP-05로 검증한다. 두 수준 구현을 이 일반성 검증의 완료로 보지 않는다.
5. 그 뒤에야 encoder 학습, GPU/분산/물리 backend, LLM adapter를 독립 대조와 함께 검토한다.

다음 작업은 항상 실패를 보존한 채 조건 변화와 버그 수정을 구분한다. 사례별 정답 분기와 평가기의 정답을 runtime에 연결하는 방식으로 성능을 올리지 않는다.
