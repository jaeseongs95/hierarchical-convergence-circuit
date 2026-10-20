# EXP-74 고정 실행 설계

질문: 원래 eligible Boolean을 source에서 정확한 임계 비교로 변환하면 기존 guarded 실행을 보존하면서 매6입력의 생성·검증 비용까지 줄일 수 있는가?

R=reset, L=legacy_guarded, C=compiled_guarded. 블록0은 R/L/C·stream정순, 블록1은 C/L/R·역순, 블록2는 L/R/C·역순, 블록3은 C/R/L·정순이다. 각 arm/stream/block은 독립 case process이며 state와 compiler를 처음부터 만든다. 전체48case process×6cell=288settles/46,080tick상한. 순차 worker1, 전체600초·stage60초·retry0, AS512MiB·parentfile32MiB/child16MiB·raw128MiB를 기존 runner로 적용한다.

원 R26의 고정4stream×6cell을 사용한다. 새 학습·세계 측정은0이다. 동일 native 코드를 호출하며 production source는 바꾸지 않는다. L/C는 binding의 정책 이름만 동일 guarded로 두고 별도 process·빈 cache로 격리하여 semantic field를 직접 비교한다. q/rows 객체가 필요한 기존 R26/R27 경로는 그대로 둔다.

의미 수용: 모든96 L/C 대응 cell에서 gate Boolean, 선택·cache 전후·initial·전체 kernel record를 타입/float bit까지 비교한다. 별도 scalar recurrence와 convergence/cost를 최대1e-15 오차로 재생한다. reset 대비 status/adopted 동일·terminal state 최대차1e-4를96대조에서 관측한다. 이 반복은24개 개발 입력을4회 실행한 것이며 독립96개 품질 표본이 아니다. 불일치/한도 초과 시 중단한다.

비용 경계1 cold lifecycle: spec/config/program 생성, 원 source SHA/profile 검증, binding, 매번 최대63회 탐색과 별도 verify, drives/membership, 원 choose, native/tick trace, state 관리, 결과 구성과 한 번의 전체 JSON 직렬화를 포함한다. compiler·state의 stream/block간 cache는 없다. 생성된 threshold를 디스크에 store/load하는 동작은 없으므로 해당 호출은0이다. 결과파일 출력은 cache store/load로 세지 않는다.

비용 경계2 case process: runner의 자식 CPU 및 wall에서 import, case dispatch, cold lifecycle, 마지막 timing 필드를 넣은 직렬화·파일출력·종료까지 기록한다. 프로세스 wall에는 scheduling/wait 비용도 포함된다. preparation/audit/source검사/seal은 연구실행 비용 원장으로 분리한다. gate-free 산술을 이 두 실측으로 대체하지 않는다. 실패 실행 비용도 result/stages에 남긴다.

개선 관측 기준: 각4블록의4stream 합계에서 C가 R과 L 양쪽보다 CPU와 wall 각각 엄격히 작고 차이가1마이크로초를 넘어야 한다. 실제 clock 해상도가1마이크로초보다 거칠면 그 해상도 이하 차이도 미입증이다. cold 경계와 full process 경계를 따로 평가하며, 어느 경계가 실패했는지 공개한다. cold 비용만 줄고 총process 비용이 줄지 않으면 전체 비용 이득으로 보고하지 않는다. 시간 부호가 순서에 따라 바뀌거나 비용 순이득이 없으면 미입증으로 종료한다. 통계적 유의성·품질 일반화·production adoption은 주장하지 않는다. 사후 threshold/수명/입력/반복 조정은 금지한다.

실행 전 준비 검사는 native나 시간을 측정하지 않는다. 저장 R26 기록으로 audit·변조 검출을 미리 연습하는 경우 합성 기록 검사라고 표시하며 신규 native 결과로 세지 않는다. 원격 결과는 별도 manifest와 수신 SHA 검증 뒤에만 결과로 채택한다.
