# EXP-09 — R0.2 기준선의 저장·학습·측정·비용 분리

명세 버전: `exp09-baseline-paired-v1`  
대상 엔진: 기존 0.2.0 그대로  
상태: 명세·도구 작성. 새 비교 실험은 아직 실행하지 않았다.

## 1. 목적과 연구 단위

로드맵 §6.3의 다섯 질문을 분리한다. 기존 36개 판단에는 training·frozen evaluation·오류 수정 attempt가 섞여 있으므로 전체 정답률 하나로 합치지 않는다. 동일 개발 사례를 반복 실행한 값을 독립 일반화 표본으로 세지 않는다.

현재 확인된 사실은 사용자 로그의 136개 테스트와 R0.2 demo/audit 통과다. 새 도구가 그 결과를 대체하지 않는다. 새 probe의 protocol은 기존 `r02-authored-path-motifs-v1`과 다르다.

## 2. 두 종류의 작업

**원시 기록의 재집계(`collect.py`)**는 기존 `runs/r02_first`를 읽고 source/plan/checkpoint/trace/summary를 연결한다. 파일 해시, event chain, 판단 행·trace 대응, 요약 집계, 비용 별칭, signal 항목 분해를 확인한다. HCR 엔진이나 수치 감사기를 import/실행하지 않는다.

**짝지은 새 실행(`probe.py --execute`)**은 동결된 실행 소스로 기존 run의 원 독립 audit를 먼저 수행한다. 이후 EXP-09에 해당하는 새 추론·외부 평가·feedback·측정을 별도 출력 폴더에 기록한다. 원 run이나 checkpoint를 수정하지 않는다.

## 3. 고정 조건

| 조건 | 규칙 |
|---|---|
| 코드 | bundle의 `source/`만 import. 원 plan의 source hash와 일치해야 함 |
| 설정 | 원 plan의 `config`·`config_signature` 그대로 |
| 표현·방법 | R0.2의 두 고정 A 수준과 기존 수렴식 유지 |
| topology | 동일 chain3 conflict. input/control마다 같은 edge ID·순서·start/goal |
| weak 측정 | 원 `misconvergence/full` 최초 관측에서 취함 |
| measured 측정 | 같은 trajectory의 실제 최종 revision 관측에서 취함 |
| truth | 원 기록의 외부 truth. engine에는 전달하지 않음 |
| 새 episode | 비교 조건을 담지 않는 `e900001`/`e900002`; 동일 쌍은 같은 값 |
| frozen matrix | 새 engine + 동일 memory 복사. feedback 없음 |
| learning trajectory | 기존 Mode.ADAPT와 request_revision/World.measure 계약만 사용 |
| 결과 | 오수렴·수정·비용감소가 나오지 않아도 그 결과를 보존 |

`measured` 조건은 실험자가 제공하는 **강한 관측을 가진 새 과제**다. 해당 frozen trial에서 엔진이 스스로 측정을 요청했다고 기록하지 않는다. 실제 revision trajectory와 이 통제 조건을 별도 phase로 둔다.

## 4. 질문 A — save/load의 행동 동등성

먼저 기존 training6 checkpoint에서 새 adaptation trajectory를 재현해 **실제로 존재하는 live RAM memory 객체**를 만든다. 원 사용자 프로세스의 RAM memory를 복구한 것처럼 표현하지 않는다.

그 객체를 파일로 저장·load하고 아래 두 조건을 같은 새로운 weak 관측에서 비교한다.

| 조건 | memory 출처 | 입력 |
|---|---|---|
| direct | live adaptation 후 객체의 deepcopy | 동일 새 weak 입력 |
| reload | 그 live 객체를 save/load한 결과의 deepcopy | 동일 새 weak 입력 |

비교에서는 `decision.id`와 `decision.cost.wall_seconds`만 제외한다. proof, 실제 activation state, primitive D, circuit ID, memory version, operation counters, 판단값, 안정상태는 모두 비교한다. 도구가 별도 측정한 copy/init/save/load 시간은 참고 측정값이며 동등성 판정에 사용하지 않는다.

**판정은 두 개다.** `behavior_equal`은 저장·복원의 행동 보존이고, `correct`는 문제 해결 결과다. 둘 다 오답이어도 동등할 수 있다. memory digest 불일치는 계약 오류로 중단하고, 행동 불일치는 감추지 않고 결과 필드로 보고한다.

## 5. 질문 B/C — memory·정보·routing의 분리

다음 2×2×2의 8개 조건을 실행한다.

| 요인 | 값 |
|---|---|
| memory | 원 `memory_after_training.json` / 원 `memory_after_adaptation.json` |
| 관측 | weak / measured |
| 회로 사용 | on / off (`use_circuits=False`) |

**memory 효과:** 같은 weak 관측과 같은 routing에서 before/after를 비교한다. 특히 circuit on의 최초 출력·회로 ID·안정성·비용을 본다.

**추가 정보 효과:** 같은 memory와 routing에서 weak/measured를 비교한다. 이 조건에서의 강한 관측 제공은 실험 지원 정보로 명시한다.

**routing 효과:** 같은 memory와 관측에서 circuit on/off를 비교한다. 기존 `no_reexpansion`은 추가 관측과 재계산도 동시에 끄므로, 그것만으로 이 세 요인의 효과를 분리하지 않는다.

이 비교에서 달라지는 결과는 해당 유한 개발 조건에서의 대조 효과다. memory 안의 여러 필드가 함께 바뀐 before/after 차이를 곧바로 strength 한 필드의 단독 인과효과로 부르지 않는다.

## 6. 질문 D — 압축의 위치와 실제 비용

새 inference를 만들지 않고 기존 familiarity의 각 `case`에서 cold/warm 행을 정확히 하나씩 대응시킨다. 두 행의 공개 관측과 외부 truth가 같아야 한다.

| 비용 구획 | 원래 항목 / 추가 분해 |
|---|---|
| dependency | graph_nodes_created, graph_edges_created, expansions, topology_edge_checks |
| matching | binding_operations, binding_checks, recall_checks, candidate_circuits |
| pool | pool_calls, pool용 tick·signal·group update |
| decision signal | decision용 tick·signal·group update |
| proof | proof_nodes_reconstructed; primitive D는 별도 품질·구조 지표 |
| 외부 검증 | assessment.verification_checks; 내부 cost와 분리 |
| learning | r02_memory_updated의 비용을 해당 decision/arm에 귀속 |
| 저장 | storage_bytes와 checkpoint 실제 bytes 구분 |
| 시간 | 기존 infer wall_seconds; 새 probe의 copy/init/load/save/assessment 시간 별도 |

pool/decision tick·signal 분해는 기존 `r02_network.kind`와 `r02_tick`에서 계산한다. tick 수×해당 network의 활성 link 수로 signal count의 내역을 재집계하며, 원래 총카운터와 일치하는지 확인한다. 이는 tick의 수치값 전체를 독립적으로 재계산하는 검사가 아니다.

별칭 네 쌍은 일치 검사 후 중복 제거한다. 서로 다른 단위를 더해 “총 연산량” 점수를 만들지 않는다. 기존 run에서 초기화·load·측정 비용이 측정되지 않았다면 `unmeasured`로 남긴다.

**완료 판정:** 정확도/strict proof/D와 각 비용 delta가 기록되어 있을 것. 비용이 증가하는 결과도 그대로 수용한다.

## 7. 질문 E — training3/6/9와 수정비용

원 protocol의 checkpoint 세 개를 재사용한다.

| 경험 수 | 파일 |
|---:|---|
| 3 | memory_training_3.json |
| 6 | memory_after_training.json |
| 9 | memory_training_9.json |

같은 새 weak 입력, 같은 config, 같은 ADAPT 및 측정 정책에서 각각 독립적으로 복사한 memory를 사용한다. 최초와 수정 attempt를 모두 보존한다. 오류가 없거나 측정 요청이 없으면 임의 수정 경로를 만들지 않는다.

attempt 수 외에 inference·feedback 비용, 실제 관측 요청, 최초/최종 판단·proof·회로를 비교한다. training 단계의 원래 비용은 기존 raw run의 해당 phase에서 별도로 얻는다. 기존 checkpoint 재사용을 새로 3/6/9회 학습한 실행으로 세지 않는다.

경험 수가 달라지면 strength뿐 아니라 evidence_count와 balance, 회로별 이력도 달라진다. 이 실험은 경험 축적 조건의 비교이며 weight 하나만 조작하는 실험이 아니다.

## 8. 기록과 검증 경계

수집 결과는 원 run의 **파일/chain/집계 검증**을 포함한다. 원 `verified=true` receipt와 구분해 `independent_numerical_audit_executed=false`로 기록한다. 필요하면 동결 source의 `hcr.py verify`로 원 run 수치 감사를 다시 수행한다.

probe는 실행 전에 원 run의 원 독립 audit 통과를 요구한다. 새 probe 자체에는 기존 외부 proof/reference 검증, 추론 중 memory 불변 검사, live roundtrip 검사, event hash chain, 소스·bundle 불변 검사를 적용한다. 그러나 **새 protocol 전체를 위한 별도 독립 수치 auditor를 구현한 것은 아니다.** 따라서 `full_independent_probe_audit_performed=false`이며 기존 `hcr.py verify`에 probe 폴더를 넘기지 않는다.

후속 연구에서 probe 전체의 독립 수치 감사가 필요하면 새 protocol을 명시적으로 지원하는 auditor를 추가한다. schema 이름만 원 demo로 바꿔 기존 검사를 우회하지 않는다.

## 9. 실패·중단 규칙

원시 파일 누락/추가, source hash 불일치, source/run 변경 감지, alias 불일치, 동일쌍 입력 불일치, frozen memory 변경, 무허가 revision 등은 실행 또는 수집 실패다. 기존 기록은 보존하고 새 결과 폴더에 완료 manifest를 만들지 않는다.

반면 안정 오답, 보류, 비용 증가, 학습 후 재오답, save/load의 동일한 오답은 계약 위반과 구분해 관찰 결과로 보고한다. 기대한 현상이 없다고 데이터를 수정하지 않는다.

## 10. R0.2.1과의 경계

EXP-09는 기존 엔진의 행동을 설명하기 위한 기준선 진단이다. generation ID, persistent activation, snapshot/resume, 새로운 compiler나 학습 규칙은 추가하지 않는다. 기준선과 그 미해결 질문이 문서·증거에 남으면 R0.2.1에서 상태 실행 계약을 별도 변경으로 진행할 수 있다.
