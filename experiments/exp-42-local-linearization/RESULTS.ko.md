# EXP-42 / R061 결과

## 결론

R060 low 상태의 한 단계 일시 증폭은 국소 선형항으로 설명되는 결과를 얻었다.
교란 epsilon을 1e-4에서 1e-6으로 줄여도 32개 방향 중 같은 8개 방향에서
증폭이 관측됐고, 최대 증폭률은 analytic Jacobian의 예측에 가까워졌다.
검사한 두 anchor 모두 가장 작은 epsilon에서 사전 gain 일치 기준을 충족했다.

한 단계 선형 근사 일치는 `observed`, R060 증폭의 국소 선형 설명은
`partially-supported`로 기록한다. 장기 안정성이나 basin을 판정한 결과는 아니다.

## 관찰

기준 commit은 `5fcdbb3f44cfe14628a65971b3fe916b0169536d`다.
[설계](design.ko.md)와 [조건](frozen_spec.json)을 실행 전에 동결했다.
연구 run은 `HCR-Evidence/exp42/r061-20260920T003940Z-3ecb1ce52b`이며 실행은 한 번이다.
두 anchor 각각 32개 부호 방향 × 세 크기와 대조 하나, 총 194 branch를 검사했다.
모든 시작 좌표는 약 0.0131833부터 0.9999925 안에 있었으며 clipping은 없었다.

| anchor | epsilon | 최대 실제 증폭률 | 증폭 방향 수 | 최대 선형 근사 오차 |
|---|---:|---:|---:|---:|
| low | 1e-4 | 1.0650183655 | 8/32 | 1.9767609e-8 |
| low | 1e-5 | 1.0648404542 | 8/32 | 1.9764876e-10 |
| low | 1e-6 | 1.0648226658 | 8/32 | 1.9764854e-12 |
| high | 1e-4 | 0.7720041801 | 0/32 | 1.0278395e-8 |
| high | 1e-5 | 0.7719116720 | 0/32 | 1.0275873e-10 |
| high | 1e-6 | 0.7719024237 | 0/32 | 1.0276121e-12 |

증폭률은 같은 anchor의 무교란 대조에 대한 한 단계 L-infinity 거리/실제 초기 거리다.
최대 선형 근사 오차는 `||ΔF-Jδ||∞`를 각 anchor·epsilon의 32개 방향에서 최대화한 값이다.
Jacobian의 최대 절대 행합은 low `1.0648206894`, high `0.7719013961`이었다.
전체 32개 부호 방향의 최대 선형 증폭률도 각각 이 값과 일치한다.
가장 작은 epsilon의 최대 실제/명목 선형 gain 차이는 low 약 `1.9765e-6`,
high 약 `1.0276e-6`으로 사전 기준 `1e-4` 이하다.

epsilon을 10배 줄일 때 각 anchor의 최대 선형 근사 오차는 약 100배 줄었다.
이는 세 검사 크기에서 관찰한 이차 오차 경향이며 무한히 작은 epsilon에 대한
경험적 차수 증명은 아니다. 두 대조의 상태와 비용도 별도로 보존했다.

연구 비용은 kernel_ticks 194, group_updates 970, normalization_ops 970,
signal_transmissions 1,552다. 단위가 다른 counter를 합치지 않는다.
anchor replay·smoke·Jacobian 계산·검산 비용은 이 kernel 비용에 합산하지 않았다.

## 해석

R060에서 남은 “증폭이 유한 크기 비선형 효과에만 의존한다”는 설명은 이번 관찰과
맞지 않는다. analytic 선형항 자체가 low에서 1보다 큰 방향 증폭을 예측하며,
실제 작은 교란의 결과가 그 값에 가까워졌다. 비선형 보정은 여전히 존재한다.

low Jacobian의 최대 행은 `p:0:0` 출력이다. `e:0`, `p:0:0`, `p:0:1` 입력의
계수 약 0.399861, 0.594984, 0.069976이 합쳐져 약 1.064821이 된다.
이는 이 갱신식에서 여러 입력 변화가 합산되어 한 단계 증폭을 만들 수 있음을 설명한다.
R059의 축 방향 결과, R060의 복원 결과와 양립한다. 한 단계 norm이 1보다 크다는
사실만으로 장기 불안정성을 결론내릴 수 없다.

R060의 복원 관찰은 유지하며, 그때의 일시 증폭 원인 설명을 좁혔다.
같은 anchor와 결정적 recurrence를 사용했으므로 독립 반복 표본으로 세지 않는다.

## 대안 설명

유한 크기에서의 비선형 기여와 부동소수점 오차는 남아 있다. 실제 δ와 명목 부호
벡터를 분리했고, 생산 미분기는 별도 고정밀 식 및 synthetic 중앙차분으로 검산했다.
그래도 모든 수치 구현의 공통 개념 오류를 배제한 독립 연구자 검증은 아니다.
이번 결과는 다른 상태·parameter·norm·다단계 궤적의 민감도를 구별하지 않는다.
high의 작은 한 단계 norm을 더 넓은 basin이나 더 좋은 정답으로 해석하지 않는다.

## 판별 실험

다음 후보는 두 anchor의 Jacobian 거듭제곱 `J^k`가 예측하는 여러 단계의
방향별 차이와 같은 작은 교란의 실제 궤적을 사전 horizon에서 비교하는 것이다.
한 단계 증폭 후 감소가 고정점 주변 선형 전파로도 설명되는지, 시간이 흐르면서
비선형 효과가 필요해지는지 구별한다. 이번 턴에는 새 다단계 연구를 실행하지 않았다.

## 현재 주장 가능한 범위와 검증

고정 synthetic recurrence의 두 anchor·세 epsilon·32개 부호 방향·한 단계에 한정한다.
장기 수렴, basin 경계, 수학적 attractor, 학습된 Circuit 형성·재사용, LLM 내부나
인간 인지에 관한 직접 증거가 아니다. native packet/proof/support/raw decision/adoption과
실제 에너지 소비는 null이다.

- synthetic·변조 검사 15개와 별도 smoke 8개 통과.
- 최종 core regression 1회: 602개 중 599개 통과, 기존 Windows symlink skip 3개 유지.
- R052 원래 program과 R058 두 anchor의 512 tick 출처 재계산 통과.
- 194개 개입·한 단계·residual·counter·비용 및 analytic Jacobian 검산 통과.
- 별도 프로세스의 생산기/runtime/dynamics/생산 미분기 import 금지 확인.
- source 320파일, bundle hash 대상 899파일, ZIP 900파일의 목록·내용·무결성 확인.
- raw로부터 방향별 선형 오차·gain·집계를 다시 계산하고 기존 index 항목 보존 확인.

근거는 run의 `analysis/audit.json`, raw와 manifests,
`HCR-Evidence/r061-validation/delivery-verification.json`이다.
연구·synthetic 검사 실패는 없었다. 계약 검증 CLI 최초 인수 형식 오류는 별도 보존했다.
이 문서는 실행 후 해석이며 동결 source와 bundle을 소급 변경하지 않는다.
