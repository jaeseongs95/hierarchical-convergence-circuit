# R48 / EXP-94: 이항 관계 4-튜플 결합 보존 대 주변곱 폐포(`projection0/1 -> feasible4 -> 봉인 binding -> consume_t -> query4`) 8토큰·64코드쌍·16-Hamming쌍 코드북 전이 및 809회 6단계 충분조건 분리

[MEDIUM 방향 토론](DELIBERATION.ko.md)에 따라 [R37(`exp-83-joint-tuple`)](../exp-83-joint-tuple/RESULTS.ko.md), [R46(`exp-92-relational-codebook-transfer`)](../exp-92-relational-codebook-transfer/RESULTS.ko.md), [R47(`exp-93-capacity-codebook-transfer`)](../exp-93-capacity-codebook-transfer/RESULTS.ko.md) 사이에 남아 있던 세 가지 구조적 공백을 분리해 검증한다:
1. [R37](../exp-83-joint-tuple/RESULTS.ko.md)은 이항 관계 $C(X,Y)$와 $T(X,Y)$ 위에서 3층 주변곱 재교차 네트워크(`projection0`, `projection1`: `f0..3 -> p00..p11 -> e0..3 -> goal`, 9그룹), 4-튜플 분류기(`feasible4`, 18그룹), 봉인된 `hcr-r37-joint-tuple-v1` `binding`(`eligibility` 4개, `coverage_activation` 1개, `state_sha256`), 그리고 격리 소비기(`consume_t -> query4`, 25그룹)를 정의했으나, namespace당 $4/8$개 토큰(`{0,1,2,3}`: `cnot20` 고정점 집합)만 사용해 $8/64$개 ordered 코드쌍만 노출되었고 불일치 역할 비교의 100%가 Hamming 거리 $d=1$($d=2, 3$ 발생 `0`회, `pair` 입력 Hamming쌍 $4/16$개)에 갇혀 있었다.
2. [R46](../exp-92-relational-codebook-transfer/RESULTS.ko.md)은 3변수 조건부 $Z$ 파이프라인(`R39/R40`)만 검증해 소비기가 $n=2$ 후보(`feasible2`)만 분류했고(`projection0/1`, `feasible4`, `query4` 미포함), 4개 코호트만 사용해 비등거리 코드북에서 $13/16 \sim 14/16$ Hamming쌍과 $24/64$ 코드쌍만 실현되었다. [R47](../exp-93-capacity-codebook-transfer/RESULTS.ko.md)은 단항 AST(`expr0..5`) 파이프라인에서만 `feasible1..4`와 `query1..4`를 검증했다.
3. `R37`의 `native_marginal`은 `projection0/1`의 최종 `goal`이 아니라 **4개 내부 중간 노드 상태 `e0..e3`**을 추출해 `feasible4`에 주입하고, `consume_t`는 봉인된 연속 `binding` 스칼라 5개와 $T(X,Y)$ 소속 스칼라 4개를 결합해 `query4`를 구동한다. 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)이 역할 단계 Hamming 거리 $d \in \{1,2,3\}$을 바꿀 때 연속 `binding['eligibility']`와 `state_sha256`/`binding_sha256`이 실제로 섭동되는데, 이때 `native_joint`(`16`개 서명, `256/256` strict) 대 `native_marginal`(`10`개 폐포 서명, `128/256` full strict, `256/256` 폐포 strict, `128/256` 기권, `0/256` 오확정)의 정보 경계와 비역할 5개 단계(`pair`, `membership`, `projection`, `feasible4`, `query4`)의 수렴 tick이 모두 불변인지 검증한다.

## 1. 112개 이항 관계 원천과 32-Base · 8/8 제한 사상 · 64/64 코드쌍 · 16/16 Hamming쌍 행렬

공개 8토큰 어휘(`amber`, `cobalt`, `jade`, `violet`, `wheat`, `umber`, `teal`, `coral`, 코드 `0..7`)의 서로 다른 모든 순서쌍 $(x, y) \in \{0..7\}^2$ ($x \ne y$, $8 \times 7 = 56$개)에 대해 문맥 관계 원천 `C` 56개(`C_0_1..C_7_6`)와 질의 관계 원천 `T` 56개(`T_0_1..T_7_6`)로 총 **112개 실제 native path 원천**을 생성한다.

`swap01 = [1,0,2,3,4,5,6,7]`의 고정점 부분집합($|S \cap \{0,1\}| = 0$인 15개 4-토큰 부분집합)과 5개 충돌 부분집합($\text{Bad}_5 = \{\{0,1,2,3\}, \{0,1,4,5\}, \{0,2,4,6\}, \{0,2,4,7\}, \{0,2,5,7\}\}$)을 제외한 **50개 유효 4-토큰 부분집합(`300`개 순서 코호트 `(X, Y)`)** 중에서 23-코호트 완전 커버를 포함하는 **32-코호트 스케줄**을 32개 base(`b00..b31`)에 배정하고, 8개 전역 3-bit bijection × 3개 팔(`native_joint`, `native_marginal`, `exact_joint`)을 적용해 **`512`개 native 평가 + `256`개 exact 평가(총 `768` 평가, `12` 배치 × `64` 기록, `448`개 비항등→항등 대응쌍)**를 고정한다:
- **Part I (`b00..b15`, `16`개 base) — `16`개 문맥 마스크(`c_mask = 0..15`) 완전 격자**:
  - `c_mask = 0..15` 전체를 1회씩 배치해 `native_joint`의 **`16/16`개 서로 다른 4-튜플 적격 서명(`normalized_eligible`)**과 `native_marginal`의 **`10/16`개 직사각형 폐포 서명(`{0,1,2,3,4,5,8,10,12,15}`)** 분리를 전수 검증한다.
  - 각 base의 `t_mask`는 `c_mask | t_mask`가 코호트의 4개 토큰(`X` 2개, `Y` 2개)을 모두 덮고, `|C| \in \{0..4\}` 및 `|T| \in \{0..4\}`(`or0..4` 전 항수)와 `native_joint`의 4개 완전 질의 태그(`empty`, `qtrue`, `qfalse`, `mixed`)가 모두 실현되며, Part I의 16개 base에서는 `native_joint`와 `native_marginal`이 최종 `(kind, selected_index, value, reason)`에서 모두 일치하도록 구성한다.
- **Part II (`b16..b23`, `8`개 base) — 대각/반대각 동등 주변곱(`c_mask in {6,9} × t_mask in {6,9} × order in {0,1}`) 완전 반례 격자**:
  - 주변집합이 모두 전체 도메인($X, Y$)으로 동일하지만 튜플 상관관계가 서로 반대인 대각(`9`)·반대각(`6`) 문맥과 질의의 $2 \times 2 \times 2 = 8$개 조합 전체를 검증한다.
  - 8개 base 모두에서 `native_joint`는 `decided`(`qtrue` 4건, `qfalse` 4건)로 정확히 판정하는 반면, `native_marginal`은 `projection0`/`projection1`의 상관 소실로 인해 네 튜플 전체를 허용(`many`)하여 `mixed`(`value=None, reason='abstain_ambiguous', unnecessary_abstention=True, incorrect_assertion=False`)로 기권한다.
- **Part III (`b24..b31`, `8`개 base) — L자형 3-튜플 비직사각형(`c_mask in {7,11,13,14}`) 상관 손실 반례**:
  - 크기가 3인 4개 비직사각형 문맥 `c_mask in {7, 11, 13, 14}`에 대해 만장일치 참(`(c_mask, c_mask, order=0)`: `native_joint` `3:0 -> qtrue` 대 `native_marginal` `3:1 -> mixed`) 4건과 만장일치 거짓(`(c_mask, 15^c_mask, order=1)`: `native_joint` `0:3 -> qfalse` 대 `native_marginal` `1:3 -> mixed`) 4건을 검증한다.
- **전 코호트·전 코드북 완전 Coverage 보장**:
  - **`32/32` 모든 base**에서 활성 4-토큰 집합이 8개 코드북을 **`8/8` 서로 다른 제한 사상(`restricted_map_classes_per_base = [8]`, 무변경 `0/448`짝, 변경 `448/448`짝)**으로 구별한다.
  - **8개 모든 코드북(`8/8`)** 각각이 실제 상위 파이프라인 `role`에서 **`64/64` ordered 3-bit 코드쌍** 전체를 소비하고, `pair`에서 **`16/16` ordered Hamming 거리 쌍(`{0,1,2,3}^2`)** 전체를 소비하며, 32개 base 전체에서 **`56/56` 교차 도메인 토큰쌍**과 112개 원천 전체가 활성 참조된다.

## 2. 6단계 관계형 4-튜플 전이 충분조건 분리 (`64 + 16 + 121 + 32 + 64 + 512 = 809` Settles)

1. **`role` 4개 Hamming 동치류 분해 (`64` settles)**:
   $8 \times 8 = 64$개 ordered 3-bit 입력쌍을 실행해 $d(x,y) \in \{0,1,2,3\}$의 4개 동치류 대표값 $G = \{g_0, g_1, g_2, g_3\}$과 $40,320 \times 64 = 2,580,480$건의 전단사 역할 일치 대조를 검산한다.
2. **`role -> pair` 전수 전이 (`4^2 = 16` settles)**:
   16개 ordered Hamming 거리 쌍 $(d_X, d_Y) \in \{0,1,2,3\}^2$을 전수 실행해 $16 \times 40,320 = 645,120$건의 전단사 동치류 합성이 오답 `0`건임을 확인하고, `pair` 극값 모서리(`pfalse_min`, `pfalse_max`, `ptrue`)를 추출한다.
3. **`pair -> or0..4` 가변 항수 소속 극값 경계 (`1 + 3 + 9 + 27 + 81 = 121` settles)**:
   `pair`의 3점 극값 모서리를 항수 $L \in \{0..4\}$의 `or0..4`에 전수 주입해 121건 모두 부울 disjunction과 일치함을 확인하고, 관계 소속 최악 내부 마진 경계(`[m_false_max, m_true_min]`)를 추출한다.
4. **`or0..4 -> projection0/1` 3층 주변곱 재교차 극값 경계 (`16 + 16 = 32` settles)**:
   `or0..4`의 최악 내부 마진 경계 `{m_false_max, m_true_min}`을 `order=0`(`projection0`)과 `order=1`(`projection1`)의 모든 $2^4 = 16$개 4-튜플 부울 모서리에 주입해 내부 상태 `e0..e3`이 직사각형 주변곱 폐포(각 10개 고유 서명)와 100% 일치함을 확인하고, 투영 최악 내부 마진 경계(`[proj_false_max, proj_true_min]`)를 추출한다.
5. **`feasible4` 팔별(`native_joint` / `native_marginal`) 내부 마진 극값 경계 (`32 + 32 = 64` settles)**:
   `or0..4` 직접 입력 경계(`native_joint` 경로 `32`회)와 `projection0/1` 경유 입력 경계(`native_marginal` 경로 `32`회)를 모든 $2^5 = 32$개 부울 모서리 $(b_0..b_3, \text{complete})$에 각각 주입해 `64/64` 모두 `none`/`unique`/`many`/`incomplete` 판정과 일치함을 확인하고, `feasible4`의 최악 출력 경계(`[elig_false_max, elig_true_min]`, `[cov_false_max, cov_true_min]`)를 추출한다.
6. **`query4` 봉인 소비기 보편 질의 극값 경계 (`2^9 = 512` settles)**:
   모든 $2^9 = 512$개 부울 모서리 $(eb_0..eb_3, tb_0..tb_3, \text{complete})$에서 `e0..e3`을 `{elig_false_max, elig_true_min}`으로, `t0..t3`을 `{m_false_max, m_true_min}`으로, `complete`를 `{cov_false_max, cov_true_min}`으로 구동해 `512/512` 전수 모서리에서 `qtrue`/`qfalse`/`empty`/`mixed`/`incomplete` 판정 보존을 검산한다.

## 3. 비용·자원 상한과 검증 경계

원천 `112` + 6단계 전이 프로브 `809`(`64 + 16 + 121 + 32 + 64 + 512`) + 상위 파이프라인 `32,832`(`native_joint` `16,288` + `native_marginal` `16,544`) = **총 `33,753`회 물리 native settle**(최대 `5,400,480` tick)을 지정 AI Research SSH(`ssh-ai-mcp`)에서 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초, `raw 128MiB` / `cache 128MiB` / `AS 512MiB` 상한으로 1회 실행한다. R47의 `audit` `KeyError` 교훈을 반영해 모든 케이스에 `r37` 필수 11개 키(`namespace` 포함)를 명시하고, `preparation()` 단계에서 768개 무변조 모의 레코드 전수 `audit` 통과 후 `ValueError` 전용 `25`개 합성 변조 거부 스위트를 사전 검증하며, 학습·세계 측정·로컬 native 실행은 `0`회다.
