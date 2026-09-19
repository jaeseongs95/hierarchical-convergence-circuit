# EXP-33 / R052 결과

## 결론

배열 순서를 뒤집은 8개 대응 비교 모두에서 구조 역할에 대응한 최종 수치 상태,
전체 tick 궤적, network, proof/support/readout의 비교 투영이 같았다.
수치 최대 차이는 0이었다. 따라서 현재 2-edge ++, 고정 강도·빈 memory 조건에서
R051의 TD·구조 위치 반응을 단순한 배열 index 차이로 설명하는 가설은 약화된다.
특정 feedback link의 원인 역할은 아직 미확인이다.

## 관찰

run: `HCR-Evidence/exp33/r052-20260919T135909Z-1f0e296bc0`

동결 checkout은 `b1d4525039f94c22f8aa2233aa6d6db616d9282c`이며 R052 신규 소스는
해당 run의 `source/`와 `source_manifest.json`, `R052_MANIFEST.json`으로 추가 결속됐다.
현재 커밋 이름만으로 실행 당시 신규 소스를 대체하지 않는다.

| 비교 | 수 | 결과 |
|---|---:|---|
| path↔swapped, 역할 대응 최종 상태 | 8 | 모두 같음, max delta=0 |
| path↔swapped, 역할 대응 전체 궤적 | 8 | 모두 같음, max delta=0 |
| path↔swapped, 역할 대응 network | 8 | 모두 같음 |
| path↔swapped, candidate 의미 투영 | 8 | 모두 같음, max delta=0 |
| path↔swapped, raw e:0/e:1 좌표 상태 | 8 | 6개 다름, 2개 같음 |
| hold↔revision_only | 4 | 상태·궤적 동일 |

`role_map_verified`만으로 불변성을 주장한 것이 아니다. 각 comparison의 실제 상태·궤적·
network·candidate 일치 판정과 차이 수치를 확인했다. provenance ID·hash·배열 slot은
원 packet에서 그대로 남고, 비교용 투영만 역할을 대응한다.

다음 값은 path와 swapped에서 각각 같았다. hold와 revision_only의 결과는 같다.

| TD | 개입 | goal activation | raw | proof 유효 | support gap | 채택 | session ticks |
|---|---|---:|---|---|---:|---|---:|
| OFF | 초기/echo | 0.017257 | False | 아니오 | 0 | 보류 | 37 |
| OFF | start_edge | 0.734164 | True | 예 | 0 | True | 47 |
| OFF | goal_edge | 0.934295 | True | 예 | 0 | True | 44 |
| ON | 초기/echo | 0.011671 | False | 예 | 1 | 보류 | 88 |
| ON | start_edge | 0.026117 | False | 예 | 1 | 보류 | 60 |
| ON | goal_edge | 0.013283 | False | 예 | 1 | 보류 | 116 |

hold는 기준선 session을 재사용하므로 추가 ticks는 0이다. 표의 초기 ticks는 고유 기준선 비용이다.
ON에서 내부 edge 충돌은 강화 전 2개, 강화 후 1개다. 남은 약한 edge의 False 가정이
양수 관측과 충돌하므로 proof가 가정하 유효해도 채택은 거부된다.
예를 들어 swapped/ON/start_edge인 c003에서는 a-edge가 array slot1에서 강화되고,
z-edge는 slot0에서 0.374907731403으로 남아 `assumed=False`, `support=sign_conflict`다.
이는 path/ON의 같은 구조 역할 결과와 일치한다.

## 해석

관찰된 반응은 이 조건에서 배열 index가 아니라 동일한 구조 역할을 따라 유지됐다.
raw 좌표 비교만 했다면 6개 대조를 실제 동역학 차이로 오해할 수 있었다.
R051에서 확인한 OFF 채택/ON 보류와 위치별 수치·비용 차이는 배열 교환 후에도 남았다.
이는 representation 대조를 먼저 수행한 이유를 충족하지만 feedback 원인을 설명한 것은 아니다.

## 대안 설명과 다음 판별 실험

TD 전역 스위치는 4개 feedback link를 함께 바꾼다. 남은 후보는 edge-local feedback,
계층 사이 feedback, 비선형 threshold와 그 상호작용이다.
다음 후보는 같은 두 강화에 동일한 사전등록 mask를 적용하는 선택적 feedback 분리다.
full-on/full-off와 edge-local/inter-level 대조의 정확한 의미, 독립 수치 replay,
config·source 동결 및 tamper 검증을 먼저 설계해야 한다.
이 후속은 아직 구현·실행하지 않았다. R052에 결과 의존 mask나 arm을 추가하지 않았다.

## 현재 주장 가능한 범위

관계 ++, 2-edge chain, score 0.02→1.0, 고정 이름, 두 배열, 두 TD 설정,
빈 memory·단일 frontier·동기 갱신에 한정된 결정론적 대조다.
다른 topology·배열·강도·초기 상태·학습 memory로 일반화하지 않는다.
frontier 경쟁이나 scheduling을 조작하지 않았고 learned circuit binding/reuse도 없었다.
16기록은 4기준선의 분기이지 독립 표본 16개가 아니다. 정답 채택은 synthetic reference=True 기준이다.
이 결과를 Graph→Circuit 학습, 인간 인지, 에너지 효율의 증거로 쓰지 않는다.

## 검증·비용·검토 기록

- 원클릭 `Run-HCR-R052.cmd` 1회, exit 0. 본 연구 4기준선/16기록 독립 audit 통과.
- 봉인 소스 자체 테스트 27/27 통과. 별도 native smoke 2기준선/8기록 audit 통과.
- core 회귀 1회: 602개 실행, 599개 통과, 기존 Windows symlink skip 3개,
  실패/오류/새 skip 0개. 실행 로그 기준 169.367초.
- 자동 retry 없음. 본 연구 실행 실패 없음. 개발 중 평가기 검토·수정은
  `IMPLEMENTATION_REVIEW.ko.md`에 기록했고 본 연구 전에 끝냈다.
- audit SHA-256: `4a3c2ee31e1815571e400177aacb5e76f73c40d446d7dac01793f8c1f9990f25`.
- ZIP CRC/inventory, 봉인 manifest의 483개 파일 ZIP 내부·로컬 SHA-256 확인.
  ZIP 크기 2,535,832 bytes. 봉인된 raw/source와 로그를 수정하지 않았다.
- 고유 기준선: kernel ticks 250, signal transmissions 1,704.
  추가 12 session: kernel ticks 784, signal transmissions 5,248, proof nodes reconstructed 34.
  측정/학습/memory write/circuit reuse 0. 에너지·프로세스 memory 미측정.
- 실험 목록 34개 경로 검증, 필수 저장소 경로 9개 확인. 기본 EXP-30 유지.

오케스트레이션에 따른 별도 읽기 전용 검토자는 최종 역할 투영 코드에서 수정 필수 finding을
제시하지 않았다. 다만 투영 가능성 자체를 불변성 증거로 읽지 말 것을 강조했다.
그 검토자는 결과 수치·core 테스트를 재실행하지 않았으며, 수치와 증거 해시는 메인이 직접 확인했다.
평가기 구현 담당과 계약 검토자를 분리했지만 provider 내부 독립성이나 모델 적용을 증명한 것은 아니다.
