# R0.1의 구체화된 계산 선택

원문 hypothesis의 유일한 구현이라고 주장하지 않는다. 식, 자료형, credit 규칙은 `architecture/r01-engine.ko.md`와 `configs/r01.toml`에 명시했다.

## 불변식

A level은 Group의 표현 종류이고, D는 별도 Proof의 직접 의존 깊이다. kernel tick, 전달 간선 수, graph 확장량, 설명 복원량은 모두 다른 양이다.

같은 tick 안에 persistent memory나 topology를 바꾸지 않는다. Feedback은 결정 이후 별도 호출이며 새로운 memory version을 만든다. runtime는 reference evaluator나 환경 truth 객체를 import하지 않는다.

false proof는 모든 공개 단순 경로의 blocked witness를 포함해야 한다. true proof는 현재 assumption으로 성립하는 실제 start→goal 경로를 포함해야 한다. primitive 직접 부모를 생략하면 invalid다. 신호상 feedback은 논리적 근거가 아니다.

## 계측

`search_edge_checks`, `dynamic_groups_created`, `dynamic_links_created`, `binding_checks`, `recall_checks`, `circuit_groups_instantiated`, `kernel_ticks`, `group_updates`, `signal_transmissions`, `normalization_ops`, `proof_nodes_reconstructed`, `compilation_items`, `memory_write_items`, `observation_requests`, `verification_checks`를 별도로 기록한다.

학습과 전체 run의 실측 시간, snapshot 입출력 바이트·시간도 따로 있다. 이것은 CPU 모든 명령의 성능 모델이 아니다. 비용의 종류가 다른 수를 무가중 합산해 '계산량 N% 절감'이라고 하지 않는다. calibration/referee 자체의 비용도 학습 실행과 구분한다.
