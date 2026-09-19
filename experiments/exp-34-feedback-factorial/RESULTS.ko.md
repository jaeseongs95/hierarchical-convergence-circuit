# EXP-34 / R053 결과

## 결론

강화 입력 두 조건에서 feedback 한 집합만 켜면 goal activation이 OFF보다 높아졌지만,
두 집합을 함께 켜면 낮아졌다. 따라서 현재 동결 커널의 낮은 goal 상태는
edge-local feedback 단독 억제로 설명되지 않는다. 사전 P1은 두 강화 조건 모두 반박됐다.
두 집합의 조건부 효과가 반전되고 큰 음의 상호작용 대비가 관찰됐다.
이는 수치 커널 결과이며 native proof·support·terminal adoption은 이번에 측정하지 않았다.

## 관찰

run: `HCR-Evidence/exp34/r053-20260919T143454Z-2703835cfd`

동결 checkout은 `cf89182a4f5d133b337795b5f8da5d9dac6a8fb2`다. 신규 R053 소스는
run의 `source/`, `source_manifest.json`, `R053_MANIFEST.json`으로 결속됐다.
현재 커밋 번호만으로 실행 당시 신규 소스를 대체하지 않는다.

E는 edge-local(A1→A0), P는 path-internal(A1→A1) feedback 각 두 링크다.
goal 값은 정답 확률이나 채택률이 아닌 activation이다.

| 입력 | OFF | E만 | P만 | E+P | goal 상호작용 대비 |
|---|---:|---:|---:|---:|---:|
| weakweak | 0.017257 | 0.022776 | 0.012075 | 0.011671 | -0.005922 |
| startstrong | 0.734164 | 0.964881 | 0.924059 | 0.026117 | -1.128658 |
| goalstrong | 0.934295 | 0.985129 | 0.984990 | 0.013283 | -1.022540 |

상호작용은 Y11−Y10−Y01+Y00다. 확률이 아니라 차이의 차이이므로 절댓값이 1보다 클 수 있다.
P2의 허용오차 내 0 여부 검사는 세 입력 모두 nonzero였다. 통계적 유의성 검정은 아니다.

| 강화 입력의 남은 약한 edge | OFF | E만 | P만 | E+P | 사전 P1 |
|---|---:|---:|---:|---:|---|
| startstrong의 e:1 | 0.551378 | 0.699820 | 0.551378 | 0.374908 | 반박 |
| goalstrong의 e:0 | 0.551378 | 0.706369 | 0.551378 | 0.385923 | 반박 |

P1은 E만으로도 약한 edge가 0.5 미만이 된다고 예측했다. 실제로는 두 집합이 모두 있을 때만
이 경계를 넘었다. 이 수치 경계를 proof 가정·support·adoption 판정으로 바꾸지 않았다.

12조건은 모두 kernel의 `stable_decision` 종료 상태였다. 이는 수치 margin·residual 조건의
이름일 뿐 native decision이나 올바른 채택을 뜻하지 않는다.
ticks는 weakweak 37/84/34/88, startstrong 47/114/76/60,
goalstrong 44/75/61/116이었다(각각 OFF/E/P/full 순서).
full/off 여섯 대조는 R052 원본의 전체 numerical trajectory·최종 상태·종료·kernel counter를 재현했다.

## 해석

startstrong에서 E의 goal 효과는 P가 없을 때 +0.230717, 있을 때 -0.897942였다.
P의 효과도 E가 없으면 +0.189895, 있으면 -0.938764였다.
goalstrong에서도 E 효과 +0.050834→-0.971706,
P 효과 +0.050694→-0.971846의 반전이 관찰됐다.
평균 주효과만 보고 어느 한 집합을 일관된 억제 원인으로 부르면 이 조건부 반전을 놓친다.

현재 두 강화 입력·초기 0.5·고정 종료 규칙에서는 낮은 goal 및 약한 edge의 0.5 미만 상태가
두 feedback 집합의 공동 존재에 의존했다. 각 집합 단독은 full의 낮은 상태를 재현하지 못했다.
이는 동결된 계산 장치 안의 집합 제거 대조에 한정된 관찰이다.

## 대안 설명

네 개 중 특정 feedback 링크 또는 닫힌 경로가 중요할 수 있고, nonlinear update와
초기 transient가 다른 안정 상태로 전개되게 했을 수도 있다. 집합별 2×2 대조만으로
개별 링크 필요성, 유일한 고리, 여러 attractor의 존재나 basin 경계를 확정하지 않는다.
모든 링크 가중치가 양수여도 전달 신호는 `2*state-1`이므로 feedback의 실제 기여는
source 상태에 따라 양수·음수가 된다. 링크 종류 자체가 항상 억제라는 해석은 부적절하다.

표는 같은 tick이 아니라 각 실행의 종료 시점 값이다. E가 꺼진 두 조건의 edge 입력 방정식은
P에 영향을 받지 않지만 종료 tick이 달라 1e-8~1e-10 수준의 endpoint 차이가 남을 수 있다.
이 작은 차이를 별도 경로의 직접 신호 효과로 해석하지 않는다. replay 허용오차 1e-12는
실행 검산 기준이고 residual 종료 기준 1e-6이나 asymptotic fixed-point 오차 한계와 같지 않다.

## 판별 실험

후속 후보는 full에서 feedback 링크를 하나씩 제거하는 사전등록 대조다.
두 강화 입력과 동일 초기 상태를 유지하면 어느 링크 제거가 낮은 goal 상태를 깨는지
집합 수준보다 더 좁힐 수 있다. 이는 단일 링크의 현재 조건 내 필요성 대조이지
attractor/basin이나 native 채택을 입증하는 실험이 아니다. 아직 구현·실행하지 않았다.
초기 상태·gain 대조와 native proof/adoption 연결은 별도 질문으로 남긴다.

## 현재 주장 가능한 범위

R052에서 동결한 2-edge ++, path-order network, 세 drive, default config,
초기 0.5에 대한 12개 결정론적 counterfactual branch다. 독립 표본 12개가 아니다.
부모 여섯 execution의 native 검산은 출처 확인이지 새 mask의 native 결과 측정이 아니다.
모든 새 record의 native packet/proof/support/raw decision/adoption은 null이다.
학습·회로 재사용·일반 topology·인간 인지·에너지 효율로 일반화하지 않는다.

## 검증 및 비용

- 원클릭 1회, exit 0. 본 연구 12조건과 R052 수치 bridge 6개 모두 독립 audit 통과.
- 봉인 소스 자체 테스트 14/14. 별도 implementation_validation smoke 4조건/2bridge 통과.
- 최종 core 회귀 1회: 602개 실행, 599개 통과, 기존 Windows symlink skip 3개.
  실패·오류·새 skip 0, 로그 기준 145.102초. skip을 pass로 세지 않았다.
- 연구 kernel ticks 836, signal transmissions 5,288, group updates/normalization ops 각각 4,180.
  단위가 다른 counter를 총 비용 하나로 합치지 않는다. 실제 에너지는 미측정이다.
- audit SHA-256: `7f398978d3dfc299653ce35e2212d4067b6d895b2c89b7482fddefb364f663b3`.
- bundle manifest가 결속한 415개 파일과 manifest 자체까지 총 416개 파일의
  ZIP CRC/inventory·로컬/ZIP SHA-256을 확인했다. ZIP 1,399,969 bytes.
- 본 연구 실패·자동 retry 없음. 예측 P1이 반박된 뒤 조건·평가기·소스를 바꾸지 않았다.
- 기존 core/src/tests와 R048~R052 소스·manifest·원자료는 보존했다. 기본 dispatcher EXP-30 유지.
- staging된 evidence 416개 파일의 Git blob이 로컬 원본 bytes와 같음을 확인했다.
  봉인한 과거 소스의 CRLF·Markdown 줄바꿈 공백·기존 EOF 빈 줄 때문에 전체 diff-check에
  경고가 남지만 evidence를 재포맷하지 않았다. 신규 소스·문서의 diff-check는 별도로 확인했다.

설계의 독립 초기 검토·교차검토와 모델 적용 관측 한계는 DISCUSSION.ko.md,
실행 전 수정은 IMPLEMENTATION_REVIEW.ko.md에 기록했다.

## 결과 후 토론

r053_causal이 audit와 12개 raw record를 읽기 전용으로 검토했다.
P1 반박·집합 수준 음의 상호작용 해석에 동의했고, 단일 초기 상태로 attractor/basin을
식별할 수 없으며 자체 종료 endpoint를 동일 시각 효과나 전체 효율로 읽으면 안 된다고 지적했다.
후속은 single-link leave-one-out을 먼저 권고했다. 한 강화 입력만 쓰면 진단적 사례로 제한하고,
두 강화 입력의 차이를 놓치지 않도록 이 문서에서는 두 입력을 유지하는 후보로 정리했다.
이 재검토는 새 blind panel·독립 재실험·fresh Judge가 아니며 추가 연구 표본으로 세지 않는다.
