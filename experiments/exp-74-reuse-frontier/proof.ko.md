# Boolean 판정의 지원 영역과 동치 유도

지원 영역은 frozen R26 lower program·전체 Config·norm weights·원 Fraction 정책·별도 검산기·순서 보존 program 생성 코드·native/model/codec·compiler source SHA, `top_down=True`, 실제 binary64 drive f0/f1 각각 [-4,4], goal=0이다. 임의 설정용 compiler가 아니다. 지원 밖은 명시적으로 거부한다. signed zero는 허용한다. source는 실행 manifest와 매 lifecycle profile에 결속한다. 실행 중 객체 변경·외부 callback·공유 context는 제공하지 않는다.

원 수식의 저장 float 계수는 Fraction으로 정확하게 올린다. d=damping, T=temperature, s=self_excitation+inhibition, omega=norm이라 하자. 각 행의 상계는

`q_i = 1-d + d/T · min(1/4, 1/P(a_i)) · (2s + 4 Σ |w_ji| omega_j/omega_i)`

`a_i=max(0, 2|bias_i+drive_i| - 2Σ|w_ji| - s)/T`, `P(a)=1+a+a²/2+a³/6+a⁴/24`다.

f0/f1은 bias=0, 같은 incoming weight와 norm이므로 같은 단변수 함수 q(|u|)를 갖는다. d>0, T>0, s>=0, omega>0이고 모든 incoming 절댓값이 비음수다. 따라서 |u|가 증가하면 a가 비감소하고 양의 계수 다항식 P는 비감소한다. 역수와 min(1/4,.)는 비증가하며 비음수 행 계수와 합성한 q도 비증가한다. goal의 drive는 0으로 고정되고 입력 상태의 전체 cube 경계를 사용하는 행 상계이므로 실제 f0/f1 drive와 무관하다. 별도 유리수 검산의 goal q는 약 0.87625로 19/20보다 작다.

따라서 전체 max(q_i)<=19/20은 f0/f1 각각의 동일한 단변수 predicate로 환원된다. 양의 유한 IEEE754 binary64 [0,4]는 unsigned bit pattern 순서와 수치 순서가 같다. 0은 거부되고 4는 허용된다. compiler는 이 bit 구간에서 최대 63회 이분 탐색하여 최소 허용 수 t를 찾는다. 별도 검산기는 expanded polynomial `24/(24+24a+12a²+4a³+a⁴)`와 행별 합을 사용해 t 허용·직전 float 거부·인접 bit를 확인한다. 단조성과 인접성 때문에 전체 binary64 구간에서 허용집합은 정확히 [t,4]의 float들이다. 절댓값 대칭으로 음수까지, 0의 원 판정으로 ±0까지 연결된다. 이는 경계 표본 일치만으로 전영역 동치를 추정하는 절차가 아니다.

순수 준비 검사에서 얻은 t는 `0x1.f5e1e8e850962p+0`, predecessor는 `0x1.f5e1e8e850961p+0`이다. 이 값은 runtime 코드에 하드코딩하지 않는다. 매 lifecycle source에서 다시 탐색·검증한다. 100개 경계 교차점과 seed 고정 64개 bit-order 진단점, 임계값 ±1ULP·엄격부등호·출처/설정/순서·영역/유한성·invalid source 부정대조는 구현 오류 검출용이다. 이 표본 수가 수학적 유도를 대체하지 않는다.

동일 Boolean이 원 choose에 들어가고 이전 cache가 같으면 선택과 initial이 같다. 빈 cache에서 시작하여 동일 native 함수, 동일 입력, 동일 순서와 상태 저장 규칙을 적용하면 다음 cache도 같다. 6입력 순서에 대한 귀납으로 원 guarded와 compiled의 kernel 및 상태 전이가 같다. native 계산 자체의 새로운 실수 오차·종료 보장을 얻는 것은 아니다. 원 guarded의 미래 reset 품질을 증명하지 않으며 full gate 객체나 시간 필드의 동일성을 주장하지 않는다.

검산은 원 Fraction 코드와 다른 다항식 전개를 재사용하며 작성자가 직접 연결했다. 구현자와 분리된 수학/구현 감사 완료를 뜻하지 않는다. HIGH 패널의 독립성은 방향 판정에 적용된다.
