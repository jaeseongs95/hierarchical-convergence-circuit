# EXP-37 / R056 결과와 토론

## 결론

두 orientation 모두 strong drive를 4 또는 3.02로 고정했을 때 weak drive를 .08→1.06으로
높이면 full goal이 low→high로 바뀌었다. 반대로 weak=.08을 고정하고 strong을 4→3.02로
낮추면 full은 low를 유지했다. 따라서 R055 내부 입력의 high 전환에 strong 감소가 함께
필요하다는 설명은 이번 국소 대조에서 지지되지 않는다.

이는 고정된 numerical kernel, initial=.5, 두 strong 수준과 두 weak 수준에서 확인한
개입 효과다. 약한 입력 증가의 일반적 충분성, 연속적 전환점 또는 HCC 전체 가설의
증명으로 확장하지 않는다. strong 감소의 연속값 효과도 0으로 취급하지 않는다.

## 관찰

연구 run: `HCR-Evidence/exp37/r056-20260919T225912Z-e2821fd0a7`.
16행 모두 stable_decision으로 종료했다. 아래 goal은 여섯 자리로 표시했다.
stable_decision은 수치 종료 상태이며 native 채택 결과가 아니다.

| orientation | strong | weak | full goal | drop_P_prefix goal | full/drop |
|---|---:|---:|---:|---:|---|
| start | 4 | .08 | 0.026117 | 0.028676 | low/low |
| start | 4 | 1.06 | 0.987527 | 0.987487 | high/high |
| start | 3.02 | .08 | 0.026088 | 0.028655 | low/low |
| start | 3.02 | 1.06 | 0.987526 | 0.987486 | high/high |
| goal | 4 | .08 | 0.013283 | 0.986808 | low/high |
| goal | 4 | 1.06 | 0.987735 | 0.987694 | high/high |
| goal | 3.02 | .08 | 0.013247 | 0.986799 | low/high |
| goal | 3.02 | 1.06 | 0.987731 | 0.987691 | high/high |

full goal의 사전 단순차는 다음과 같다. strong 감소는 3.02−4 방향,
weak 증가는 1.06−.08 방향이다. 값은 기술량이며 통계 검정이 아니다.

| orientation | weak 증가, strong=4 | weak 증가, strong=3.02 | strong 감소, weak=.08 | strong 감소, weak=1.06 |
|---|---:|---:|---:|---:|
| start | +0.9614093770 | +0.9614380297 | −0.0000288600 | −0.0000002073 |
| goal | +0.9744513292 | +0.9744845574 | −0.0000364634 | −0.0000032352 |

P_prefix 삭제 효과(delta_goal=drop−full)는 weak=.08인 start에서 +0.002559/+0.002567,
goal에서 +0.973524/+0.973552였다(strong 4/3.02 순서).
weak=1.06에서는 두 방향과 두 strong 수준 모두 약 −0.000040이었다.
동결된 low 술어에 대한 필요성은 weak=.08의 start에서 false, goal에서 true다.
weak=1.06에서는 full부터 high이므로 필요성은 null이며 false로 바꾸지 않는다.

delta_goal의 사전 interaction=(d−c)−(b−a)는 start −0.0000083779163377,
goal −0.0000280565607532다. 0이 아니지만 수치 오차 경계나 통계적 유의성은
추정하지 않았다. 모든 full/dropout/delta의 표·단순차·interaction은 audit에 보존했다.

연구 분기만 합친 counter는 kernel ticks 892, signal transmissions 6,728,
group updates 4,460, normalization operations 4,460이다.
단위가 다른 counter를 합산하지 않았고 smoke·출처 replay를 연구 비용에 넣지 않았다.
실제 에너지는 미측정이다.

## 해석

R055에서는 weak 증가와 strong 감소가 동시에 일어났다. R056은 다른 drive를 고정한
대조를 추가해, 관측된 full의 low→high 전환이 strong 감소 없이도 나타남을 확인했다.
strong 감소만으로 같은 전환이 나타나지는 않았다. 이 구분은 두 orientation에서 같았다.

반면 P_prefix 삭제의 범주적 효과는 orientation에 따라 다르다.
weak=.08인 goal 방향에서만 full low/drop high 패턴이 두 strong 수준에 걸쳐 유지됐다.
이는 R054의 끝점 비대칭이 strong=4 한 점에만 국한되지 않음을 보여주지만,
그 비대칭의 원인이 bias·경로 길이·feedback 방향 중 무엇인지는 아직 구별하지 못한다.

주장 상태는 다음과 같이 갱신한다.

- `observed`: 고정된 두 strong 수준에서 weak 증가만으로 full low→high가 나타났다.
- `unsupported`: 이 전환에 strong 감소가 함께 필요하다는 국소 설명.
- `observed`: strong 감소의 연속값 효과는 존재하지만 이번 점들에서는 endpoint 범주가 유지됐다.
- `hypothesis`: 입력 포화, 초기 상태 의존성, bias 또는 feedback 경로가 비대칭을 설명한다.

## 대안 설명

단일 drive 개입은 총량도 바꾼다. 따라서 weak drive의 효과와 별도 총량 효과를 독립
원인으로 완전히 분해한 것은 아니다. 다만 R055와 이번 대각선의 동일 총량 4.08에서
서로 다른 endpoint가 재현되므로, 총량만으로 모든 endpoint를 정하는 설명은 맞지 않는다.

strong 쪽 edge의 최종 활성도가 높은 것은 포화 설명과 양립한다. 하지만 strong 범위를
더 넓게 조작하지 않았으므로 strong이 중요하지 않거나 영향이 없다고 주장하지 않는다.
현재 initial=.5 하나에서의 결과는 입력·구조가 유일한 종착점을 정한다는 설명과
초기 상태에 따라 다른 종착점에 도달할 수 있다는 설명을 모두 허용한다.
종료 tick이 서로 다르므로 endpoint 차이를 동일 tick의 효과나 계산 효율로 해석하지 않는다.

## 사후 토론과 다음 판별 실험

더 촘촘한 weak drive sweep은 전환 구간을 좁힐 수 있지만, 현재 관측을 같은 입력·program의
유일한 종착점으로 해석해도 되는지는 알려주지 못한다. 다음 우선안은 초기 상태 대조다.

- 입력은 startstrong=(4,.08), goalstrong=(.08,4) 두 개를 고정한다.
- full/drop_P_prefix 각각에서 모든 좌표의 초기 활성도를 .1/.5/.9로 바꾼다.
- 12행 중 initial=.5인 4행은 R056 전체 궤적 bridge, 나머지 8행은 새 대조다.
- program·drives·config·종료 규칙·tick budget을 유지하고, 초기 상태에 따른 전체 궤적과
  endpoint 차이를 사전 정의한다. budget/oscillation은 실패 유형으로 분리한다.

이 우선안은 main의 사후 판단이며 독립 패널 합의가 아니다. 다음 계약은 아직 동결·실행하지
않았다. 초기 상태 차이만으로 basin 경계, 수학적 attractor 또는 hysteresis를 증명할 수는 없다.
새 실험의 판정은 초기 상태 의존성의 관찰에 한정하고 더 강한 주장은 별도 검증한다.

## 현재 주장 가능한 범위

새 8개 off-diagonal 대조와 8개 재현 control은 결정론적 분기이며 독립 표본 16개가 아니다.
R052 native replay와 R055 궤적 replay는 provenance 검증이며 새 연구 증거로 중복 계산하지 않는다.
native packet/proof/support/raw decision/adoption/실제 에너지는 null이다.
외부 LLM 행동, hidden state, 인간 인지, 학습·Circuit 재사용 또는 HCC 전체 가설의 직접 증거가 아니다.

## 검증과 보존

- 오케스트레이션은 main이 직접 수행했다. 독립성은 생성기와 별도 프로세스·수식으로
  동작하는 numerical verifier에 한정하며, 독립 연구자·최종 Judge 감사를 수행했다고 하지 않는다.
- 개발 중 직접 unittest 호출은 root hcr.py가 src/hcr를 가리는 import 오류로 실패했다.
  기존 bootstrap 진입점으로 수정했고 22개 synthetic 검사가 통과했다.
  실패 원인과 명령은 `HCR-Evidence/r056-validation/development-checks.json`에 보존했다.
  실제 연구 조건이나 수식을 이 오류 때문에 변경하지 않았다.
- 원클릭 동결 source self-test 22개 통과, 별도 smoke 8행·8bridge 통과.
- 최종 core regression은 1회: 602개 중 599개 통과, 기존 Windows symlink 환경 skip 3개.
  새 실패·새 skip은 없다. skip을 pass에 포함하지 않았다.
- 실제 연구 16행의 모든 tick·최초 종료·counter와 R055 전체 궤적 bridge 8개 검산 통과.
  main도 raw endpoint에서 모든 좌표 delta와 6개 factorial 표·단순차·interaction을 대조했다.
- source 231개 동결 일치, bundle 555개 파일 hash, manifest 포함 ZIP 556개 파일의
  목록·CRC·원본 bytes 일치를 확인했다. ZIP 크기는 1,730,863 bytes다.
- 최초 원클릭이 정상 완료했다. 실제 연구 재시작·자동 retry·기존 raw 덮어쓰기는 없다.
  실행 후 검증 기록은 `HCR-Evidence/r056-validation/delivery-verification.json`이다.

Audit SHA-256: `8968cf2dfa2c7aa421379fc0a255b5fe3611af487643113955f3a7863ee02de4`.
ZIP SHA-256: `5c9fe6d785a38725a77c3c4d61b59f6127eac24a312ea1ca9afe379a23036260`.

원클릭은 `Run-HCR-R056.cmd`다. 이 문서는 사후 해석 기록이며 동결 source manifest에
소급해 넣지 않는다. 기존 core/tests/R050–R055 source·manifest·evidence는 보존했다.
