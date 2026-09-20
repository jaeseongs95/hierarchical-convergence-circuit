# 단일 공통 엔진

R0.1은 experimental 상태지만 공통 구현을 지금부터 `hcr/`에 하나만 둔다. 실험별 복제 후 안정화 때 다시 합치는 방식을 사용하지 않는다. 외부 시스템과의 adapter가 필요해지면 평가 기준과 함께 추가하며 빈 backend 구조를 미리 만들지 않는다.

`hcr.runtime.Engine`은 evaluation/reference와 환경 World에 의존하지 않는다. 선택된 판단을 설명기나 평가기로 고쳐 반환하지 않는다. 각 책임은 `architecture/r01-engine.ko.md`에 정의했다.
