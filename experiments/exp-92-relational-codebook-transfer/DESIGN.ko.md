# R46 / EXP-92: 다변수 관계형 봉인 상태 파이프라인의 8토큰·16 Hamming쌍 코드북 전이와 6단계 충분조건 분리

[MEDIUM 방향 토론](DELIBERATION.ko.md)에 따라 R45(`exp-91-codebook-transfer-coverage`) 이후 남아 있던 구조적 간극—단일 변수 unary AST 파이프라인(`r35/r36`, 깊이 3단계)에서 검증된 8토큰 코드북 불변성과 단계별 전이가 **다변수 관계형 봉인 상태 생산–소비 파이프라인(`r39/r40`, 깊이 6단계)**에서도 성립하는지—를 검증한다. R37~R43의 모든 관계형 실험은 8토큰 어휘 중 6개(`0..5`)만 사용하고 보조 슬롯 `6, 7`을 소비하지 않았으며, 도메인 내부 XOR이 `1`(`0^1=2^3=4^5=1`)로 고정되어 불일치 역할 비교의 100%가 Hamming 거리 $d=1$에서만 일어났고 `pair` 게이트는 가능한 16개 $(d_1, d_2) \in \{0,1,2,3\}^2$ 조합 중 4개($\{0,1\}^2$)만 경험했다. 또한 `r39`/`r40`에서는 생산자(`produce`)가 연속 스칼라 배열(`slices` 8개, `factors` 12개, `xy/z` 6개)을 `payload_sha256`으로 봉인해 어휘·도메인 접근이 없는 소비자(`consume`)에게 전달하므로, 비등거리 코드북이 $d \in \{1,2,3\}$을 바꾸면 봉인된 연속 `payload` 수치와 `payload_sha256` 자체가 코드북마다 달라진다.

## 1. 48개 원천과 대칭 4-Cohort 8토큰·16 Hamming쌍 관계형 행렬

공개 8토큰 어휘(`amber`, `cobalt`, `jade`, `violet`, `wheat`, `umber`, `teal`, `coral`, 코드 `0..7`) 전체에 대해 생략 토큰 쌍이 `{0..7}`을 서로소 분할하는 **대칭 4-cohort 도메인 구조**를 고정한다.
- **Cohort 0** (생략 `{5, 6}`): `X=[0,2]` ($\Delta=2$), `Y=[1,4]` ($\Delta=5$), `Z=[3,7]` ($\Delta=4$) $\implies d_{\text{id}}=(1,2,1)$
- **Cohort 1** (생략 `{3, 4}`): `X=[0,6]` ($\Delta=6$), `Y=[2,5]` ($\Delta=7$), `Z=[1,7]` ($\Delta=6$) $\implies d_{\text{id}}=(2,3,2)$
- **Cohort 2** (생략 `{1, 2}`): `X=[0,7]` ($\Delta=7$), `Y=[5,6]` ($\Delta=3$), `Z=[3,4]` ($\Delta=7$) $\implies d_{\text{id}}=(3,2,3)$
- **Cohort 3** (생략 `{0, 7}`): `X=[2,3]` ($\Delta=1$), `Y=[1,6]` ($\Delta=7$), `Z=[4,5]` ($\Delta=1$) $\implies d_{\text{id}}=(1,3,1)$

각 cohort의 `R(X×Y)`, `S(Y×Z)`, `U(X×Z)` 완전 테이블(각 4개, cohort당 12개)로 총 **48개 실제 native path 원천**(`c0_R_0..c3_U_3`)을 생성한다. 8개 판별 마스크 삼중쌍 `(9,9,9), (9,6,6), (9,5,5), (9,10,10), (9,9,6), (1,1,1), (1,3,3), (6,9,6)` × 2개 `order`(`0, 1`, `cohort = (2 * m_idx + order) % 4`)로 **16개 base**를 구성하고, 8개 전역 3-bit bijection(`identity`, `bit_reverse`, `xor7`, `cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)을 적용해 **128개 mapped context**를 만든다. 각 context마다 `native_joint`(`r39`), `native_factor`(`r40`), `native_compact`(`r39`), `exact_joint` 4개 arm과 5개 공개 질의(`conditional slot 0..3` + `unary None`)를 실행해 **총 512개 평가(384 native + 128 exact) 및 2,560개 질의 응답(1,920 native + 640 exact)**을 검산한다.
- 8개 토큰 전체가 정확히 3/4 cohort(`24`개 도메인 슬롯 중 각 `3`개)에 균등 참여하며, 모든 cohort에서 `0`과 `1`이 서로 다른 도메인에 분리되어 **16개 모든 base에서 제한 대응 수가 정확히 8개(`restricted_map_classes_per_base == [8]`, 무변경 0/336 native 쌍)**다.
- 7개 비영 XOR 차분 $\Delta \in \{1..7\}$이 모두 포함되어 **8개 모든 코드북이 실제 파이프라인에서 $d \in \{0,1,2,3\}$ 4개 동치류를 모두 소비**하고, `identity`/`bit_reverse`/`xor7` 및 행렬 전체에서 상위 파이프라인 `pair` 단계가 **가능한 모든 16개 ordered Hamming 거리 쌍 $(d_1, d_2) \in \{0,1,2,3\}^2$**을 실제로 실현한다.
- 기존 `r37/r38/r39/r40` 실행기는 수정하지 않고 그대로 호출하며, `order=1`에서 `r39`(`slot = 3-i`)와 `r40`(`slot = i`)의 질의 슬롯 정렬만 외부 입력에서 맞춘다.

## 2. 6단계 연속 스칼라 전이 프로브 (`569` Settles)와 봉인 상태 불변성 검증

1. **`role` 4개 Hamming 동치류 (`64` settles) 및 `role -> pair` 전수 전이 (`16` settles)**:
   64개 ordered 3-bit 입력쌍의 4개 동치류 $G_{\text{role}} = \{g_0, g_1, g_2, g_3\}$를 확인하고, `pair`(`['and', 0, 1]`)가 받을 수 있는 모든 $4^2 = 16$개 ordered Hamming 쌍 $(d_0, d_1) \in \{0,1,2,3\}^2$을 전수 실행해 $8! = 40,320$개 모든 bijection에 대한 `role -> pair` 전이(`64 × 40,320 = 2,580,480` 대응)와 극값 대표점 $P_{\text{env}} = \{p_{\text{False}}^{\min}, p_{\text{False}}^{\max}, p_{0,0}\}$을 추출한다.
2. **`or0..4` (`121` settles) 및 `triple` (`64` settles) 극값 전이**:
   `or0..4`(`L = 0..4`)에 대해 $\sum_{L=0}^4 3^L = 1 + 3 + 9 + 27 + 81 = 121$개 조합을 실행해 봉인 `factor`(`membership`) 극값 구간 $M_{\text{env}} = \{m_{\text{False}}^{\min}, m_{\text{False}}^{\max}, m_{\text{True}}^{\min}, m_{\text{True}}^{\max}\}$을 구하고, `triple`에 대해 $4^3 = 64$개 조합을 실행해 봉인 `slice` 극값 구간 $S_{\text{env}} = \{s_{\text{False}}^{\min}, s_{\text{False}}^{\max}, s_{\text{True}}^{\min}, s_{\text{True}}^{\max}\}$을 검증한다.
3. **`projection` (`or2` 16 + `or4` 256 = `272` settles) 및 `consume` (`pair` 16 + `feasible2` 16 = `32` settles)**:
   $S_{\text{env}}$ 위에서 `or2`($4^2 = 16$회)와 `or4`($4^4 = 256$회)를 실행해 봉인 `xy`/`z` 및 unary 질의 입력 극값 구간을 구하고, 소비자 `pair`($4^2 = 16$회)와 최종 `feasible2`($4^2 = 16$회) 극값 경계를 검증한다.
4. **봉인 연속 `payload` 섭동 하 비역할 단계 tick 불변 및 정보 경계 보존**:
   비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)에서 봉인된 연속 `payload`와 `payload_sha256`이 실제로 변함을 확인하되, 각 평가 내 5개 질의 전후 봉인 불변성, 등거리 코드북(`bit_reverse`, `xor7`)의 `payload_sha256` 완전 일치, 8개 모든 코드북 간 비역할 단계(`pair`, `membership`, `triple`, `projection`, `query_input`, `feasible`) tick 차이 `0`, `native_joint`·`native_factor`의 `640/640` 완전 정합, `native_compact`의 주변곱 오라클 `640/640` 정합 및 전체 결합 오라클 대비 `544/640` 정합(`96/640` 조건부 `unique -> many` 보류, 허위 `unique` `0`건) 보존을 검산한다.

## 3. 비용·자원 상한과 사전 변조 검증

원천 `48` + 6단계 전이 프로브 `569` + 상위 파이프라인 `38,272`(`native_joint` `11,904` + `native_factor` `12,928` + `native_compact` `13,440`) = **총 `38,889`회 물리 native settle**(최대 `6,222,240` tick)을 지정 AI Research SSH(`ssh-ai-mcp`)에서 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초, `raw 128MiB` / `cache 128MiB` / `AS 512MiB` 상한으로 1회 실행한다. `preparation` 단계에서 Boolean stub 기반 모의 번들로 `verify.py`의 22개 전체 합성 변조 거부 스위트를 사전 실행해 통과시킨다.
