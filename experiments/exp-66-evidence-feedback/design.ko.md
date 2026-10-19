# EXP-66 / r20: 불확실성·보조측정 lineage에 따른 피드백 허용 조건

## 질문과 범위

r19는 모호한 하위 출력을 문맥 방향으로 결정할 수 있었지만 잘못된 문맥도 오답으로 전파했고, 무조건 피드백의 tick은 312→676으로 늘었다. 이번에는 **어떤 공개 정보가 있을 때 추가 상위 계산·피드백을 허용할지**와 그 품질/계산 비용을 비교한다. 실제 회로 학습·재사용 절감 실험과 중복해 주장하지 않는다. 이전 조건 일부는 새 gate의 기준선으로 다시 사용하며 독립 발견 표본으로 세지 않는다.

기존 r19의 두 Program과 `hcr.dynamics.tick/settle`을 그대로 쓴다. 하위는 두 feature의 A/B 분류, 상위는 category confidence/context의 XNOR이다. kernel·gain은 r19와 같고 학습 0회다. 새 코드는 task wrapper와 검산뿐이며 src·r19 source/봉인은 바꾸지 않는다.

## 사전 고정 정책

모든 public input은 id, revision, measurement 두 값, 역할 ID f0/f1, ±1 context, 선택적인 aux packet만 가진다. hidden truth는 reference.json에서 audit만 읽는다. id·case key로 정답이나 행동을 고르지 않는다.

1. 하위가 `stable_decision`이면 상위 관계를 한 번 계산하고 피드백을 생략한다. 문맥과 충돌하더라도 현재 안정된 하위 출력을 문맥만으로 뒤집지 않는 보수적 규칙이다.
2. `stable_ambiguous` 외의 미수렴 상태는 보류한다.
3. 하위가 모호하면 aux가 등록된 `aux_sensor` 출처인지, revision이 같은지, aux의 measurement IDs/명시된 parents가 f0/f1과 겹치지 않는지, `abs(score)>=0.8`인지, score 방향과 context가 같은지를 순서대로 검사한다.
4. 모두 통과한 경우만 기존 상위 match_A−match_B 신호를 고정 1회 하위에 보내 하위·상위를 재계산한다. 거부하면 상위 settle·승격도 생략하고 분류/관계 모두 보류한다.
5. 최종 하위가 보류하면 상위 관계도 채택하지 않는다. 모든 승격은 전체 public input hash, 하위 trace hash, revision·measurement·uncertainty와 gate hash를 묶는다.

0.8은 작은 합성 실험에서 강한 측정 크기를 구분하기 위해 사전에 고정한 경계다. 정답 신뢰도 80%를 뜻하지 않으며 학습·교정된 threshold가 아니다. metadata의 출처·lineage 분리도 **선언된 기록상의 분리**다. 실제 센서 인증, 숨은 공통 원인의 배제, 통계적 독립성이나 진실성을 증명하지 않는다. 모든 측정은 사전에 만든 합성 입력이다.

## 11개 조건과 세 방식

| key | 공개 조건 | reference 분류/관계 |
|---|---|---|
| clear_A | 강한 A feature, +context, aux 없음 | A / 일치 |
| clear_B | 강한 B feature, −context, aux 없음 | B / 일치 |
| revision_0 | feature 0/0, −context, aux 없음, revision 0 | A / 불일치 |
| derived_aux | feature 0/0, −context, score−1 aux의 parent가 f0 | A / 불일치 |
| independent_A | feature 0/0, +context, 같은 revision·분리된 aux+1 | A / 일치 |
| independent_B | feature 0/0, −context, 같은 revision·분리된 aux−1 | B / 일치 |
| conflicting_aux | feature 0/0, −context, 분리된 aux+1 | A / 불일치 |
| stale_aux | feature 0/0, −context, revision 1에 revision 0 aux−1 | A / 불일치 |
| independent_wrong | independent_B와 id 외 공개 정보 동일, reference만 다름 | A / 불일치 |
| strong_conflict | 강한 A feature, −context, 분리된 aux−1 | A / 불일치 |
| revision_1 | revision_0과 같은 id·context, 새 revision 1의 강한 A feature | A / 불일치 |

`bottom_up`은 항상 하위/상위 2 settle, `unconditional`은 항상 4 settle, `gated`는 하위 1 settle 뒤 정책에 따라 총 1/2/4 settle을 쓴다. 정책은 상위 계산 전에 결정한다. graph 객체는 세 방식 모두 두 Program을 구성하므로 그 비용이 사라졌다고 주장하지 않는다. gate·hash·adapter·출력 직렬화 비용도 존재한다.

`independent_B`/`independent_wrong`은 aux까지 같으므로 둘을 모두 맞히도록 요구할 수 없다. gate가 출처 조건을 통과한 잘못된 근거를 여전히 받아들이는 반례를 숨기지 않는다. `revision_0`→`revision_1`은 실제 measurement가 바뀐 두 실행이다. 각 실행은 .5에서 새로 시작하고 메모리 학습이 없으므로 이를 수정 기억 유지·학습으로 해석하지 않는다.

## 측정과 판정

11×3=33개 cell을 각각 한 번만 실행한다. native settle은 최대110회이며 0회 학습, parameter 탐색·seed 반복·결과 기반 수정은 없다. 준비 1→case33→audit1의 35개 단계다.

- 기능: 분류/관계의 정답·오답·보류를 분리한다. gated의 보류 시 관계 채택 금지, 각 gate 사유와 실행 경로를 검사한다. 분리된 잘못된 aux를 받은 오답도 정상 관측으로 보존하며 전 사례 정답을 완료 조건으로 삼지 않는다.
- 비용: 실제 settle/tick/group update/signal transmission, promotion/output bytes, gate predicate 수·gate wall, cell child CPU/wall을 보고한다. adapter vector 수는 생성된 벡터의 수이며 모든 Python 연산을 센 값이 아니다. child CPU에는 import·graph 구성·정책·hash·직렬화가 포함된다. 이 작은 단일 관측으로 통계적 CPU/금전/에너지 우위를 주장하지 않는다.
- 검산: 기존 별도 scalar 수식으로 매 tick, 종료·판정·비용을 재생한다. Program은 `plain`으로 JSON 정규화한다. 입력·gate·drive·승격 연결과 paired-world 동일 예측을 정확히 검사한다. gate action, 승격 revision/값, tick state, program bias 변조 5종을 거부해야 한다.
- 허용치: **동일 서버 수식 검산은 절대오차 0**, Windows 등 별도 호스트의 보조 재생은 절대오차 1e-15·상대오차 0으로 실행 전에 고정한다. 근거는 r19의 동일 수식에서 관측한 최대 1.694e-21 차이를 포괄하면서 커널 정지 기준 1e-6보다 9차수 작은 경계라는 것이다. 형식적 반올림 오차 상한 증명은 아니다. discrete 필드·Program·drive·gate·provenance는 계속 정확히 대조한다.

## 실행·보존

AI Research SSH의 새 전용 `/home/mcpops/hcc-evidence-feedback-20261019-r20`만 사용한다. 전체600초, 순차1, stage60초, child 주소공간512MiB, raw128MiB, 자동 retry0이다. 실패 자료는 보존하며 결과를 보고 반복하지 않는다. source 전후 hash는 audit 성공 여부와 관계없이 기록한다.

로컬/서버 preparation은 공개 경계와 synthetic stub 분기, r19 저장 trace의 새 감사 경로를 검사한다. **새 native tick/settle을 호출하지 않으며 stub cell을 실험 결과로 세지 않는다.** 실제 관측은 서버 case 단계에서만 얻는다. 원자료·source manifest·검산·CPU/wall·봉인 ZIP 해시와 수신 범위를 남긴다.

이 실험은 조건부 피드백 계약의 기술 확인이다. 일반화·학습 효율·품질 보존 보증·native AdaptiveSession adoption·primitive route proof·자율 계층 형성의 증거가 아니다. 모델 입력에 없는 참/거짓을 metadata 검사로 알아낼 수 있다고 주장하지 않는다.
