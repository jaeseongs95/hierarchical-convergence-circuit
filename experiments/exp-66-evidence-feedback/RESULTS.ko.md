# EXP-66 / r20 결과: 조건부 피드백의 품질·계산 절충

2026-10-19 KST. AI Research SSH에서 11개 합성 입력×3방식, 총33개 cell을 한 번 실행했다. **조건부 피드백은 무조건 피드백의 오답 5개를 1개로 줄이고, tick을 1,244→582로 줄였다.** 피드백 없는 기준선은 오답 0·보류 7개였으므로 품질 보존을 보증한 결과는 아니다. 출처 조건을 통과한 잘못된 aux에서 오답이 남았다.

## 실행·검산

실행은 `COMPLETED`다. 준비1·case33·audit1의 **35단계 모두 exit0**, 봉인 포함 **4.373920381초**로 600초 상한 안에서 끝났다. 학습0, 실제 native settle90회로 사전 상한110회 안이며, 2,386개 native tick을 기록했다. 자동 반복·parameter 변경은 없었다. PID13035는 종료 후 `/proc`에 없었다.

서버 준비는104개 pure assertion을 통과했다. 이 중66개는 stub orchestration assertion이며 실제 커널 관측으로 세지 않는다. 별도 scalar 수식으로 실제33개 기록의 state·residual·종료·판정·비용을 재생했고, 사전 고정한 서버 절대오차0에서 통과했다. gate/drive/승격 provenance 및 paired-world 동일 예측도 확인했다. Programs와 커널은 main `5927d60`의 r19 구현을 재사용했다. 해당 r19 감사 도구는 tuple/list 수정판 `bb0159ba…`다.

서버 audit는 gate action·승격 revision/값·tick state·program bias 변조5종을 거부했다. 원래 tick/program 변조는 하위 trace hash 때문에 `gate binding`에서 먼저 거부될 수 있다. 이를 해당 하위 검사기의 변이 증거로 과장하지 않도록, 사후 로컬 검산에서 gate가 없는 bottom_up 기록에 별도로 변조했다. 각각 **`scalar replay tick mismatch`**, **`fixed program`**에서 거부됨을 정확히 확인했다. 실행 source나 결과는 수정하지 않았다.

로컬 보조 재생도33개 cell 전체가 통과했다. 새로운 native tick/settle은 금지했고, 사전 고정한 절대오차1e-15에서 관측한 최대 차이는 `1.6940658945086007e-21`이다. 원자료 집계·정답/오답/보류·비용·출력 bytes도 재계산했다. 이는 독립 실험 반복이나 새 성능 표본이 아니다.

## 품질

| 방식: 각11개 조건 | 분류 정답 | 분류 오답 | 분류 보류 | 관계 정답 | 관계 오답 | 관계 보류 |
|---|---:|---:|---:|---:|---:|---:|
| bottom_up | 4 | 0 | 7 | 6 | 5 | 0 |
| unconditional | 6 | 5 | 0 | 6 | 5 | 0 |
| gated | 6 | 1 | 4 | 6 | 1 | 4 |

gated는 이 사례 집합에서 무조건 피드백의 정답6개를 유지하고, 잘못된 채택4개를 보류로 바꿨다. bottom_up과 비교하면 정답2개가 늘고 오답1개가 추가됐다. 보류가 줄었다는 사실만으로 품질이 보존됐다고 말할 수 없다. 관계 판정에서도 하위가 모호한데 상위가 답을 내는 경우를4개 보류로 바꿨지만, 최종 하위 자체가 잘못 결정된1개는 남았다.

| 조건 | gated 행동 | 최종 분류/관계 | tick / settle |
|---|---|---|---:|
| clear_A | 이미 결정됨: 관계만 계산 | A / 일치 | 56 / 2 |
| clear_B | 이미 결정됨: 관계만 계산 | B / 일치 | 56 / 2 |
| revision_0 | aux 없음: 상위 생략 | 보류 / 보류 | 4 / 1 |
| derived_aux | f0와 근거 중복: 상위 생략 | 보류 / 보류 | 4 / 1 |
| independent_A | 조건 통과: 피드백1회 | A / 일치 | 114 / 4 |
| independent_B | 조건 통과: 피드백1회 | B / 일치 | 114 / 4 |
| conflicting_aux | aux/context 방향 충돌: 상위 생략 | 보류 / 보류 | 4 / 1 |
| stale_aux | aux revision 불일치: 상위 생략 | 보류 / 보류 | 4 / 1 |
| independent_wrong | 조건 통과: 피드백1회 | **B / 일치: 둘 다 오답** | 114 / 4 |
| strong_conflict | 안정된 하위 유지: 관계만 계산 | A / 불일치 | 56 / 2 |
| revision_1 | 새 측정으로 하위 결정: 관계만 계산 | A / 불일치 | 56 / 2 |

`independent_B`와 `independent_wrong`은 id 외 공개 measurement/context/aux까지 같고 hidden reference만 다르다. 세 방식 모두 같은 예측·계산을 냈다. 기록된 출처 분리와 방향 일치는 truth를 구별할 정보가 아니다. 모든 입력이 합성이므로 실제 센서의 독립성·정확도·source 인증도 검증하지 않았다.

`revision_0`→`revision_1`에서는 같은 id/context에 새 revision의 실제 primary feature가 0/0→1/.8로 바뀌었다. gated는 보류→A/불일치로 바뀌었다. 각 cell은 새 process와 .5 state에서 시작한다. 이는 새 입력 처리의 확인이며 학습된 수정 기억·장기 수정 유지의 결과가 아니다.

## 계산과 전체 비용

| 방식: 11개 합계 | settle | tick | group update | signal transmission | case child CPU초 | case wall초 |
|---|---:|---:|---:|---:|---:|---:|
| bottom_up | 22 | 560 | 2,536 | 5,664 | 1.061255 | 1.271703 |
| unconditional | 44 | 1,244 | 5,248 | 11,040 | 1.073258 | 1.271740 |
| gated | 24 | 582 | 2,430 | 5,064 | 1.056877 | 1.271466 |

무조건 피드백 대비 gated의 tick은 **53.2%**, group update는 **53.7%**, signal은 **54.1%** 적었다. 하위가 이미 결정된4개에서는 추가 feedback을 생략했고, 부적합 aux4개에서는 상위 settle과 승격 자체를 생략했다. 이는 고정된 task wrapper의 계산 선별 효과이며 학습 회로의 정확 대체·재사용 절감이 아니다.

bottom_up 대비 gated는 tick이22개(3.9%) 늘었지만, group update는106개(4.2%), signal은600개(10.6%) 적었다. 생략된 큰 상위망과 추가된 작은 하위망의 비중이 달라 카운터가 같은 방향으로 움직이지 않았다. 서로 다른 비용 단위를 합산하거나 tick 하나로 전체 효율을 판정하지 않는다.

gate wall 합계는0.001259216초였다. predicate 수·gate hash와 adapter vector 수는 raw에 있으며 promotion bytes는 bottom_up4,910 / unconditional10,071 / gated4,587이다. adapter vector 수는 생성된 벡터 수이고 전체 Python 연산 수가 아니다. 세 방식 모두 graph 객체 구성 비용이 남는다.

case CPU/wall은 import·graph 구성·gate·hash·adapter·출력 직렬화를 포함한다. 준비와 서버 검산을 포함한 전체 child CPU는3.476114초, 봉인 포함 server wall은4.373920381초다. 로컬 보조 검산은 별도0.5871623초였다. 작은 단일 실행은 import와 대기 간격의 영향을 크게 받으므로 CPU 속도 차이·금전 절감·에너지 우위는 입증하지 않았다. 학습0이므로 학습 포함 손익분기도 판정하지 않는다.

## 수신·보존 범위와 제약

`evidence/evidence-feedback-20261019-r20/raw/`에는33개 전체 case JSON과 preparation/result/summary JSON을 보존했다. 이 **36개 JSON의 SHA256이 서버 raw manifest와 전부 일치**한다. native 기록·집계는 마스킹되지 않았고 전부 로컬 재생했다.

서버 result는 source74개 전후 일치를 보고하며, 실행 source manifest SHA는 동결 패키지와 같다. 현재 로컬 source74개도 동결 manifest와 대조했다. 다만 포털이 원격 source manifest 및 source-postcheck의 경로2개를 마스킹했다. 두 원격 파일의 정확한 원문 bytes는 받지 못했다. 이를 `source-manifest.redacted.json`, `source-postcheck.redacted.json`으로 구분해 보존하며 raw 해시 검증36개에 포함하지 않는다. `source-manifest.expected.json`은 전송 전의 로컬 동결본이다. 원문을 복구하거나 원격 두 파일의 byte 일치를 주장하지 않는다.

전체 evidence.zip은 서버에서 준비됐으나 로컬 수신은 확인하지 않았다. 따라서 로컬 자료를 봉인 ZIP 내부와 직접 byte 대조했다는 주장도 하지 않는다. download 준비 완료와 파일 수신은 별개다.

실제 run은600초·stage60초 이내였고 raw/ZIP도128MiB 미만이었다. 128MiB 검사는 stage 종료 뒤 수행되며 디스크 hard quota는 아니다. 바깥 timeout의 강제 SIGTERM 등 모든 종료에서 finally 봉인이 보장되지는 않는다. 이번 정상 종료의 봉인 완료만 확인했다. 다음 실행 계약에서는 이 실패 경로의 한계를 별도로 처리해야 한다.

## 다음 방향

조건부 피드백은 명시적 근거 결함을 거부하는 작은 정책으로 유지할 수 있다. 남은1개 오답은 같은 공개 정보로 구별되지 않으므로 **새 식별 정보를 얻는 관측 요청의 조건과 비용 상한**을 다음 과제로 정한다. 비교는 현재 gated의 보류와, 제한된 새 primary 측정을 요청한 뒤 재판정하는 정책으로 한정하고 정답·오답·보류·관측/재계산 비용을 함께 고정한다. 관측 응답은 공개 측정이며 hidden reference/정답 플래그를 정책에 넘기지 않는다.

이번에는 그 후속 실험을 실행하지 않았다. 일반화·품질 보존 보증·학습 효율·native AdaptiveSession adoption·route proof·자율 계층 학습은 여전히 입증되지 않았다.

## 재현 핀

- 실행 source ZIP:242,655 bytes, SHA256 `ccf86621f7e5ff9ed1370e831f63fcb24385846fa88ae0e206c1602625409869`.
- 실행 source manifest SHA256: `2d05884841085ed454ae029fc1d53d87086dd811ecaad91c7807e2080197bad2`.
- 검증된 summary SHA256: `138e6fd5824840e3891d2376b1c621f5a152669883fd383716e9d0123d127b9e`.
- 서버 `/home/mcpops/hcc-evidence-feedback-20261019-r20/evidence.zip`:205,335 bytes, SHA256 `765a0a8710190e95ad7118f9664ec90c3ba98e5e27351e61733103f7df46c035`.
- 실행 요청 `506593f0…`:소유자 승인 후1회 실행. 다운로드 준비 요청 `35bc1ec4…`:서버 준비 완료, 로컬 ZIP 수신 미확인.
- 저장 자료 재생: `python -B tools/r20_evidence_feedback/replay_saved.py --evidence evidence/evidence-feedback-20261019-r20 --out <존재하지 않는 새 receipt.json 경로>`.
- 재생 utility는 실행 후 추가한 로컬 검증 도구다. 동결 source ZIP에 포함됐다고 주장하지 않는다. `probe.py`·정책·입력은 실행 후 바꾸지 않았다.
