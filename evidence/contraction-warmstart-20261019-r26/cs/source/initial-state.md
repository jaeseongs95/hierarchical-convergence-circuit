# EXP-38 / R057 결과와 토론

## 결론

같은 입력·program에서도 uniform 초기 상태에 따라 서로 다른 low/high endpoint가 관측됐다.
두 orientation의 full은 initial=.1/.5에서 low, .9에서 high로 종료했다.
start/drop_P_prefix에서도 같은 분리가 나타났다. goal/drop_P_prefix는 세 초기값 모두 high였다.
따라서 R056의 endpoint를 초기 상태와 무관한 입력·program의 단일 결과로 일반화할 수 없다.

이번 결과는 동결한 수치 종료 규칙 아래에서의 초기 상태 의존성이다.
서로 다른 수학적 attractor, basin 경계, 전역 수렴 또는 hysteresis를 입증한 것은 아니다.

## 관찰

연구 run: `HCR-Evidence/exp38/r057-20260919T232156Z-e40677a0fb`.
12행 모두 stable_decision이었다. 아래 goal은 여섯 자리로 표시했다.

| orientation | initial | full goal | drop_P_prefix goal | full/drop | ticks full/drop |
|---|---:|---:|---:|---|---|
| start | .1 | 0.026117 | 0.028676 | low/low | 70/73 |
| start | .5 | 0.026117 | 0.028676 | low/low | 60/62 |
| start | .9 | 0.982017 | 0.981604 | high/high | 37/38 |
| goal | .1 | 0.013283 | 0.986808 | low/high | 75/99 |
| goal | .5 | 0.013283 | 0.986808 | low/high | 116/75 |
| goal | .9 | 0.987483 | 0.986808 | high/high | 38/60 |

초기값 .9−.5의 goal 차이는 start/full +0.9558999634,
start/drop +0.9529281905, goal/full +0.9741995885였다.
goal/drop에서는 +0.0000001747346299였고 high 범주를 유지했다.
사전 대조 8개 중 3개에서 서로 다른 안정 low/high 범주가 확인됐다.
이는 독립 시행의 성공률 3/8을 추정한 것이 아니다.

initial=.1−.5의 goal 차이는 start/full +3.6684812368e-8,
start/drop +5.6182267071e-8, goal/full −2.2300523117e-7,
goal/drop +6.4112826159e-10이었다. 같은 범주와 작은 차이를 확인했지만
완전히 같은 고정점·수치적 동등성·초기 상태 영향 부재를 입증하지 않았다.

동결된 low 술어에 대한 P_prefix의 맥락적 필요성은 initial=.1/.5의 start에서 false,
goal에서 true였다. initial=.9에서는 full부터 high이므로 두 방향 모두 null이다.
이를 링크가 불필요해졌다는 결론으로 바꾸지 않는다.
initial=.9의 삭제 효과(drop−full)는 start −0.0004127885, goal −0.0006749915였다.

연구 12분기만 합친 비용 counter는 kernel ticks 803, signal transmissions 6,017,
group updates 4,015, normalization operations 4,015다.
단위가 다른 counter를 더하지 않았고 smoke·부모 replay는 연구 비용에 포함하지 않았다.
실제 에너지는 측정하지 않았다. stable_decision은 수치 종료이며 native 채택 결과가 아니다.

## 해석

R056에서 weak drive 증가가 full low→high를 만들었다는 결과는 initial=.5 맥락에서 유효하다.
R057은 weak drive=.08을 그대로 두어도 uniform initial=.9에서는 full이 high로 끝남을 보여준다.
따라서 관측된 high endpoint에 도달하는 경로를 weak drive 증가 하나로 제한할 수 없다.
이번 실험은 초기 상태가 계산 궤적과 종착점 범주에 관여함을 직접 조작해 확인했다.

링크 삭제 효과 역시 초기 상태에 조건부다. goal 방향의 large low→high 삭제 효과는
initial=.1/.5에서 관측됐지만, .9에서는 두 mask 모두 이미 high였다.
이는 과거 관측의 반증이 아니라 해당 필요성 주장의 적용 조건을 더 분명히 한 결과다.

주장 상태는 다음과 같이 구분한다.

- `observed`: 두 full 및 start/drop에서 .5→.9 초기 상태 변경에 따른 low→high 범주 차이.
- `observed`: goal/drop은 이번 세 초기값에서 high로 종료함.
- `falsified`: 이 program·입력에서 조사한 uniform 초기값들이 항상 같은 endpoint 범주로 끝난다는 일반화.
  이는 HCC 전체 가설이나 수학적 고정점 유일성 자체의 반증이 아니다.
- `hypothesis`: 관측된 분리가 서로 다른 장기 안정 상태의 영향권을 반영함.

## 대안 설명

종료 규칙은 residual과 연속 안정 tick을 사용하는 유한시간 기준이다.
지금의 low/high가 더 긴 계산에서도 유지되는지 아직 관측하지 않았다.
따라서 장기적으로 서로 다른 상태를 유지한다는 설명과, 현재 종료 이후 천천히 다른 상태로
움직일 수 있다는 설명은 이번 실험만으로 완전히 구별되지 않는다.

모든 좌표를 동시에 .1/.5/.9로 설정했으므로 edge, prefix, goal 중 어떤 초기 좌표가
분리에 기여했는지는 모른다. 초기 상태 전체 공간이나 비균일 상태를 조사하지도 않았다.
서로 다른 종료 tick의 endpoint 차이는 같은 시각의 상태 차이·효율 차이와 같지 않다.
goal/drop의 세 high 결과만으로 이 구조가 모든 초기 상태에서 high로 수렴한다고 말할 수 없다.

## 사후 토론과 다음 판별 실험

다음 우선안은 더 촘촘한 초기값 탐색에 앞서 종료 뒤에도 분리가 유지되는지 확인하는 것이다.
좌표별 개입은 원인 분리에 유용하지만 먼저 유한시간 종료의 영향을 구별하는 편이
현재의 장기 안정 상태 해석을 더 직접적으로 점검한다.

- 같은 12조건에서 입력·program·초기 상태·갱신 수식을 그대로 둔다.
- 기존 최초 종료 지점은 marker로 보존하되 계산을 거기서 중단하지 않고 tick 512까지 이어간다.
- marker까지 R057 전체 궤적 12개를 bridge로 비교하고, 그 뒤 구간을 별도 continuation 개입으로 기록한다.
- 기존 marker와 tick 160/512의 상태·residual·범주를 사전 정의해 비교한다.
  중단 규칙 변경과 연장된 비용을 숨기지 않고 기존 first termination을 대체하지 않는다.

이것은 다음 phase 제안이며 이번 연구의 추가 실행이 아니다. 다음 계약은 아직 동결·실행하지 않았다.
512 tick에서 분리가 유지돼도 무한시간 안정성이나 basin 경계의 증명은 아니며,
유한시간 지속성의 증거로만 해석한다. 이 우선안은 main의 사후 판단이며 독립 패널 합의가 아니다.

## 현재 주장 가능한 범위

고정 numerical kernel에서 초기 상태를 조작했을 때 계산 궤적과 안정 종료 범주가 달라졌다.
native packet/proof/support/raw decision/adoption/실제 에너지는 null이다.
12행은 결정론적 분기이며 독립 표본이 아니다. .5의 4행은 재현 control이고
다른 초기값의 8행이 새 대조다. R052 native replay와 R056 replay를 새 연구 증거로 중복 계산하지 않는다.
외부 LLM 행동, 모델 내부, 인간 인지, 학습된 Circuit 형성·재사용, HCC 통합가설의 증명으로 확장하지 않는다.

## 검증과 보존

- main이 직접 구현·통합했다. 별도 프로세스의 독립 recurrence 검산은 수행했지만
  독립 연구자·최종 Judge 감사는 수행하지 않았다.
- 개발 synthetic 검사 22개 및 원클릭 동결 source self-test 22개 통과.
  fixture는 실제 연구의 prefix bias와 다르게 구성했고 연구 결과에 포함하지 않았다.
- 별도 smoke 4행·R056 전체 궤적 bridge 4개 통과.
- 최종 core regression 1회: 602개 중 599개 통과, 기존 Windows symlink 환경 skip 3개.
  새 실패·새 skip은 없으며 skip을 pass로 세지 않았다.
- 실제 연구 12행의 전 tick·최초 종료·counter와 R056 bridge 4개 검산 통과.
  main도 raw에서 모든 좌표 delta, 초기 상태 대조 8개, 범주 차이 판정을 직접 대조했다.
- source 249개의 동결 일치, bundle 575개 파일 hash, manifest 포함 ZIP 576개 파일의
  목록·CRC·원본 bytes 일치를 확인했다. ZIP 크기는 1,744,739 bytes다.
- 최초 원클릭에서 완료했다. 실제 연구 재시작·자동 retry·기존 raw 덮어쓰기는 없다.
  확인 기록은 `HCR-Evidence/r057-validation/delivery-verification.json`에 보존했다.

Audit SHA-256: `65b884c5333a8443dfd01fb5161b8b9bf39a822711555c96a9f16078fc906e64`.
ZIP SHA-256: `bfb7fb46bf373e06b0f8a9b05c509f6d3f7d6c151de34851ccf09fbbb452606b`.

원클릭은 `Run-HCR-R057.cmd`다. 이 문서는 사후 해석 기록이며 동결 source에 소급해 넣지 않는다.
기존 core/tests/R050–R056 source·manifest·raw evidence 및 기본 dispatcher EXP-30은 보존했다.
