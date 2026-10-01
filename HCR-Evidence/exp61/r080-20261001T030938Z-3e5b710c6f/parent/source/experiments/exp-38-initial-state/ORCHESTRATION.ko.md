# R057 작업 구성

기준 commit: `ff3caf7ad0e486829a7dcd209b04b1a664f4673f`.
사용자의 다음 턴 진행 요청과 R056의 사후 판별 실험을 근거로 R057을 별도 동결 계약으로 구현한다.
현행 프로젝트 지침의 한 턴에는 검증·커밋·로컬 병합·push·원격 반영 확인이 포함된다.

development-orchestration으로 조사·조건 확정·구현·검산·해석·통합 단계를 구분한다.
기존 생성·검산 장치를 재사용하는 순차 작업이므로 main이 직접 수행하며 서브에이전트나
모델 override는 사용하지 않는다. 검산의 독립성은 생산기와 다른 수식·별도 프로세스에 한정한다.
독립 연구자·blind panel·최종 Judge 감사로 표현하지 않는다.

Ponytail 원칙에 따라 기존 execute, mask, provenance 검사와 trajectory verifier를 재사용한다.
새 부분은 조건별 uniform 초기 상태 주입·결속 검사와 baseline=.5 대비 대조다.
기존 raw·manifest를 보존하기 위해 버전별 add-on을 사용한다.

수용 기준은 동결 12행, .5 anchor 4개, 전 tick/최초 종료/cost 검산, 초기 상태 변조 거부,
fresh state 확인, 비안정 종료의 null 판정, contrast 방향, 회귀 1회와 bundle 무결성이다.
예측 방향의 성공은 수용 기준이 아니다. 실제 연구 전에는 synthetic fixture만 실행한다.
사후 해석은 별도 RESULTS.ko.md에 기록하며 동결 source에 소급해 넣지 않는다.
