# EXP-41 / R060 사전 동결 설계

## 질문과 이전 근거

R057은 초기 상태 의존성, R058은 512 tick의 상태 지속성을 관찰했다.
R059의 두 anchor에서는 한 좌표씩 ±1e-4 교란한 20개 조건이 모두
128 tick의 사전 복원 기준을 충족했다. 축 방향 복원만으로 여러 좌표가
동시에 변할 때도 복원되는지는 판단할 수 없다. R059 결과의 후속 제안을 검사한다.

## 조건과 개입

기준 main은 `b3fc168a4650851b5930964ac79fdaa8eb96cc27`이다.
R058 goal/full initial=.5와 .9의 tick 512 상태를 각각 low/high anchor로 사용한다.
R052 c001/start_edge full program, link·배열 순서·bias, goal 방향 drive
`e:0=.08, e:1=4, goal=0`, default config 및 동기 갱신식은 유지한다.

각 anchor에서 다섯 좌표 `e:0, e:1, p:0:0, p:0:1, goal`을 동시에
±1e-4씩 바꾸는 32개 부호 조합과 무교란 대조 1개, 합계 66 branch를 실행한다.
각 branch는 anchor의 새 복사본에서 시작하며 tick 0에 한 번만 개입한다.
clipping·정규화·host correction은 없다. 사전 범위 확인에서 모든 시작 상태가
[0,1] 안에 있음을 확인했다. 안정 counter는 모두 0에서 시작한다.
128 tick을 끝까지 실행하며 조기 종료하지 않는다.

R059와 L-infinity 초기 변화량은 같지만 L1 변화량은 5배, L2 변화량은
sqrt(5)배다. 전체 교란 크기까지 통제한 비교로 해석하지 않는다.
32개 방향은 5차원 상자의 꼭짓점이며 면·모서리 내부나 모든 방향을 덮지 않는다.

## 사전 측정과 판정

같은 anchor의 무교란 대조와 같은 tick에서 전 좌표 최대 절대 차이를 계산한다.
tick 113..128 모두 `<=1e-8`이면 유한시간 복원 true, 아니면 false다.
무교란 대조의 복원 판정은 null이다. 최종 거리만 작아도 tail 이탈이 있으면 실패다.
복원과 비복원은 모두 유효한 연구 결과이며 audit 성공에 복원을 요구하지 않는다.

secondary는 tick 1/16/32/64/128 거리, 전체 최대 거리/초기 거리 비,
관측한 끝까지 tolerance 안에 머무르는 최초 tick, 최종 state/residual/counter다.
goal band는 `<.5-1e-6` low, `>.5+1e-6` high, 나머지는 inconclusive다.
tick 0..128의 범주 유지와 대조 궤적 복원을 별도로 판정한다.
최초 복원 tick은 관측한 suffix에 관한 값이며 이후 무한시간 유지를 뜻하지 않는다.

비용은 66 branch의 kernel_ticks, group_updates, normalization_ops,
signal_transmissions를 단위별로 보고한다. anchor 생성·출처 재생·smoke·검산은
연구 비용에 합산하지 않는다. native packet/proof/support/raw decision/adoption과
실제 에너지는 null이다. 결정적 paired intervention을 독립 표본으로 세지 않는다.

## 출처·검증·실행 계약

spec은 R052 출처 10개와 R058 anchor 출처 6개의 byte hash를 고정한다.
검산기는 원래 network와 두 anchor의 최초 종료·512 tick까지를 재계산한다.
R060의 각 초기 상태, 128개 tick·residual·counter·비용은 매 관측 상태에서
다음 한 단계를 별도 수식으로 검산한다. 생산기/runtime/dynamics를 import하지 않는
별도 프로세스에서 수행하고 raw로부터 거리와 판정을 계산한다.
기존 R059의 kernel loop와 anchor 검산을 재사용하되 과거 소스는 수정하지 않는다.

`Run-HCR-R060.cmd`: source/spec/parents/anchors 동결 → synthetic self-test →
별도 smoke 8개(각 anchor의 control/mmmmm/ppppp/mpmpm)와 수치 검산 →
최종 core regression 1회 → 연구 66개 1회 → 별도 수치 검산 → summary/bundle/ZIP.
개발 중 synthetic 결함 수정은 허용하되 연구 후 조건·tolerance 변경과 재실행은 없다.
최초 실패·traceback·부분 evidence를 보존하며 자동 retry나 결과 덮어쓰기를 하지 않는다.
새 실행기에는 Git 조작이 없고 기본 EXP-30 dispatcher는 유지한다.

범위는 R060 add-on·진입점·EXP-41 문서/index 및 신규 evidence다.
core/tests/releases와 기존 raw·manifest·사용자 미추적 파일은 보존한다.
결과와 필수 검증을 확인하면 커밋·로컬 main 병합·작업 브랜치 정리·일반 push와
원격 일치를 확인한다. 결과 해석은 실행 뒤 문서로 남기며 frozen source에 소급 편입하지 않는다.

## 주장 범위와 종료

고정 synthetic recurrence의 두 상태·64개 동시 부호 교란·128 tick에 한정한다.
근방 전체 안정성·basin 경계·수학적 attractor·무한시간 안정성·학습된 Circuit을
증명하지 않는다. LLM 내부, 인간 인지나 HCC 전체 가설의 직접 근거가 아니다.
필수 검증 후 추가 방향·크기·horizon 탐색은 다음 실험으로 남긴다.
