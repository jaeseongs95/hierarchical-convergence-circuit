# EXP-35 / R054 결과와 토론

## 결론

사전 동결한 두 입력에서 약한 edge로 돌아가는 E feedback을 하나 제거하면 low goal이
high로 바뀌었다(P1 두 조건 지지). 강한 edge로 돌아가는 E feedback만 제거하면
low가 유지됐다(P2 두 조건 지지). goal→prefix feedback은 양쪽 입력에서 필요했지만,
prefix 사이 feedback은 goalstrong에서만 필요했다.
여기서 필요성은 초기 전 좌표 0.5·고정 입력·설정·종료 규칙에서의 low endpoint 술어에 한정한다.

R053의 집합 간 효과 반전을 개별 링크 대조로 좁혔지만, 유일한 원인 고리나 일반적 충분성,
native proof/support/adoption, 다중 attractor를 입증한 것은 아니다.

## 관찰

연구 run: `HCR-Evidence/exp35/r054-20260919T153156Z-4ea84e3e56`.
아래 값은 goal activation을 소수점 여섯 자리로 표시했다. 정확한 값·전 좌표·모든 tick은 raw에 있다.

| feedback 조작 | startstrong goal | goalstrong goal |
|---|---:|---:|
| full | 0.026117 | 0.013283 |
| off | 0.734164 | 0.934295 |
| E_start 제거 | 0.026113 | 0.984993 |
| E_goal 제거 | 0.924068 | 0.013286 |
| P_prefix 제거 | 0.028676 | 0.986808 |
| P_goal 제거 | 0.967004 | 0.986579 |

12개 모두 stable_decision으로 종료했다. 이는 수치 커널의 종료 상태명이지 native 채택 결과가 아니다.
경계 구간·비안정 종료로 인한 판정보류는 없었다. P_prefix/P_goal은 비방향 사전 대조이며,
관측 방향을 사전 예측 성공으로 소급하지 않는다.

약한 edge E 제거의 delta_goal은 startstrong +0.8979505520266531,
goalstrong +0.9717096664617507이었다. 약한 edge activation의 변화는 각각
+0.1764703522810127, +0.16545503264066325였다.
강한 edge E 제거의 delta_goal은 각각 −0.000004520914407196708,
+0.000002982203844197062였다. 작은 차이가 존재하므로 “영향 없음”으로 바꾸지 않는다.

연구 12개 분기의 counter 합계는 kernel ticks 894, signal transmissions 6,161,
group updates 4,470, normalization operations 4,470이다. 단위는 합치지 않는다.
smoke·부모 replay 비용은 이 합계에 포함하지 않았다. 실제 에너지는 측정하지 않았다.

## 해석

약한 edge 쪽 feedback의 조건부 역할은 두 입력에서 반복됐지만, 필요한 내부 경로는 같지 않았다.
startstrong에서는 P_prefix 하나를 제거해도 low가 유지됐고,
goalstrong에서는 같은 링크 제거가 high 전환을 일으켰다.
따라서 “네 feedback 모두가 필수”라는 설명은 맞지 않는다.

P_goal은 두 조건에서 개별 제거 시 low를 깨뜨렸다. 이는 full 배경에서 해당 링크의
조건부 필요성을 지지하지만, P_goal 단독의 충분성이나 유일한 기여 경로를 뜻하지 않는다.
R053의 E-only/P-only 결과와 함께 보면 집합 구성에 따른 상호작용 설명은 유지되며,
개별 링크를 모두 같은 기능으로 취급하는 설명은 좁혀진다.

## 대안 설명과 한계

양의 link weight도 centered signal(2×activation−1)의 부호에 따라 억제 방향으로 작용할 수 있다.
하지만 이번 endpoint 대조만으로 어느 tick의 신호가 전환을 결정했다고 단정하지 않는다.
입력 위치와 support topology·prefix bias·경로 길이의 비대칭은 함께 남아 있으므로
P_prefix 효과 차이를 순수한 의미적 역할 차이로 해석하지 않는다.

다중 링크의 공동 제거 효과는 단일 제거 결과의 합과 다를 수 있다.
low가 유지된 링크도 다른 feedback 배경이나 초기 상태에서는 필요할 수 있다.
종료 tick이 서로 다르므로 endpoint 차이는 동일 시간의 효과가 아니다.
0.5±1e-6은 동결한 공학적 판정보류 폭이지 고정점 오차 한계가 아니다.
새 8개 단일 제거 대조와 4개 재현 control은 결정론적 분기이며 독립 표본 12개가 아니다.

## 사후 토론과 다음 판별 실험

설계 검토자가 raw·audit를 읽고 제안한 우선 방향은 P_prefix 비대칭에 대한
고정총량 입력 배분 대조다. main은 네 feedback의 전체 16 subset을 조사하는 대안도
검토했으나, 이는 공동 제거·충분성 질문으로 넓어지므로 후순위로 두었다.
현재 관찰의 입력 의존성을 직접 좁히는 아래 후보를 다음 phase 우선안으로 선택했다.

- 입력 쌍: (1,.02), (.755,.265), (.51,.51), (.265,.755), (.02,1).
- 각 쌍에서 full과 drop_P_prefix를 비교: 총 10개 중 양 끝 4개는 R054 bridge,
  내부 6개만 새 수치 대조다. 초기값·config·topology·bias·종료 규칙은 고정한다.
- 입력 표기와 실제 kernel drive의 4배 매핑을 구별하고, primary delta_goal 및
  e:0/e:1 두 고정 좌표를 모두 보고한다. 중간·동률 조건의 “weak edge”를 사후 선택하지 않는다.
- low/high 판정보류 규칙과 raw trajectory·단위별 counter를 유지한다.
  단조성이나 전환점 존재를 가정하지 않으며 관측하지 않은 구간을 보간 결론으로 쓰지 않는다.

이 후보는 상대 입력 배분에 대한 의존성을 측정하지만, 고정된 topology·bias·경로 길이 중
무엇이 비대칭을 만드는지는 분리하지 못한다. native session 실험이나 충분성 add-back과 섞지 않는다.
아직 다음 phase의 소스·최종 조건을 동결하거나 실행하지 않았으며, 이번 결과 뒤 추가 탐색은 없다.

## 검증과 보존

- 오케스트레이션으로 설계 검토, producer/pipeline, 별도 numerical evaluator 구현을 분리했다.
  독립 blind 패널이나 최종 fresh Judge 감사로 표현하지 않는다.
- Ponytail 원칙에 따라 기존 kernel 실행·독립 recurrence 검산을 재사용했고 과거 소스를 바꾸지 않았다.
- 동결 소스 self-test 18개 통과. 별도 implementation smoke 6개·R053 bridge 2개 통과.
- 최종 core regression은 1회: 602개 중 599개 통과, 기존 Windows symlink 제약 skip 3개,
  새 실패·새 skip 없음. skip을 pass로 세지 않았다.
- 본 연구 12개, R053 전체 궤적·종료·counter bridge 4개 통과.
  R052 6 native 부모 replay와 R053 4 anchor replay는 출처 검증이며 새 연구 결과가 아니다.
- raw와 audit row·delta를 별도 대조했고, 동결 source 195개와 현재 source가 일치했다.
- bundle manifest 대상 469개, manifest 자체를 포함한 ZIP 470개에 대해 inventory·CRC·원본 bytes를 확인했다.
  ZIP 크기는 1,548,450 bytes다. 기존 evidence를 덮어쓰지 않았고 자동 retry는 없었다.

Audit SHA-256: `1af5e5d88e4c86233b3d21b4e98cd0f7987ff1a806f268ffb07984a8b29da0c7`.
ZIP SHA-256: `05b73566270411780b57b8b87a16f675ba69c467204483d06eb16115e391f780`.

이 문서는 실행 후 해석 기록이며 실행 전 source manifest에 소급해 포함하지 않는다.
기본 dispatcher EXP-30은 유지하며 R054 원클릭 진입점은 `Run-HCR-R054.cmd`다.
