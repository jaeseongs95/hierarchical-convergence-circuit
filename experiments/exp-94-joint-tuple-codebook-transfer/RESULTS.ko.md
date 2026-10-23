# R48 / EXP-94: 고정 8토큰 2변수 결합-튜플 대 주변곱-폐포 관계형 생산-소비 파이프라인 및 6단계 코드북 전이에서 의미 불변성 채택

[R47 후속 방향 숙의](DELIBERATION.ko.md)에 따라 2변수 4-튜플 관계형 생산-소비 파이프라인(`R37`: `role -> pair -> or0..4 -> [projection0/1] -> feasible4 -> hcr-r37-joint-tuple-v1 binding -> consume_t -> query4`)에서 8토큰(`0..7`)·64개 ordered 코드쌍·16개 ordered Hamming쌍(`{0,1,2,3}^2`)·56개 교차 도메인 사실쌍 전수 커버리지, `native_joint`(16개 결합 적격 서명) 대 `native_marginal`(10개 주변곱 폐포 서명 및 대각/L자형 상관 소실 `mixed` 기권) 정보 경계, 그리고 8개 3비트 코드북·6단계 연속 전이 프로브(`809`회 settle)를 고정해 AI Research SSH에서 1회 실행했다. **`native_joint` 256조건·`native_marginal` 256조건·`exact_joint` 256조건(총 768평가)과 448개 non-identity→identity 의미 대응을 검산했다. 전체 단계의 유한 의미 보존 및 6단계 전이 판정은 `True`다.** 전체 파이프라인 40,320개 전수 실행이나 `64^n` 전체 곱집합 열거, 학습된 코드북·학습 효율·H03 구조 재사용의 증거는 아니다.

## 질문과 고정된 개입

[R37](../exp-83-joint-tuple/RESULTS.ko.md), [R46](../exp-92-relational-codebook-transfer/RESULTS.ko.md), [R47](../exp-93-capacity-codebook-transfer/RESULTS.ko.md)을 거치며 다음 세 가지 구조적 공백이 남아 있었다:
1. [R37](../exp-83-joint-tuple/RESULTS.ko.md)은 `X × Y` 4-튜플 결합 상태(`native_joint`)와 주변곱 폐포(`native_marginal`)를 비교했으나, 각 namespace에서 8개 토큰 중 4개(`{0,1,2,3}` 또는 `{4,5,6,7}`)만 사용하고 변수 내부 고정 쌍(`0^1 = 2^3 = 4^5 = 6^7 = 1`)만 비교하여 불일치 역할 비교의 **100%가 Hamming 거리 `d=1`에만 갇혀 있었다**(`d=2, 3`은 `0`회, 64개 코드쌍 중 8개, 16개 Hamming쌍 중 `{0,1}^2` 4개만 발생, `(0, 1, 2, 3)`에서 `cnot20 == identity` 축퇴).
2. [R46](../exp-92-relational-codebook-transfer/RESULTS.ko.md)은 3변수 관계형 파이프라인(`r39/r40`)의 코드북 전이를 검증했으나 소비기가 **`n=2` `Z` 후보(`feasible2`)만 분류**하여 4-튜플 경쟁 분류기(`feasible4`)나 4-튜플 보편 질의기(`query4`), 그리고 3층 주변곱 재교차 커널(`projection0/1`: `f0..3 -> p00,p01,p10,p11 -> e0..3 -> goal`)을 포함하지 않았다.
3. [R47](../exp-93-capacity-codebook-transfer/RESULTS.ko.md)은 `feasible1..4`와 `query1..4`를 단항 AST(`expr0..5`) 위에서만 검증하여, 이항 관계 `C(X,Y)`와 `T(X,Y)`에서 `role -> pair -> or0..4 -> projection0/1 -> feasible4 -> 봉인된 hcr-r37-joint-tuple-v1 binding -> 격리 소비기 consume_t -> query4`로 이어지는 관계형 4-튜플 파이프라인과 주변곱 상관 소실 경계는 한 번도 검증되지 않았다.

이번 R48은 원래 `R37` Program 생성기·Config·initial 0.5·guard·controller·history·Cost와 `execute` 경로를 전혀 수정하지 않고:
1. 112개 원천(`C_0_1..C_7_6` 56개 + `T_0_1..T_7_6` 56개) 위에서 **32개 base 조건**(Part I `b00..b15` 16개: `c_mask = 0..15` 완전 격자, `16/16` 결합 서명 대 `10/16` 주변곱 폐포 서명 분리 및 두 팔 합의 + Part II `b16..b23` 8개: `c_mask ∈ {6,9} × t_mask ∈ {6,9} × order ∈ {0,1}` 대각/반대각 동등 주변곱 반례 완전 격자 + Part III `b24..b31` 8개: `c_mask ∈ {7,11,13,14}` L자형 3-튜플 비직사각형 상관 소실 반례) × 8개 코드북 × 3개 팔 = **768개 평가(`32,832`회 상위 settle)**를 구성했다. 32개 모든 base 조건이 8개 코드북에서 **8/8 서로 다른 제한 사상(`restricted_map_classes_per_base = [8]`, 무변경 `0/224` 케이스·`0/448` 수치 팔, 변경 `224/224` 케이스·`448/448` 수치 팔)**을 유도하고, 각 코드북이 **64/64 ordered 코드쌍**, **16/16 ordered Hamming쌍(`{0,1,2,3}^2`)**, **56/56 교차 도메인 사실쌍**을 실제 파이프라인에서 100% 소비하게 했다.
2. 직접 `role`(64회)과 전수 `pair`(16회) 전이 위에서 `or0..4`(121회), `projection0/1`(32회), `feasible4`(64회: `or0..4` 직접 경로 32회 + `projection0/1` 경유 경로 32회), `query4`(512회) 최악 내부 마진(`[false_max, true_min]`) 극값 모서리 전이(`809`회 settle)를 분리해 측정했다. 계약과 입력은 [설계](DESIGN.ko.md), [동결 spec](frozen_spec.json), [방향 판정 기록](decision-record.json)에 있다.

## 팔(`arm`)별 및 코드북별 실제 파이프라인 결과

| 팔(`arm`) | 평가 수 | 전체 진리 strict | 개입(폐포) strict | 결합 적격 튜플 | 개입 적격 튜플 | Part I 고유 서명 | Part II 기권 | Part III 기권 | 오확정 | 최종 `query4` 태그 분포 | 상위 settle | 상위 tick |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| `exact_joint` | 256 | 256/256 | 256/256 | 1024/1024 | 1024/1024 | 16/16 | 0/64 | 0/64 | 0 | `{"empty": 8, "mixed": 56, "qfalse": 96, "qtrue": 96}` | 0 | 0 |
| `native_joint` | 256 | 256/256 | 256/256 | 1024/1024 | 1024/1024 | 16/16 | 0/64 | 0/64 | 0 | `{"empty": 8, "mixed": 56, "qfalse": 96, "qtrue": 96}` | 16,288 | 492,672 |
| `native_marginal` | 256 | 128/256 | 256/256 | 768/1024 | 1024/1024 | 10/16 | 64/64 | 64/64 | 0 | `{"empty": 8, "mixed": 184, "qfalse": 32, "qtrue": 32}` | 16,544 | 499,736 |

| 코드북 | 전체 진리 (`joint+marg`) | 개입 strict (`joint+marg`) | 역할(`role`) | 쌍(`pair`) | 소속(`or0..4`) | 주변곱(`proj`) | 상위 tick (`role/pair/or/proj/feas/query`) | 코드쌍 | Hamming쌍 | 교차 사실쌍 | 이종 비영 Hamming쌍 | 팔당 역할 Hamming 거리 분포 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `bit_reverse` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 124,081 (75,692/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 73/572 | `{"0": 572, "1": 218, "2": 292, "3": 62}` |
| `cnot01` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 124,169 (75,780/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 73/572 | `{"0": 572, "1": 274, "2": 230, "3": 68}` |
| `cnot12` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 123,829 (75,440/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 74/572 | `{"0": 572, "1": 240, "2": 196, "3": 136}` |
| `cnot20` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 123,969 (75,580/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 75/572 | `{"0": 572, "1": 214, "2": 270, "3": 88}` |
| `cnot_chain` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 124,105 (75,716/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 79/572 | `{"0": 572, "1": 266, "2": 226, "3": 80}` |
| `identity` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 124,081 (75,692/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 73/572 | `{"0": 572, "1": 218, "2": 292, "3": 62}` |
| `swap01` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 124,093 (75,704/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 96/572 | `{"0": 572, "1": 264, "2": 226, "3": 82}` |
| `xor7` | 48/64 | 64/64 | 2288/2288 | 1144/1144 | 512/512 | 128/128 | 124,081 (75,692/29,744/13,710/947/1,938/2,050) | 64/64 | 16/16 | 56/56 | 73/572 | `{"0": 572, "1": 218, "2": 292, "3": 62}` |

1. **`native_joint` 대 `native_marginal` 정보 경계의 8코드북 완전 보존 및 448짝 의미 불변**:
   - `native_joint`(256조건)와 `exact_joint`(256조건)는 Part I(128조건), Part II(64조건), Part III(64조건) 전체에서 **256/256(100%)** 전체 진리 정확도와 **1,024/1,024(100%)** 4-튜플 적격 판정 정확도를 달성했으며, Part I(`c_mask = 0..15`)에서 **16/16개 서로 다른 결합 적격 서명**과 상위 파이프라인의 4개 완결 질의 태그(`empty` 8, `qtrue` 112, `qfalse` 104, `mixed` 32)를 모두 실현했다.
   - `native_marginal`(256조건)은 주변곱 폐포 오라클(`closure=True`) 대비 **256/256(100%)** 개입 정확도와 **1,024/1,024(100%)** 폐포 적격 정확도를 달성했고, Part I에서 16개 결합 서명이 정확히 **10/16개 직사각형 폐포 서명**으로 축약되면서도 Part I 128조건 전체에서 `native_joint`와 최종 판정이 일치(`128/128`)했다. 반면 Part II 대각/반대각 반례(`c_mask ∈ {6,9} × t_mask ∈ {6,9}`, 64조건)와 Part III L자형 3-튜플 반례(`c_mask ∈ {7,11,13,14}`, 64조건)에서는 `native_joint`가 각각 `qtrue` 32건·`qfalse` 32건을 확정하는 동안 `native_marginal`이 상관 소실로 인해 **64/64 + 64/64 = 128/128건 모두 `mixed`(`abstain_ambiguous`)로 안전하게 기권**하고 **오확정(`incorrect_assertion`)은 0건**이었다.
   - 32개 base × 2개 수치 팔(`native_joint`, `native_marginal`) × 7개 비항등 코드북 = **448개 대응 조건** 전체에서 비항등 코드북은 `identity` 기준선과 `kind`, `tag`, `normalized_selected`, `normalized_eligible`, `value`, `reason`, `strict_correct`, `intervention_strict_correct`, `unnecessary_abstention`, `incorrect_assertion`을 **448/448(100%)** 그대로 보존했다.
2. **등거리 대 비등거리 연속 봉인 바인딩(`state_sha256`, `binding_sha256`) 변동의 정량 분리 및 비역할 5단계 tick 불변성**:
   - 등거리 코드북(`bit_reverse`, `xor7`, 128쌍)에서는 봉인된 `hcr-r37-joint-tuple-v1` 바인딩의 연속 스칼라(`eligibility[0..3]`, `coverage_activation`) 최대 절대 차이가 `0.000e+00`였고 **128/128쌍(`128/128`)** 모두가 `state_sha256`과 소비기 `binding_sha256`까지 동일했다.
   - 비등거리 코드북(`cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`, 320쌍)에서는 Hamming 거리 재배치로 인해 **`220/320`쌍**에서 `state_sha256`과 `binding_sha256`이 실제로 변했고 연속 바인딩 스칼라가 최대 `4.221068e-12` 변했으나, 격리 소비기 `consume_t`와 `query4`의 최종 의미 판정은 단 1건도 바뀌지 않았다.
   - 코드북 간 총 상위 tick 차이(`123,829`~`124,169` tick)는 **100% `role_ticks`(`75,440`~`75,780` tick)에만 국한**되었으며, `pair_ticks`(`29,744`), `membership_ticks`(`13,710`), `projection_ticks`(`947`), `feasible_ticks`(`1,938`), `query_ticks`(`2,050`)의 비역할 5개 단계는 8개 코드북 전체에서 단 1 tick의 차이도 없이 정확히 불변(`nonrole_stage_ticks_invariant_across_codebooks = True`)이었다.

## 6단계 연속 전이 프로브(809회 settle) 분석

- **1단계 `role`(64회 settle) → 2단계 `pair`(16회 전수 settle)**: 64개 숫자 역할 입력은 4개 Hamming 동치류(`d=0: 0.986470535294`, `d=1: 0.008324815594`, `d=2: 0.000003567999`, `d=3: 0.000000019441`, 동치류 내부 최대 편차 `1.041e-17`)로 분해된다. `4^2 = 16`개 ordered Hamming쌍 `(d_X, d_Y)` 전수 settle에서 `16/16` 모두 정확했고(거짓 구간 `[4.091034650497e-06, 0.011626869774]`, 참 값 `0.988310655569`), 40,320개 모든 3비트 전단사에 대한 `role -> pair` 동치류 합성 검사(`645,120`건)에서 오답은 `0`건이었다.
- **3단계 `or0..4`(121회 극값 settle) → 4단계 `projection0/1`(32회 극값 settle)**: `pair`의 3점 경계(`[pfalse_min, pfalse_max, ptrue]`)를 `or0..4`에 주입한 `1 + 3 + 9 + 27 + 81 = 121`회 settle에서 `121/121` 모두 정확했다(거짓 구간 `[1.166434879089e-02, 0.011712942728]`, 참 구간 `[0.988323570372, 0.999999838548]`). 이어 `or0..4`의 최악 내부 마진(`[mfalse_max, mtrue_min]`)을 `projection0`과 `projection1`의 모든 `2^4 = 16`개 부울 모서리에 주입한 32회 settle에서 `32/32` 모두 내부 주변곱 노드(`p00..p11`)와 재교차 출력(`e0..e3`, 거짓 구간 `[2.078383169801e-06, 0.021949682428]`, 참 구간 `[0.992958520211, 0.994203838579]`)의 엄격 마진을 만족하며 16개 입력 마스크를 정확히 `order=0: 10개`, `order=1: 10개`의 주변곱 폐포 서명으로 사상했다.
- **5단계 `feasible4`(64회 극값 settle) → 6단계 `query4`(512회 극값 settle)**: `or0..4` 직접 경로(32회)와 `projection0/1` 경유 경로(32회)의 최악 내부 마진을 `feasible4`의 모든 `2^5 = 32`개 부울 모서리에 주입한 64회 settle에서 `64/64` 모두 `none`/`unique`/`many`/`incomplete` 판정과 `e0..e3`·`complete` 마진을 정확히 복원했다. 마지막으로 `feasible4`의 최악 내부 마진(`e0..e3`, `complete`)과 `or0..4`의 최악 내부 마진(`t0..t3`)을 `query4`의 모든 `2^9 = 512`개 부울 모서리에 주입한 512회 settle에서 `512/512` 모두 5개 질의 태그(`{"empty": 16, "incomplete": 256, "mixed": 110, "qfalse": 65, "qtrue": 65}`)를 정확히 복원했다. 이는 최악 내부 마진 모서리 검증이며 `64^n` 전체 곱집합 열거 증명이 아니다.

## 실행·검산·비용

서버 Linux/Python 3.12.3에서 준비(`preparation`, 3.171659초, exit 0), 본 실행(`work`, 61.487527초, exit 0), 저장 감사(`audit`, 14.953332초, exit 0) 3단계가 모두 첫 실행에서 `returncode 0`(`status = COMPLETED`)으로 완료되어 원천 112 + 6단계 전이 프로브 809(직접 `role` 64 포함) + 상위 파이프라인 32,832 = **33,753회 actual settle**(총 1,020,630 tick, 1428개 고유 trace)과 768개 평가 기록(`batch00..11`, `metrics00..11`, `sources.json`, `roles.json`, `transfer.json`, `summary.json`, `work-ledger.json`, `n000..n1427`)이 전체 봉인 포함 **80.673714초**(상한 600초 이내)에 생성·검증되었다. stage 240초/total 600초·worker 1/retry 0·학습/World.measure/local native 0을 지켰고, 동결 뒤 코드 수정·native 재실행·튜닝·조건 추가는 0(`native_rerun = False`)이다.

로컬 saved-data 재생 검산(`analyze.py`)에서 무수정 `verify.bundle`이 서버 `summary.json`과 100% 일치하며 전체 768개 평가·809개 6단계 전이·1,428개 고유 trace와 `ValueError` 전용 25개 합성 변조 거부(`25/25`: `revision`, `source`, `variables`, `tuple`, `eligibility`, `messages`, `applied`, `state_hash`, `T_hash`, `value`, `selected`, `network_ref`, `binding_hash`, `coverage_activation`, `final_tag_tamper`, `marginal_projection_bypass`, `nonbijective_map`, `inverse_vocab_mismatch`, `numeric_role_coverage`, `incomplete_codepair_coverage`, `collapsed_restricted_codebook`, `pair_transfer_tamper`, `projection_envelope_tamper`, `feasible4_envelope_tamper`, `query4_envelope_tamper`)가 모두 통과함을 확인했다. scalar 최대오차는 서버 `0.0` / 로컬 `1.3877787807814457e-17` / tolerance `1e-9`였다. 로컬 검산과 CS 리뷰는 작성자의 saved-data 검산이며 독립 감사가 아니다.

고유 trace 1428개는 kernel+Config의 전체 canonical bytes를 확인해 **저장만** 공유했다. 모든 33,753회 추론 계산은 실제로 수행했다. 모든 phase CPU + parent 봉인 + launcher CPU 합계는 80.638477초이며, 기록 core 40.485076초, 저장 16.328447초, 원천 0.129516초, 6단계 전이 프로브(역할 포함) 3.587936초와 준비·audit·봉인 비용을 분석에 분리해 기록했다. 하위 항목 시간은 전체 process 비용의 부분집합이며 다시 더하지 않는다. 속도 비교·통계적 우위·학습 포함 효율 채택선은 없다.

## 근거와 한계

[분석](../../evidence/joint-tuple-codebook-transfer-20261023-r48/analysis.json), [로컬 검산](../../evidence/joint-tuple-codebook-transfer-20261023-r48/local-verification.json), [수신 검산](../../evidence/joint-tuple-codebook-transfer-20261023-r48/receipt-verification.json), [서버 manifest](../../evidence/joint-tuple-codebook-transfer-20261023-r48/raw/manifest.json), [서버 완료](../../evidence/joint-tuple-codebook-transfer-20261023-r48/server-completion.json), [CS 검토](../../evidence/joint-tuple-codebook-transfer-20261023-r48/cs/review.json)에 연결한다. manifest 대상 비어 있지 않은 파일 1460개와 manifest 자체를 받아 원본 크기·SHA-256을 직접 대조했다(어댑터 엔트로피 마스킹 감지 여부: `True`, 복원 파일 수: `1`). source 163파일·input 127핀은 변하지 않았다. 빈 stdout/stderr 6개와 evidence ZIP 자체는 받지 않았다. manifest는 자기 해시 밖에 있고 same-channel hash는 host attestation이 아니다.

## 판정과 다음 방향

**고정 8토큰 2변수 결합-튜플 대 주변곱-폐포 관계형 생산-소비 파이프라인 및 6단계 코드북 전이에서 의미 불변성 채택.** 이 결과는 2변수 4-튜플 관계형 생산-소비 파이프라인(`R37`)에서 8개 토큰·64개 ordered 코드쌍·16개 ordered Hamming쌍·56개 교차 도메인 사실쌍을 모두 활성화하여 비등거리 코드북이 봉인된 `hcr-r37-joint-tuple-v1` 바인딩의 연속 상태를 실제로 섭동시키는 조건에서도, `native_joint`의 16개 결합 적격 서명 및 100% 진리 복원과 `native_marginal`의 10개 주변곱 폐포 서명 및 대각/L자형 반례 128건의 안전한 `mixed` 기권(오확정 0건), 그리고 비역할 5개 상위 단계(`pair`, `membership`, `projection`, `feasible4`, `query4`)의 수렴 tick이 8개 코드북 전체에서 정확히 보존됨을 보인 유한 증거다. authored codebook을 학습된 표현·H03 구조 재사용·원계산 대체·속도/효율 증거로 합산하지 않으며, 최악 내부 마진 모서리 검증을 `64^n` 전체 곱집합 열거로 과장하지 않는다. core에 자동 반영하지 않으며, 이번 요청에서 추가 후속 실험은 자동 시작하지 않는다.
