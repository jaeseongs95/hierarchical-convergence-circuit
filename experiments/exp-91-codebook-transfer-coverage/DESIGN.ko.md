# R45 / EXP-91: 8토큰 전체 코드 공간 coverage와 역할→후속 유한 전이 충분조건 분리

[MEDIUM 방향 토론](DELIBERATION.ko.md)에 따라 R44(`exp-90-codebook-invariance`)에서 남은 두 가지 한계를 분리해 검증한다. R44는 2개 토큰(`amber`, `cobalt`)만 파이프라인에 등장해 8개 전역 bijection이 base당 6개 제한 대응으로 축약됐고(256짝 불변), 코드북당 4개의 ordered 코드쌍과 단일 비영 Hamming 거리만 소비했다. 또한 역할 단계 64개 입력의 이산 `adopted`만 40,320개 bijection에 대조했을 뿐, 연속 스칼라 `4*(2*goal-1)`이 후속 `expr`·`feasible2`·`query2`로 전달될 때 수렴과 의미가 유지되는 조건은 분리하지 않았다.

## 1. 56개 원천과 8/8 제한 대응·64/64 코드쌍 파이프라인 행렬

공개 8토큰 어휘(`amber`, `cobalt`, `jade`, `violet`, `wheat`, `umber`, `teal`, `coral`, 코드 `0..7`) 전체에 대해 후보 원천 `R` 8개(`n0_R_0..7`), 문맥 원천 `P0/P1/P2` 각 8개(`24`개), 질의 원천 `Q0/Q1/Q2` 각 8개(`24`개)로 총 **56개 실제 native path 원천**을 생성한다.

후보 쌍 4개 `(0,6), (1,2), (3,5), (4,7)` × AST 쌍 4개 `(0,1), (2,3), (4,5), (5,4)`(6개 AST `0..5` 모두 포함) × C/T 마스크 8개(`t_mask = c_mask ^ xor_offset`, `xor_offset in [7,1,2,4]`)로 **128개 base**를 고정하고, 8개 전역 bijection(`identity`, `bit_reverse`, `xor7`, `cnot01`, `cnot12`, `cnot20`, `cnot_chain`, `swap01`)을 적용해 **1,024개 native 조건 + 128개 exact 조건(총 1,152 평가)**을 실행한다.
- 모든 단일 base는 최소 1개 이상의 거짓 leaf 슬롯에 1-토큰 구별 앵커를 포함하여 **128개 모든 base에서 제한 대응 수가 정확히 8개(`actual_restricted_map_classes_per_base == [8]`, 무변경 0/896짝, 실제 코드 변경 896/896짝)**다.
- 각 코드북은 128개 조건의 `1,536`회 역할 비교에서 **가능한 모든 64개 ordered 코드쌍(`0..7 × 0..7`)**과 모든 Hamming 거리 $d \in \{0,1,2,3\}$ 및 같은 AST 내 이종 비영 Hamming 거리 삼중쌍을 실제로 소비한다.
- 원래 R35/R36 생성기·`execute`·`Config`·초기상태 `0.5`·typed slot guard·packet-only T 소비자 경계는 수정 없이 그대로 사용한다.

## 2. 역할→후속 유한 전이 충분조건 분리 (64 Role + 384 Expr + 80 극값 경계)

1. **역할 단계 4개 Hamming 동치류 분해 (`64` settles)**:
   64개 ordered 3-bit 입력쌍 `(x, y)`을 실제 실행하고, 비트 위치·극성 대칭에 의해 최종 `state['goal']`과 `ticks`가 오직 Hamming 거리 $d(x,y) \in \{0,1,2,3\}$에 의해서만 결정되는 4개 동치류 $G = \{g_0, g_1, g_2, g_3\}$로 정확히 분할되는지 검증한다.
2. **`role -> expr` 전수 유한 전이 (`6 AST × 4^3 = 384` settles)**:
   `evaluate()`는 3개 leaf의 역할 출력 $(k_0, k_1, k_2) \in G^3$을 받아 `4*(2*k_j-1)`을 `expr`에 전달한다. 따라서 $8! = 40,320$개 모든 3-bit bijection과 모든 3-leaf 조합이 `expr` 단계에 줄 수 있는 입력 벡터는 AST당 최대 $4^3 = 64$개뿐이다. 6개 AST 전체에 대해 $6 \times 64 = 384$회를 전수 실행하고, 모든 $(d_0, d_1, d_2) \in \{0,1,2,3\}^3$에서 이산 진릿값 `truth(tree, [d0==0, d1==0, d2==0])`이 보존되는지, 그리고 `expr` 출력의 참 구간 $[v_{\text{True}}^{\min}, v_{\text{True}}^{\max}]$과 거짓 구간 $[v_{\text{False}}^{\min}, v_{\text{False}}^{\max}]$ 및 모든 40,320개 bijection의 `role -> expr` saved lookup(`6 × 8^3 × 40,320` 대응)을 검산한다.
3. **`feasible2` 및 `query2` 극값 구간 경계 (`16 + 64 = 80` settles)**:
   384개 `expr` 결과에서 추출한 4개 극값 대표점 $E_{\text{env}} = \{v_{\text{False}}^{\min}, v_{\text{False}}^{\max}, v_{\text{True}}^{\min}, v_{\text{True}}^{\max}\}$에 대해 `feasible2`의 모든 $4^2 = 16$개 조합과, 그 결과에서 추출한 극값 eligibility 대표점 $Elig_{\text{env}}$와 $E_{\text{env}}$를 결합한 `query2`의 64개 극값 모서리 조합을 실제 실행한다. 이는 연속 구간의 양끝 경계 검사이며, $64^2$ 또는 $64^4$ 전체 곱공간 열거로 과장하지 않는다.

## 3. 비용·자원 상한과 검증 경계

원천 `56` + 역할 `64` + `expr` 전수 전이 `384` + 극값 경계 `80` + 상위 파이프라인 `18,432`(`1,024 × 18`) = **총 `19,016`회 실제 native settle**(최대 `3,042,560` tick)을 지정 AI Research SSH(`ssh-ai-mcp`)에서 `worker=1`, `retry=0`, 단계 `240`초 / 전체 `600`초, `raw 128MiB` / `cache 128MiB` / `AS 512MiB` 상한으로 1회 실행한다. 학습·세계 측정·로컬 native 실행은 `0`회다.
