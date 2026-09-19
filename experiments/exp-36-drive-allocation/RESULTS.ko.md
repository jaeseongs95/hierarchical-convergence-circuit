# EXP-36 / R055 결과와 토론

## 결론

R054에서 관측한 P_prefix 필요성 차이는 두 끝점에서 재현됐지만,
내부 세 입력에서는 full과 drop_P_prefix가 모두 high로 종료했다.
따라서 두 번째 edge 쪽 입력이 더 크다는 사실만으로 low endpoint에 대한 필요성을 예측할 수 없다.
이번 5점에서 full의 goal은 low–high–high–high–low였으며,
drop_P_prefix는 low–high–high–high–high였다.

이는 고정된 numerical kernel의 사전 지정 입력점 결과다.
연속 구간의 모양·전환점·다중 attractor·native proof/adoption을 입증하지 않는다.

## 관찰

연구 run: `HCR-Evidence/exp36/r055-20260919T223338Z-f38382c648`.
입력 총량은 1.02, 실제 edge drive 총량은 4.08이다. 아래 goal은 여섯 자리로 표시했다.

| 입력 (e:0,e:1) | full goal | drop_P_prefix goal | delta goal | full/drop |
|---|---:|---:|---:|---|
| (1,.02) | 0.026117 | 0.028676 | +0.0025589845 | low / low |
| (.755,.265) | 0.987526 | 0.987486 | −0.0000401911 | high / high |
| (.51,.51) | 0.987717 | 0.987686 | −0.0000316401 | high / high |
| (.265,.755) | 0.987731 | 0.987691 | −0.0000407267 | high / high |
| (.02,1) | 0.013283 | 0.986808 | +0.9735244223 | low / high |

10개 모두 stable_decision이었다. 이 이름은 수치 종료 상태이지 native 채택 결과가 아니다.
내부 세 점은 full부터 high였으므로 low 유지에 대한 필요성 값은 null이다.
이를 링크가 불필요하다거나 효과가 없다고 바꾸어 해석하지 않는다.
startstrong의 필요성 값은 false, goalstrong은 true이며 모두 동결된 low 술어에 한정한다.

기술 대조 right−left는 외부 쌍 +0.9709654378044079,
내부 쌍 −0.0000005355590100286634였다. 이 값은 대칭성 검정이나 0에 대한 통계 검정이 아니다.
내부 delta들이 작다는 사실은 확인했지만 수치 오차 한계·통계적 동등성·영향 부재를 증명하지 않았다.
결과 방향을 지정하지 않은 사전 대조이므로 이를 방향 예측의 성공으로 소급하지 않는다.

연구 10개 분기의 counter 합계는 kernel ticks 513, signal transmissions 3,867,
group updates 2,565, normalization operations 2,565다.
단위를 합치지 않았으며 smoke·부모 replay 비용은 포함하지 않았다. 실제 에너지는 미측정이다.

## 해석

R054의 끝점 차이를 입력 우세 방향에 따른 단순한 규칙으로 확장할 수 없다는 점이 명확해졌다.
내부 세 점에서는 두 edge가 모두 높은 활성도로 종료하고 goal도 high였다.
관측한 세 내부 점의 작은 삭제 효과와 양 끝의 차이는 이 고정 program에서 확인된 사실이다.
한쪽 edge가 매우 약한 끝점에 low가 나타났다는 설명과 양립하지만,
약한 입력 하나가 원인인지, 다른 입력의 크기와 상호작용한 것인지는 아직 분리되지 않았다.

R055는 입력 배분과 P_prefix 삭제 효과의 조건 의존성을 보여준다.
full의 양 끝 low와 내부 high를 단순한 선형·단조 변화로 표현할 수 없다.
다만 관측하지 않은 입력점에서의 연속적 곡선이나 경계 위치는 주장하지 않는다.

## 대안 설명과 현재 주장 범위

고정총량 조건에서는 약한 drive를 높일 때 강한 drive도 함께 낮아졌다.
따라서 총량 효과는 통제했지만, 개별 drive 변경의 기여는 이번 대각선 대조만으로 분리되지 않는다.
topology·p:0:1의 −2 bias·support 경로 길이·feedback 방향도 그대로 남아 있다.
내부 high와 작은 delta는 포화 응답과 양립하지만, 포화를 독립적으로 조작한 증거는 아니다.

각 branch는 fresh initial=.5이고 서로 다른 입력을 썼다. 같은 입력의 여러 초기 상태를 조사한
것이 아니므로 basin/다중 attractor나 hysteresis를 주장하지 않는다.
종료 tick이 다르므로 endpoint 차이를 동일 시간의 효과나 효율로 바꾸지 않는다.
새 내부 6개 대조와 재현 control 4개는 결정론적 분기이며 독립 표본 10개가 아니다.
native packet/proof/support/raw decision/adoption 및 실제 에너지는 null이다.

## 사후 토론과 다음 판별 실험

main은 끝점 사이를 더 촘촘히 탐색하는 대안과 두 drive의 factorial 분리를 비교했다.
읽기 전용 검토자도 raw·audit를 확인한 뒤, 약한 drive 증가와 강한 drive 감소를 분리하는
2×2 대조가 현재 대안을 더 직접적으로 구별한다는 의견을 냈다. 이를 다음 phase 우선안으로 정했다.

- strong drive {4, 3.02} × weak drive {.08, 1.06}을 두 orientation에서 따로 비교한다.
- 각 조합에 full/drop_P_prefix를 적용하면 16행이다.
  R055 대각선 8행은 전체 궤적 bridge, off-diagonal 8행만 새 대조다.
- orientation별 delta_goal 2×2 표와 다른 drive를 고정한 단순차를 사전 정의한다.
  구조적으로 교환 가능한 orientation이 아니므로 평균이나 대칭 검정으로 합치지 않는다.

이는 R055 고정총량 계약의 추가 실행이 아니라 다음 phase의 새 국소 factorial 계약이다.
off-diagonal 총 drive는 3.10 또는 5.06이며 총량이 달라짐을 명시해야 한다.
개별 drive 효과와 별도의 총량 효과를 동시에 독립 원인으로 분해했다고 주장하지 않는다.
topology·bias·경로 길이의 원인 분리는 여전히 남는다.
다음 phase의 최종 spec·소스는 아직 동결하거나 실행하지 않았다.

## 검증과 보존

- 오케스트레이션으로 읽기 전용 설계·구현 검토와 별도 numerical evaluator 구현을 분리했다.
  blind 패널이나 독립 최종 Judge 감사로 표현하지 않는다. 모델 인자는 전달했지만 실제 적용은 unverified다.
- Ponytail 원칙에 따라 기존 kernel 실행·삭제 mask·독립 recurrence 검산을 재사용했다.
  기존 core/tests 및 R050–R054 manifest/source는 변경하지 않았다.
- 동결 source self-test 21개 통과. 별도 implementation smoke 4개·전체 궤적 bridge 4개 통과.
- 최종 core regression 1회: 602개 중 599개 통과, 기존 Windows symlink 환경 제약 skip 3개.
  새 실패·새 skip 없음. skip을 pass로 세지 않았다.
- 연구 10개와 R054 전체 궤적 bridge 4개를 독립 검산했다.
  R052 6 native replay 및 R054 4 anchor replay는 출처 검증이지 새 연구 표본이 아니다.
- main이 raw↔audit의 상태·counter·세 좌표 delta를 별도 대조했다.
  source 213개의 freeze 일치와 bundle 501개 파일의 hash를 확인했다.
- manifest 자체를 포함한 ZIP 502개 파일의 목록·CRC·원본 bytes 일치를 확인했다.
  ZIP 크기는 1,587,755 bytes다. 최초 원클릭에서 정상 완료했으며 자동 retry·추가 연구 실행은 없었다.

Audit SHA-256: `cbba5efa6699b01d39b8a9cdc916d995bd01f9d849461872ead0d2a6ce503e9d`.
ZIP SHA-256: `785a398d990613f173b9a9667bdcf3ff221edfd5ea34bc026e70c4c5c33ce3dc`.

이 문서는 사후 해석 기록이며 실행 전 source manifest에 소급해 넣지 않는다.
원클릭은 `Run-HCR-R055.cmd`이며 기본 dispatcher EXP-30은 유지했다.
