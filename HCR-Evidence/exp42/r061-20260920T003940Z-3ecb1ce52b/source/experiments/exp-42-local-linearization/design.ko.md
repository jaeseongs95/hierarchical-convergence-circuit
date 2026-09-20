# EXP-42 / R061 사전 동결 설계

## 질문과 이전 근거

R059는 두 anchor에서 축 방향 교란의 복원을, R060은 동시 부호 교란의 복원을 관찰했다.
R060 low anchor에서는 8개 방향의 L-infinity 거리가 첫 tick에 증가했다.
이번에는 이 일시 증폭을 국소 선형화가 설명하는지, 유한 크기 비선형 효과가
필수인지를 한 단계에서 구별한다. 기준 main은 `5fcdbb3f44cfe14628a65971b3fe916b0169536d`다.

## 조건과 개입

R058 goal_i05/full과 goal_i09/full의 tick 512 상태를 그대로 사용한다.
R052 c001/start_edge program, drive, config, link·배열 순서·bias는 유지한다.
두 anchor 각각에서 다섯 좌표의 모든 32개 부호 방향을 epsilon
`1e-4, 1e-5, 1e-6`로 한 번씩 교란하고 무교란 대조 하나를 둔다.
총 194 branch는 anchor의 새 복사본에서 시작해 정확히 한 kernel tick을 실행한다.
clipping, host correction, 조기 종료, retry는 없다. 모든 시작 좌표의 [0,1] 범위를
실행 전에 검사하며 범위를 넘는 조건이 있으면 실행을 중단한다.
동일 방향과 norm에서 epsilon만 바꾸는 paired intervention이다.

## 미분식과 사전 측정

갱신식은 `F_i(x)=(1-d)x_i+d sigmoid(z_i)`이며
`z_i=[2(bias_i+drive_i+Σ_j w_ij(2x_j-1))+(s+h)(2x_i-1)]/T`다.
따라서 `J_ij=(1-d)δ_ij+d sigmoid(z_i)(1-sigmoid(z_i))
*[4Σ w_ij+2(s+h)δ_ij]/T`이다. 같은 source/target link는 합산한다.
여기서 d는 damping, s는 self_excitation, h는 inhibition, T는 temperature다.
행은 출력 좌표, 열은 입력 좌표이며 순서는 `e:0,e:1,p:0:0,p:0:1,goal`이다.

각 branch에서 실제 저장된 초기 차이 δ와 대조 대비 한 단계 차이 ΔF를 보존하고
`Jδ`, `||ΔF-Jδ||∞`, 이를 초기 거리와 epsilon²로 나눈 값, 실제/예측 증폭률을 계산한다.
부동소수점 덧셈 때문에 실제 δ와 명목 epsilon 부호 벡터를 따로 기록한다.
명목 방향의 `||Js||∞`와 실제 증폭률 차이가 가장 작은 epsilon의 모든 방향에서
`<=1e-4`이면 해당 anchor의 사전 gain 일치 기준을 충족한다.
이 판정은 유효한 검산의 통과 조건이 아니다. 불일치도 연구 결과로 보존한다.
오차가 epsilon 감소에 따라 줄어드는지와 epsilon² 정규화 오차는 보조 관찰이다.
`1e-14` 이하 오차는 반올림 영향 가능 구간으로 다루며 차수를 확정하지 않는다.
Jacobian의 최대 절대 행합도 보고하되 spectral radius나 장기 안정성으로 해석하지 않는다.

## 검증·출처·실행

spec은 R052 원자료 10개와 R058 출처 6개의 byte hash를 고정한다.
별도 프로세스의 검산기는 원래 program과 두 anchor의 최초 종료·512 tick을 재계산한다.
연구 record의 초기 개입·한 단계·residual·counter·비용을 기존 독립 수식으로 검산한다.
Jacobian은 생산 미분기를 import하지 않고 60자리 Decimal의 exp 미분식으로 대조한다.
허용 수치 오차는 절대·상대 각각 `1e-12`다. 검산 독립성은 수식·프로세스에 한정하며
독립 연구자 감사라고 주장하지 않는다. synthetic central difference와 변조 테스트를 둔다.

`Run-HCR-R061.cmd`: source/spec/출처 동결 → synthetic self-test → 별도 smoke 8개와
검산 → 최종 core regression 1회 → 연구 194개 1회 → 별도 검산 → summary/bundle/ZIP.
smoke는 각 anchor의 control/e4_mmmmm/e5_ppppp/e6_mpmpm이며 연구 증거에 합산하지 않는다.
개발 중 synthetic 검사 결함 수정은 허용한다. 연구 실행 뒤 조건·판정 기준을 바꾸거나
연구를 재실행하지 않는다. 실패 시 로그·traceback·부분 evidence를 보존한다.
자동 재시도와 Git 조작은 실행기에 넣지 않는다. 기본 EXP-30 dispatcher는 유지한다.

범위는 R061 add-on, 새 실행기·EXP-42 문서·index, 신규 evidence다.
core/tests, 과거 source/raw/manifest와 기존 미추적 자료는 보존한다.
필수 검증 뒤 커밋·로컬 main 병합·작업 브랜치 정리·일반 push·원격 반영을 확인한다.
결과 해석은 실행 후 별도 문서이며 frozen source에 소급 편입하지 않는다.

## 비용과 주장 범위

연구 kernel_ticks/group_updates/normalization_ops/signal_transmissions만 단위별로 집계한다.
anchor replay, smoke, 미분·검산은 연구 kernel 비용에 포함하지 않는다.
실제 에너지와 native packet/proof/support/raw decision/adoption은 null이다.
paired deterministic 조건을 독립 표본으로 세지 않는다.
한 단계 국소 선형화 일치는 장기 복원·basin·수학적 attractor·학습된 Circuit이나
LLM 내부·인간 인지·HCC 전체 이론의 직접 검증이 아니다. 새 크기·방향·horizon은 다음 턴이다.
