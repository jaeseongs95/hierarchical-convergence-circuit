# R070: 회로 약화 신호의 전달 경계 재분석

R069의 동일 관측 새 세션은 M0/M1에서 판단과 정수 비용이 같았다. 이번 작업은 그 원자료의 pool과 decision 계산을 분리해 확인한다. 기존 회로, engine, memory, observation, config와 raw evidence를 변경하지 않는다.

## 질문과 대안

1. strength 변경이 pool prior와 drive까지 전달되지 않았다.
2. pool 수치는 변했지만 기존 eligibility 경계를 넘지 않아 같은 회로가 선택됐다.
3. 선택 경로가 같을 때 route_only의 decision network는 prior 차이를 직접 받지 않았다.

위 설명은 서로 배타적이지 않다. 원자료에서 각 경계의 변화 여부를 따로 판정한다. M0/M1는 strength만 바꾼 개입이 아니라 version, feedback 이력 등을 포함한 checkpoint 비교다. 동일 관측·episode 수가 확인될 때 prior 식의 strength 항에 수치 차이를 연결한다.

## 실행 전 고정한 측정

R069의 new-M0-stale, new-M1-stale, new-M0-fresh, new-M1-fresh 네 packet을 사용한다. 부모 bundle/source manifest의 바이트 hash와 전체 파일 목록을 확인한다. 복사본에서 기존 독립 session audit를 수행하고, pool grammar·drive·mismatch를 별도 evaluator 식으로 구성한 뒤 초기 activation 0.5부터 모든 tick을 재생한다. 수치 허용 오차는 2e-12다.

pool activation, stable 상태, activation/mismatch threshold, eligibility, 최초 선택, decision program·drive와 전체 숫자 궤적을 비교한다. 최종 판단이 같아도 pool 궤적이 다르면 계산 전체가 같다고 쓰지 않는다. 새 process의 검산기는 분석 모듈을 import하지 않고 독립 감사된 packet에서 집계 projection을 대조한다.

동일 조건의 두 activation이 다르고 stable·mismatch gate가 모두 허용하면 두 값 사이 `(낮은 값, 높은 값]`을 threshold 재분류의 수학적 구간으로 산출한다. 이는 기존 수치에서 도출한 후속 설계 입력이며 새 native 실행 결과가 아니다. 경계 조건을 실행해 선택·readout 변화가 생겼다고 주장하지 않는다.

## 수용과 한계

핵심 수용 조건은 원본 보존, 네 packet의 수식/궤적/선택 대조, 여덟 종류 측정 변조 거부, 별도 집계 검산과 기존 core 회귀 1회다. 원클릭은 `Run-HCR-R070.cmd`이며 기존 결과를 덮어쓰지 않는다. 실패와 traceback을 별도 디렉터리에 보존하고 자동 retry하지 않는다.

새 native 연구 실행과 새 독립 표본은 모두 0이다. 단일 회로 후보여서 회로 간 경쟁은 측정 불가다. synthetic 변조 검사는 구현 검증이며 연구 표본이 아니다. 에너지·메모리는 측정하지 않으며 일반적 학습 효과, 자율 sensing과 HCC 우위는 주장하지 않는다.
