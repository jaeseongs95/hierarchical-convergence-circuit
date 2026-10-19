# EXP-68 / r22 결과: 새 측정의 상호 지지와 채택 손실

2026-10-19 KST. AI Research SSH에서 고정한13개 합성 입력×3정책, 총39조건을 한 번 실행했다. **두 측정의 공개 계보 분리와 feature별 일치를 요구하면 단일 측정 대비 오답은4→2개로 줄었지만 정답도8→3개로 줄었다.** 전체 tick은830→434로 줄었고 측정 요청은11→18회로 늘었다. 보류를 늘린 정책의 비용·품질 절충이며 품질 보존이나 전체 효율 우위는 입증하지 않았다.

## 실행·검산·감사 지적 반영

준비1·case39·audit1의41단계가 모두 exit0으로 끝났다. 봉인 포함5.254357456초, 실제 native settle81회·World.measure29회·native tick1,530개로 전체600초·상한260회/39회 이내다. 학습0·threshold 탐색0·자동 재실행0이며 결과를 보고 실행 코드·입력·기준을 바꾸지 않았다.

서버 준비208개 assertion은 새 native 실행과 측정 없이 통과했다. 실제39개 기록의 초기·재추론 tick·종료·판정·비용을 기존 별도 scalar 수식으로 재생했고 사전 서버 절대오차0에서 통과했다. 로컬 보조 재생도 사전 절대오차1e-15·상대오차0에서 최대 차이0이었다. 로컬 재생 중 새 tick/settle·World.measure를 금지했으며 새 실험이나 성능 표본으로 세지 않는다.

변조10종은 각각 지정된 거부 사유까지 일치했다. request gate→`request gate binding`, request revision→`request binding`, charge→`measurement charge ledger`, response score→`provider response binding`, adoption action→`adoption binding`, request cap→`request cap`, unit cap→`measurement unit cap`, revision budget→`revision reservation`, 상위 tick→`scalar replay tick mismatch`, 상위 program bias→`fixed program`이다. 상위 trace를 변조해 앞선 하위 hash 검사가 더 깊은 검사를 가리는 경로를 피했다. request/unit/revision cap 변조는 full-record 검산에서 해당 거부 분기까지 도달했다.

r21 감사의 미시험 전역 상한에는 준비 단계에서 초과 카운터를 global_caps 함수에 직접 넣어 요청/settle 거부 사유를 각각 확인했다. 이는 실제39행 전체를 변조한 전역 감사 통합 시험이 아니다. nonzero rc와 raw 크기 초과를 함께 반환하는 stage_violations 사례도 pure 검사했다. 이번 실제 서버 단계는 모두 성공했으므로 OS 자원 초과·강제 실패·SIGTERM을 주입해 그 실패 경로를 실측한 것은 아니다.

부모 실행 프로세스의 실제 주소공간 soft/hard 한도512MiB·개별 파일32MiB, 준비 worker의 실제 주소공간512MiB·개별 파일16MiB를 각각 result/preparation에서 확인했다. 각 worker를 생성하는 동일 코드 경로에서 자식 한도를 적용한다. 모든 case에서 getrlimit을 별도로 기록한 것은 아니며, AS 한도는 실제 resident RAM 사용량 측정이 아니다.

## 전체13입력 품질

| 정책 | 분류 정답 | 오답 | 보류 | 관계 정답 | 오답 | 보류 |
|---|---:|---:|---:|---:|---:|---:|
| no_query | 1 | 2 | 10 | 1 | 2 | 10 |
| single_contract | 8 | 4 | 1 | 8 | 4 | 1 |
| corroborated | 3 | 2 | 8 | 3 | 2 | 8 |

세 정책은 초기 r20 gated를 모두 실행한다. single_contract와 corroborated의 요청 조건은 r21과 같은 초기 primary `stable_ambiguous`다. 이번에는 새 측정을 언제 요청할지 다시 비교하지 않고, 받은 측정의 채택 조건을 비교했다. 안정된 primary 오답은 세 정책 모두 요청하지 못했다.

corroborated의 채택 조건은 허용 source·request hash·episode·다음 revision·측정 대상의 계약 일치, 서로 다른 선언 acquisition/root 집합, 모든 feature 절대 score0.8 이상, 대응 feature별 부호 일치다. 0.8은 기존 r20 aux 상수를 가져온 규칙이며 신뢰도 calibration 결과가 아니다. witness는 primary의 채택 여부만 판단하며 값의 평균·합산이나 inference 중복 주입은 하지 않았다.

| 조건 | 단일 측정 → 이중 측정의 최종 분류 | 확인된 행동 |
|---|---|---|
| clear_A | A 정답 → A 정답 | 모든 정책 요청 없음 |
| repair_aux_A | A 정답 → A 정답 | 초기 aux 오답B를 두 정책 모두 교정 |
| missing_aux_A | A 정답 → A 정답 | 정상 측정 채택 |
| primary_flipped_A | B 오답 → 보류 | witness와 feature 방향 불일치 |
| witness_flipped_A | A 정답 → 보류 | 나쁜 witness가 올바른 primary 채택도 막음 |
| both_wrong_A | B 오답 → B 오답 | 두 측정이 함께 틀리면 선언 분리·일치 조건을 통과 |
| declared_overlap_A | B 오답 → 보류 | 공개 root 겹침을 거부 |
| stale_witness_A | A 정답 → 보류 | witness revision 오류 |
| no_information_A | 보류 → 보류 | 첫 score0/0의 강도 부족; 단일 정책은 재추론 후에도 보류 |
| weak_witness_A | A 정답 → 보류 | witness +0.2/+0.2는 강도 기준 미달 |
| request_budget_A | A 정답 → 보류 | 이중 정책은 요청2회 예약을 못 해 제공자 호출 전에 거부 |
| feature_budget_A | A 정답 → 보류 | 이중 정책은 feature4단위 예약을 못 해 제공자 호출 전에 거부 |
| strong_primary_wrong_B | A 오답 → A 오답 | 요청 조건 불충족으로 새 정보 접근 없음 |

이중 정책에서 남은 오답은 both_wrong_A와 strong_primary_wrong_B다. source 이름·revision·선언 계보가 맞고 두 응답이 일치해도 truth는 보장되지 않는다. root는 두 새 응답 사이의 선언을 비교하는 필드이며 실물 인증이나 초기 관측까지 포함한 독립성의 검증이 아니다. reference/fault mode는 audit 전용이며 정책에 전달하지 않았다.

이 표본은 실패 경로를 확인하도록 만든 합성 집합이다. 모집단 정확도·통계적 일반화 성능을 추정하지 않는다. 분류와 관계의 수가 같아도 독립 표본 두 개로 세지 않는다. ±0.98 score는 실제 센서 정확도98%가 아니다.

## 채택 조건과 예산 효과 분리

두 요청 정책이 모두 실제 측정을 수행한9입력만 비교하면 다음과 같다. 이 부분집합은 사후 집계이며 새 정책·입력이나 추가 실험은 아니다. 빠진4입력은 요청 조건에 해당하지 않은 clear_A/strong_primary_wrong_B와 이중 정책이 예산 때문에 요청하지 못한2입력이다.

| 실제 요청이 있는 동일9입력 | 정답 | 오답 | 보류 | 요청 / feature 단위 |
|---|---:|---:|---:|---:|
| single_contract | 5 | 3 | 1 | 9 / 18 |
| corroborated | 2 | 1 | 6 | 18 / 36 |

이중 정책은 primary_flipped_A·declared_overlap_A의 오답2개를 보류로 바꿨다. 반면 witness_flipped_A·stale_witness_A·weak_witness_A의 정답3개도 보류했다. 전체 정답 감소5개 중 나머지2개는 요청/feature 예산 부족으로 측정 자체를 하지 못한 효과다. 따라서 전체 오답 감소를 채택 조건만의 무조건적 개선으로 설명하지 않는다.

## 측정과 전체 계산 비용

초기13입력 합계는 세 정책 모두 settle18·tick266·group update1,066·signal2,136이다. 아래 전체 비용은 이 초기 비용을 포함한다.

| 정책 | 요청 / feature 단위 | 재추론 settle / tick | 전체 settle / tick | 전체 group update | 전체 signal | case child CPU초 | case wall초 |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_query | 0 / 0 | 0 / 0 | 18 / 266 | 1,066 | 2,136 | 1.438158 | 1.513037 |
| single_contract | 11 / 22 | 21 / 564 | 39 / 830 | 3,358 | 6,792 | 1.465492 | 1.614454 |
| corroborated | 18 / 36 | 6 / 168 | 24 / 434 | 1,750 | 3,528 | 1.452064 | 1.563880 |

이중 정책의 tick은 단일 정책보다47.7% 적지만 측정 요청과 합성 feature 단위는63.6% 많았다. 채택을 보류하거나 예산 때문에 요청을 거부하면 재추론이 줄어든다. 정답도 함께 감소했으므로 같은 품질에서 계산을 절감한 결과가 아니다. no_query보다도 tick은266→434로 늘었다. 서로 다른 측정 단위와 tick을 임의 환율로 합치거나 금전·에너지 우위를 주장하지 않는다.

single_contract는 추가 settle44회를 예약해21회 사용·23회 해제했다. corroborated는36회를 예약해6회 사용·30회 해제했다. 잘못되거나 정보가 없는 측정에도 요청당2 feature 단위를 부과했다. normalization 연산 수는 각 정책의 group update 수와 같다. case JSON bytes는106,256 / 280,449 / 169,593이다.

provider wall 합계는 단일0.002678621초, 이중0.003963073초였다. 이는 합성 fixture I/O·World.measure·응답 변환 비용이며 실제 센서 대기시간이 아니다. case CPU/wall에는 import·graph 구성·정책/hash·fixture I/O·측정·재추론·직렬화가 포함된다. 준비·서버 audit를 포함한 전체 child CPU는4.696034초였다. 짧은 단일 실행과 대기 간격의 영향을 받으므로 작은 CPU/wall 차이로 속도 개선을 추정하지 않는다. 학습0이므로 학습 포함 손익분기는 판정하지 않는다.

## 무결성·수신과 실행 한계

case39개와 preparation/result/summary/source-postcheck4개, **총43개 원자료 JSON의 SHA256이 서버 raw manifest와 모두 일치**한다. source manifest도 전송 전 동결 SHA와 일치하며82개 source의 현재 로컬 bytes와 원격 전후 일치 보고를 대조했다. 이번 수신 자료는 마스킹되지 않았다. completion은 raw 봉인 후 생성된 별도 영수증이다.

전체 evidence.zip은 서버 준비 완료이며 agent/기기의 로컬 수신은 확인하지 않았다. ZIP 내부와 로컬 raw를 직접 byte 대조했다고 주장하지 않는다. download 준비와 실제 전달을 구별해 transport-receipt에 기록했다.

첫 실행 요청은 INVALID_ARGUMENT를 반환했고 요청 ID가 없었다. 원격 실행 폴더 부재를 읽기 전용으로 확인한 뒤, 포털 요청 길이 제한에 맞게 설명을 줄이고 같은 동작의 한 줄 명령으로 제출했다. ZIP hash와 실험 코드·상한은 바꾸지 않았다. 실제 실험은 소유자 승인된 d1196eed 요청으로1회 실행됐으며, 이 접수 수정은 실패 실험의 재실행이 아니다.

stage에 기록된 raw 합계 최대는598,614bytes였다. raw128MiB 검사는 실패를 포함해 stage가 끝난 뒤 수행하는 soft 검사이고 디스크 hard quota가 아니다. 개별 파일 제한을 합계 quota로 해석하지 않는다. 부모 한도로 큰 봉인·실패 영수증 쓰기도 실패할 수 있고 SIGTERM 정리/봉인은 best effort다. 실제 실패를 주입하지 않았으므로 SIGKILL·저장장치 정지 등의 봉인을 보증하지 않는다. 이번 정상 종료의 봉인만 확인했다.

bootstrap의 중요 조건은 assert 대신 명시적 예외를 쓰고 worker PYTHONOPTIMIZE=0을 고정했다. private 생성 스크립트는 역사적 작성 기록이며 정식 source 복원·재실행용이 아님을 표시했다. prepared/ 사본은 없다. 기존 src·r19/r20/r21 하네스·과거 입력/봉인은 변경하지 않았다. replay_saved.py는 실행 후 추가한 보조 검산 도구이며 동결 ZIP에는 포함되지 않는다.

## 연구 판단

이번 규칙은 일부 명시적 불일치와 알려진 근거 중복을 거부하는 장치로는 작동했다. 그러나 **두 측정의 일치만으로 믿고 채택할 일반 조건은 얻지 못했다.** 올바른 primary를 막는 비용과 동시 오답을 허용하는 실패가 모두 남았다. 이 정책을 품질 보존 정책으로 승격하지 않는다.

다음 설계에서는 오답·보류·측정 비용의 허용 기준을 먼저 고정하고, source 신뢰도를 주장하려면 선언 외에 실제로 관측 가능한 calibration 근거와 분리된 평가 입력·그 근거를 얻는 비용을 포함해야 한다. r22의 정답을 보고0.8을 조정하거나 fault 이름을 정책에 넣지 않는다. 이번에는 그 후속 실험을 실행하지 않았다. 학습 효율·수정 기억 유지·자율 계층 형성·물리 센서 독립성·일반화는 여전히 입증되지 않았다.

## 재현 핀

- 실행 source ZIP:256,989bytes, SHA256 `0297f0af7312897b1c4fde5f47036d3b6950e5988632eee707d43f823fa77ef1`.
- source manifest SHA256: `89a203fa1cffbe3d0b487c291ebc53174cce28a820aad3c644d847f94ba324d8`.
- summary SHA256: `b96a75b109342144a2ba848e66c8ef073ceb45696d20267bcbdec06b8ecb9220`.
- 서버 evidence.zip:179,219bytes, SHA256 `ca6335b416fcc71335d4c2fa7eeb931e83818ac068a628865ad47f2d9af97de5`.
- 실행 요청 `d1196eed…`, 다운로드 준비 요청 `82d37319…`(서버 준비 완료·로컬 ZIP 수신 미확인).
- 저장 자료 재생: `python -B tools/r22_measurement_adoption/replay_saved.py --evidence evidence/measurement-adoption-20261019-r22 --out <존재하지 않는 새 receipt.json 경로>`.
