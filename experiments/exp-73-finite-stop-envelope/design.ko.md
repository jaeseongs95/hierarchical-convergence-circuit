# EXP-73 / R27: 관측된 native 유한 종료의 오차 경계와 gate 손익분기

기준 main `bad0c94e7c84f2018363756de898c577b5dcff27`. 실행 전에 고정한다.

## 질문과 비중복 범위

R26은 current-input exact-rational contraction 선별로 품질24/24와 tick8.20% 감소를 관측했지만 gate 포함 CPU가70.31% 증가해 미채택했다. 이상적인 실수 map의 수축만으로 native 반올림·유한 종료의 답 보존을 보장하지 못했다. 기존 EXP62 계열에도 잔차/수축 기반 종료·거리 분석이 있으므로 수축 정리나 단순 초기값 실험을 새 연구로 세지 않는다.

새 질문은 **R26의 실제 warm/reset 유한 종료 기록에서 마지막 native step의 점별 수치 결함을 엄밀히 둘러싸면, 품질 허용 오차와 readout을 인증할 수 있는가**다. 다른 질문은 **저장된 R26 비용에서 gate만 바꿔 이길 수 있는 비용 예산이 얼마인가**다. 반복 실행이나 더 큰 서버보다 이 제한 분석을 먼저 한다. 새 독립 토론 패널을 수행했다고 주장하지 않는다.

이번 인증은 완료된 기록에 대한 사후 판정이다. 실행 전 채택 gate, native 함수 전체의 오차 상계 또는 미관측 입력의 품질 보장으로 사용하지 않는다. 원 source·controller·기억·과거 run은 불변이다. 신규 native 추론·학습·World.measure·성능 benchmark는 모두0이다.

## 입력과 수명

R26의 hash 고정된4stream×6입력×3arm=72record와 reset 대비 carry/guarded의48pair 전체를 사용한다. 일부 좋은 입력만 선택하지 않는다. 같은 target pair는 동일 program/config/drives이며, 모든 원 궤적·source provenance·종료·Cost를 기존 R26 별도 scalar 검산으로 확인한다. 원자료4stream/preparation/result/summary와 spec 및 source hash를 실행 전에 묶는다.

연산은 Python 표준 라이브러리 Fraction과 고정 크기 dyadic 격자를 사용한다. 프로그램은 R26의 lower template, config·norm 가중치(1,1,8), 품질 허용 오차1e-4를 유지한다. global q는 원 R26 이상적 map의 유리수 도함수 상계이며 별도 구간 전개와 대조한다. q>=1은 이번 인증 불가이지 비수축·비수렴·오답의 증명이 아니다.

## 마지막 native step의 점별 결함

관측 마지막 step의 입력을 p, native 출력/종료 상태를 y라 놓는다. p는 penultimate tick state이며 tick이1개면 기록 initial이다. 저장된 binary64 입력·상수는 정확한 유리수로 취급한다. 이상적인 실수 map F의 logit을 원 식과 별도 positive/negative 식 두 방식으로 계산한다.

sigmoid에 필요한 exp(a), a=|z|는0<=a<=16에서 인증한다. 현재 고정 program/config와 drive 범위의 cube logit 절댓값은 최대9.15이므로 이 cap 안이다. N=128, 격자2^-192를 실행 전에 고정한다. 양의 Taylor 항의 하·상한을 각 곱셈/나눗셈마다 격자 바깥쪽으로 반올림하고 합산한다. 마지막 상한 항을 t_N^+라 하면 양의 tail은

    t_N^+ * a/(N+1) / (1-a/(N+2))

이하다. 따라서 합의 하한과 합+tail의 상한이 exp(a)를 둘러싼다. a=0은 exp=1 정확값이다. sigmoid의 단조 유리함수와 damping을 통해 각 F_i(p)의 구간[L_i,U_i]를 얻는다. 이는 플랫폼 math.exp의 정확 반올림을 가정하지 않는다.

별도 verifier는 항마다 dyadic 반올림하지 않고 exact Fraction Taylor 합과 tail을 계산한다. 제안된 exp 구간이 이 sandwich를 포함하고 폭<=1e-40이며 끝점이 격자 위인지 확인한다. logit·sigmoid·damping도 별도 전개로 재구성한다. 잘못된 cap·interval·q·radius는 거부한다.

    eta = max_i max(|y_i-L_i|,|y_i-U_i|)/omega_i
    r   = max_i |y_i-p_i|/omega_i

eta는 **이 기록의 이 점에서만** ||y-F(p)||_omega를 둘러싼다. float epsilon을 가정하거나 0으로 버리지 않는다. native의 모든 입력/다음 step에 동일하게 적용되는 roundoff 상계가 아니다.

## 유한 terminal과 pair 인증

q<1인 전역 contraction은 cube의 유일한 실수 고정점 x*를 갖는다. 삼각 부등식으로

    ||y-x*|| <= ||y-F(p)|| + q||p-y|| + q||y-x*||
    rho = (eta+q*r)/(1-q)

이므로 기록된 y와 공통 x*의 거리가 rho 이하다. 서로 다른 tick 수에서 끝난 reset/candidate 두 기록에도 각각 적용한다. 두 상태의 모든 성분 차이는 max(omega)*(rho_reset+rho_candidate) 이하다.

먼저 두 **전체 kernel record**가 타입·float bit까지 같으면 EXACT_RECORD_IDENTITY로 인증한다. 이는 reset 정책 선택과 동의어가 아니다. warm 초기값이 우연히 reset과 같아진 기록도 포함할 수 있다.

나머지는 두 q<1 경계가 있고 위 pair 차이 상계가1e-4 이하이며, 검산된 두 native 종료 status가 stable_decision일 때만 readout을 추가 검사한다. reset goal을 중심으로 omega_goal*(rho_reset+max(rho_reset,rho_candidate))를 확장하면 두 terminal goal을 함께 포함하는 구간이다. 이 구간 전체가 (1+margin_threshold)/2 이상 또는 (1-margin_threshold)/2 이하면 같은 부호·충분한 margin을 인증한다. 실제 adopted 값과도 검산한다. 그렇지 않으면 UNPROVEN이며 관측 품질 불일치와 구별한다.

종료 status는 저장된 controller replay로 확인한 관측 사실이다. 새로운 초기값의 미래 종료 status를 이 인증식이 예측한다는 주장이 아니다. 원자료의 실제 pair 차이·답·status를 별도로 계산해 false certification이0인지 확인한다. 기록 범위를 벗어난 자동 채택은 하지 않는다.

## gate 손익분기와 비용 경계

R26의 reset 비용R, guarded의 gate 포함 비용C, 그 안의 gate 비용G를 그대로 사용한다. 전역 및4stream의 실제 prefix K=1..6에 대해 CPU/wall 각각 계산한다. 서로 다른 단위는 합치지 않는다.

    D = R-(C-G)
    가정한 다른 비용이 고정일 때만, 새 gate 비용 G_new < D 이면 순이득

D<=0이면 gate를0으로 만들어도 이 가정에서 이길 수 없다. D>0이면 허용 gate 예산D와 필요한 gate 감소율1-D/G를 기록한다. 가상으로 같은 G를 유효하게 m회 분담할 수 있다고 가정하면 m>G/D이지만, 실제 certificate 재사용 타당성·동일 입력 반복·컴파일/저장/조회 비용을 확인한 것은 아니다. 이 수치를 실제 손익분기 실험이나 최적화 성능으로 표현하지 않는다. 기존 한 번의 작은 시간 관측은 잡음과 순서 효과가 있으며 통계 주장을 하지 않는다.

이번 사후 인증의 준비·검산·봉인 시간은 runner의 별도 분석 비용이다. 이를 미래 gate 비용으로 대체하거나 R26 실행의 성능 수치에 섞지 않는다. 학습 비용은 이번에도0이며 학습이 있는 방식과의 총비용 비교로 확대하지 않는다.

## 검사·상한·실패

순수 Taylor/격자/음수 cap/결함 포함/미인증/identity/비용 부호 검사와 기존 R26 순수 경계 검사를 준비 단계에 수행한다. 원격에서4stream을 분석하고 audit에서 interval/q/radius/source/order/scope/pair/cost 변조8종을 의도한 사유로 거부한다. source·입력·검증 근거·CS의무3개를 고정한다.

기존 R22 runner로 준비→4stream→audit의6stage, 총600초·단계60초·worker1/retry0을 사용한다. 부모 AS512MiB/개별파일32MiB, child AS512MiB/개별파일16MiB, stage 종료 raw128MiB soft 검사다. hard disk quota·peak RSS·모든 OS 실패의 봉인 보증은 아니다. 실패하면 bounded 자료를 남기고 중단하며 새 실행으로 덮지 않는다.

새 R27 전용 폴더·ZIP·소유자 요청만 사용하고 R26 실행 승인을 새 명령 승인으로 해석하지 않는다. 수신 JSON의 hash 검증 범위와 adapter/출처 한계를 분리한다. CS/범위 CLI 통과는 독립 수학 감사나 실행 attestation이 아니다. 결과 후 입력·수식·허용치·반복 수를 바꾸거나 더 좋은 결과를 위해 재실행하지 않는다.
