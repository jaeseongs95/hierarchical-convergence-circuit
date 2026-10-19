# EXP-72 / r26: 입력별 수축률 상계로 warm-start를 선별하기

2026-10-19 KST, 실행 전 고정. 기준 main `a97c2f26f61da2107873e678d622c7bbd2d01443`.

## 비중복 질문과 범위

R24의 exact 전이 반복은 원 수명에서 고정점18회만 남았고, R25의 산술 생략은 결과를 보존했지만 같은 부하에서 약44% 느렸다. 이번에는 그 구현을 다듬지 않고 **입력이 바뀔 때 과거 수렴 state를 초기값으로 써도 될 조건을 현재 입력에서 먼저 판별할 수 있는가**를 묻는다. EXP27의 A→B 상태/관계 전달과 EXP38의 uniform 초기값 의존성이 이미 있으므로 단순 carry나 초기값 sweep을 새 연구로 세지 않는다. 새 개입은 공개 drive에 따른 exact-rational 수축 상계 선별과 그 정책의 실제 native 답·비용 대조다.

세 arm은 매번0.5 초기화하는 `reset`, 같은 stream 직전 stable state를 무조건 쓰는 `carry`, 현재 입력의 수축 상계가 충분히 작을 때만 쓰는 `guarded`다. 모두 원 `hcr.dynamics.settle/tick`을 사용하고 source/controller/history/patience를 바꾸지 않는다. warm state는 결과 cache가 아니라 초기값이며 모든 tick은 실제 native 계산이다. 학습 회로·strength·feedback·World.measure는 사용하지 않는다. 독립 토론 패널을 이번에 새로 수행했다고 주장하지 않는다.

## 수식과 gate

프로그램은 R19의 unchanged lower template(f0,f1,goal), config도 원 R19 전체를 고정한다. 공개 score 두 개로 drive를 evidence_gain×score로 만든 뒤 gate를 계산한다. top_down=True다. (s=\mathrm{self\_excitation}+\mathrm{inhibition}\), (d=\mathrm{damping}\), (T=\mathrm{temperature}\)라 놓으면 이상적인 실수 수식의 target logit은

\[
z_i=\{2(b_i+u_i)+2\sum_j w_{ji}(2x_j-1)+s(2x_i-1)\}/T.
\]

전체 cube (x\in[0,1]^n\)에서 중심 (c_i=2(b_i+u_i)\), 반경 (r_i=2\sum_j|w_{ji}|+s\)다. 0에서 logit 구간까지의 거리는 (a_i=\max(0,|c_i|-r_i)/T\). sigmoid 도함수는 (\sigma'(z)\le\min(1/4,e^{-|z|})\)이고 (a\ge0\)에서 (e^a\ge1+a+a^2/2+a^3/6+a^4/24\)이므로

\[
U_i=\min\{1/4,1/(1+a_i+a_i^2/2+a_i^3/6+a_i^4/24)\}
\]

가 전체 구간의 보수적 도함수 상계다. norm은 (\|v\|_\omega=\max_i|v_i|/\omega_i\), 가중치는 f0=1,f1=1,goal=8로 고정한다. 행별 상계는

\[
q_i=(1-d)+dU_i\{2s+4\sum_j|w_{ji}|\omega_j/\omega_i\}/T,
\quad q=\max_iq_i.
\]

gate는 (q\le19/20\)일 때만 허용한다. goal 가중치8은 원 템플릿의 incoming weight2 두 개와 설정에서 goal 행의 최대 상계를 약0.87625로 만들어19/20보다 작게 두는 실행 전 구조 선택이다. 관측 결과나 threshold 탐색으로 고르지 않는다. 모든 입력 float는 그 저장된 binary64 값을 정확한 유리수로 취급하고 Fraction으로 상계를 계산한다. exp 근삿값이나 부동소수 반올림 여유를 certificate에 사용하지 않는다. 별도 검산식은 구간의 lo/hi와 다항식 역수를 다르게 전개해 대조한다.

이 이상적 실수 map은 cube를 cube로 보내며, 위 bound가1 미만이면 해당 weighted norm에서 contraction인 충분조건이다. 그러나 **native의 반올림된 함수, 유한 max_ticks/patience 종료, margin/readout, bit 동일성을 증명하는 certificate는 아니다.** 큰 bound는 비수축이나 잘못된 입력의 증명이 아니라 선별 미성립이다. 강한 입력에서만 통과해도 그 자체를 native 품질 보존으로 세지 않는다. native 차이는 아래 고정된 실험으로 별도 측정한다.

## 상태 수명과 입력

4stream은 strong/weak×positive-first/negative-first다. 강한 두 입력은 score(1,.8),(.8,.6), 약한 두 입력은(.2,.15),(.15,.1)이다. 각 stream은 같은 부호 두 입력→중립(0,0)→반대 부호 두 입력→중립의6cell이다. 음수-first는 두 부호를 교환한다. 총24개의 순차 target이며 각 arm에서 stream 시작은 cold다. 같은 중립 입력을 여러 과거 상태 뒤에 배치한 것이지 독립 모집단 표본을 추가한 것은 아니다.

arm별 private source는 직전 stable_decision/stable_ambiguous의 state 복사만 보관한다. nonstable이면 폐기한다. program·config·dynamics source SHA·stream·arm binding이 다르면 reset한다. source state의 key/type/유한성/[0,1] 범위를 검사한다. source cell은 과거에 완료한 해당 arm의 기록이어야 하며 다른 arm·stream·미래 결과를 사용하지 않는다. drive 변경은 의도한 개입이고 현재 drive 전체로 gate를 다시 계산한다. gate는 case/arm ID·이후 답·truth를 읽지 않는다. ID는 provenance와 경계 분리에만 쓴다. 외부 observer나 상태 mutation·동시 호출은 지원하지 않는다.

각 cell의 arm 시작 순서는 세 arm을 순환하고 stream별 order_offset도 고정한다. stream마다 별도 worker process로 cache를 폐기한다. 경로·원 source·기억을 수정하거나 더 좋은 결과를 위해 입력 순서를 바꾸지 않는다.

## 판정·검산·비용

일차 질문은 무조건 carry와 guarded가 reset의 종료 status·adopted 값을 보존하며 terminal state의 최대 절대 차이를1e-4 이하로 유지하는가다. 이 tolerance는 정책 비교용이며 scalar trace 검산 허용치1e-15(상대오차0)와 구분한다. reset을 선택한 cell은 전체 kernel record가 reset arm과 타입/float bit까지 동일해야 한다. warm-start는 tick 수와 궤적을 의도적으로 바꾸므로 R25처럼 전체 이력을 같은 것으로 요구하지 않는다. 모든 궤적은 기록된 initial부터 별도 scalar 수식으로 재생돼야 한다.

carry가 답을 바꾸거나 guarded도 보존에 실패하면 유효한 음성 결과다. reset과의 일치는 외부 정답 검증이 아니라 이 기준 실행과의 유한 입력 대조다. 안정 종료를 실제 세계의 정답이나 학습 성능으로 바꾸지 않는다. 현재 구현에 자동 편입하거나 제품 채택하지 않는다.

원 native Cost의 tick/group/signal/normalization과 state read/write 값 수·logical state payload(값당8bytes, metadata/allocator/RSS 제외)를 보존한다. CPU/wall 경계는 현재 drive 구성·gate·source 검사·initial 선택·native 전체 settle와 trace 복사·결과 구성·private cache 갱신을 포함한다. 최초 공통 program/config 준비, raw JSON 저장, imports와 최종 audit는 밖이며 stage 비용으로 별도 남긴다. gate CPU/wall은 전체 안에 포함된 부분이며 더하지 않는다. 각 stream의 실제 prefix K=1..6 비용도 집계한다. 단위가 다른 counter는 합치지 않고 이번 학습 비용은0이다.

cell마다 한 번인 작은 고정 부하이므로 CPU/wall 차이는 관측치이며 통계적 속도 개선으로 주장하지 않는다. gate 비용을 빼거나 좋은 cell만 골라 순이득을 선언하지 않는다. 새로운 조건·재측정·반복 확대는 하지 않는다.

gate/initial/state/Cost/source/order/timing inclusion 변조7종은 정확한 사유로 거부해야 한다. 초기 pure 검사는 수식과 정책 경계만 사용하며 native 연구 계산은 AI Research SSH에서만 한다. CS 조건3개와 의무는 별도 cs artifacts에 실행 전 동결한다. READY와 검증 bundle의 구조/digest 통과를 독립 구현 감사나 native 실행 증거로 바꾸지 않는다.

## 상한·실패·출처

4×6×3=72 native settle, 각 max_ticks160으로 최대11,520 native tick이다. 학습/World.measure0, worker1/retry0, 전체600초·stage60초다. 기존 R22 bounded runner로 준비→4stream→audit6단계를 실행한다. 부모 AS512MiB/개별파일32MiB, child AS512MiB/개별파일16MiB, stage 종료 raw128MiB soft 검사를 사용한다. hard disk quota·peak RSS·모든 child 개별 getrlimit·OS 실패 봉인을 보증하지 않는다. 실패면 bounded 자료를 남기고 중단하며 재실행하지 않는다.

새 ZIP/source/spec/design/input hash를 실행 전에 고정하고 새 전용 폴더와 새 R26 소유자 요청만 사용한다. R25 승인을 재사용하지 않는다. 송신 manifest와 실제 수신 자료를 구분하고 원격 source 경로가 가려지면 복원하지 않는다. 모든 source와 과거 evidence는 불변이다. 이번은 R19/25의 과거 실패·한계를 바꾸는 재실행이 아니다. 결과와 실제 수신/검증 범위는 실행 후 별도 기록한다.
