# EXP-70 / r24 결과: 정확 전이 재사용 기회 선별

기존 실행의 process 수명에 맞춘 분석에서는 988개 전이 중 18개(1.82%)만 적중했고, 모두 같은 settle 안에서 값이 더 이상 변하지 않는 정확한 고정점 반복이었다. 서로 다른 settle 사이의 적중은 없었다. **이 자료는 범용 회로 cache 구현을 진행할 근거를 제공하지 않는다.** 별도 native cache나 조기 종료는 구현하지 않았다.

## 방향성 토론과 실행

구현 전에 HIGH 토론을 수행했다. 연구 가치·평가 타당성·상태 수명·비용의 독립 4관점, 조건부 교차반박 3건, 별도 fresh judge가 후보를 검토했다. 원자료에서 완전 입력의 정확한 반복이 실제로 남는지 먼저 선별하는 C안을 조건부 채택했다. 토론과 조건은 [DIRECTION.ko.md](DIRECTION.ko.md), 실행 전 계약은 [design.ko.md](design.ko.md)에 보존했다. 이 토론은 구현 최종 감사나 SSH 소유자 승인을 대신하지 않는다.

승인된 AI Research SSH 요청 `ccec9883041b1493694fa6e6027b8b2ca7b9653f3a47e032`을 한 번 실행했다. 새 전용 폴더에서 준비→저장 전이 분석→별도 검산을 수행했고 3단계 모두 exit 0이었다. 봉인 포함 wall 2.988781초, 자식 CPU 합계 2.717183초였다. 전체 600초 상한 안에서 종료했고 재시도하지 않았다. 학습·새 native tick·settle·World.measure 호출은 각각 0회다.

입력은 R19의 18 case, 36 settle, 988 tick이다. 전이가 없는 separate_algorithms 6 case는 tick 수를 늘리지 않는다. 같은 988개 전이를 두 cache 수명 가정으로 분석한 1,976행이며, 독립 실행이나 표본 1,976개가 아니다. 새 품질·예측·학습 효과를 측정한 실험도 아니다.

## 수명별 관측

| arm / 수명 | 전이 | hit / miss | 같은 settle / 다른 settle / 교차 case | peak 항목 / logical bytes |
|---|---:|---:|---:|---:|
| bottom_up / case_local | 312 | 9 / 303 | 9 / 0 / 0 | 56 / 364,836 |
| coupled / case_local | 676 | 9 / 667 | 9 / 0 / 0 | 112 / 761,744 |
| bottom_up / arm_stream | 312 | 81 / 231 | 3 / 0 / 78 | 231 / 1,662,924 |
| coupled / arm_stream | 676 | 147 / 529 | 3 / 0 / 144 | 529 / 3,570,161 |

`case_local`은 원 R19의 case별 subprocess 수명에 맞춘다. 두 arm 각각 ambiguous_A·ambiguous_B·misleading_A에서 3회씩 적중했고, current와 next의 이진 값이 모두 같았다. 다른 case에서는 0회였다. 이 고정점의 숫자를 재사용해도 stable_steps·history·margin·남은 budget·Cost·trace 처리는 별도다. 실제 종료나 tick API 전체를 생략했다고 해석할 수 없다.

`arm_stream`은 arm별로 여러 case를 한 process에서 처리한다고 가정한 긴 수명이다. 원 실행에서 제공되지 않은 수명이다. 228 hit 중 222개는 **프로그램·config·initial·drives·flags·source까지 같은 전체 kernel 입력의 재호출**에서 나왔다. 이 222개 중 공개 measurement/context도 같은 것은 154개, 공개 입력은 달라도 해당 kernel의 완전 입력은 같은 것은 68개였다. 새로운 kernel 입력으로 일반화한 교차 case 적중은 0개다. 나머지 6개는 같은 settle 반복이다. 첫 삽입 원점으로 귀속하므로 긴 수명에서는 일부 고정점 반복도 이전 case 원점으로 분류된다. 두 수명의 hit를 합치거나 차이를 독립적인 성과로 세지 않는다.

## 비용 해석

원 수명에서 생략 가능하다고 계산한 수치 산술의 상한은 group update 54개, signal transmission 72개, normalization 54개였다. 원 988 tick의 group 4,212개·signal 8,944개 비용 기록은 수정하지 않았다. 이 상한은 native 호출·수렴 제어·Cost·trace까지 제거한 측정치가 아니다.

수명 하나를 분석할 때 완전 key 3,137,004 bytes를 생성했다. case_local의 분석 CPU는 bottom_up 0.104622초, coupled 0.216353초였고, wall은 각각 0.104623초·0.216372초였다. arm_stream은 CPU 0.104817초·0.219292초, wall 0.104819초·0.219316초였다. key/hash/lookup/copy-store/저장값 검증 구간은 원자료에 별도로 기록했다. 이 부분 계측에는 보고서·원점 구성·추가 직렬화·reset 등 모든 비용이 포함되지는 않는다.

이는 저장 자료를 분석한 비용이며 online cache의 실제 비용이나 native 기준 실행과의 속도 비교가 아니다. known next-state와의 검증도 연구 비용이다. logical payload는 정의된 key·next·origin·header·공개 signature bytes 합이며 dict overhead·공유 객체·allocator·전체 RSS가 아니다. **CPU·메모리·금액·학습 포함 총비용 절감은 입증하지 않았다.**

## 검증과 한계

완전 key는 Program 순서·Config 전체·current 전체·drives·top_down·동결 dynamics SHA를 결속한다. 타입과 signed zero를 구별하며 근접 float를 합치지 않는다. 조회는 SHA 일치만이 아니라 전체 key bytes의 동등성으로 결정한다. 과거 삽입만 사용하고, 저장 출력 bit가 충돌하면 중단한다. 다른 arm에서 cache를 물려받지 않는다.

준비 단계의 27개 순수 검사는 합성 4전이만 사용했다. 실제 census의 독립 표현 index 검산과 hit/key/origin/산술상한/합계 변조 5종 거부가 통과했다. 원 입력 수식 재생의 서버 최대 절대오차는 0, 로컬은 1.6940658945086007e-21로 PRE 허용치 1e-15, 상대오차 0 안이었다. 이 허용치는 수식 재생에만 쓰며 재사용 key/next bit 동등성을 완화하지 않는다. 저장 원자료 4개 JSON의 SHA와 로컬 동결 source 107개를 확인했다. 사후 작성한 `replay_saved.py`는 저장 결과 재검산 도구이며 서버의 동결 ZIP에는 포함되지 않는다.

원 R19의 `FAILED_AT_AUDIT` 이력은 그대로다. 당시 tuple/JSON 배열 검산 문제의 수정 재생과 이번 분석을 원 실행 성공으로 바꾸지 않았다. 원 R19의 실행 후 전체 source 재해시 미완료도 해소했다고 주장하지 않는다.

초기 큰 stdout 출력은 잘렸다. census는 정상 범위 읽기로 800,000 bytes와 612,942 bytes를 받아 결합했고 전체 SHA를 서버 manifest와 대조했다. 가려진 source 경로를 복원하거나 표현을 바꿔 우회하지 않았다. remote source manifest와 postcheck는 일부 경로가 가려진 원문만 보존했다. 서버의 `source_unchanged=true` 보고 및 source manifest SHA 결속은 확인했지만 **두 remote source 목록의 정확한 bytes는 로컬 검증하지 못했다.** 로컬 pre-frozen manifest는 송신 전 파일이며 수신 manifest로 가장하지 않는다. stdout/stderr 6개와 완성 evidence ZIP은 로컬 미수신이다. ZIP 준비 완료를 다운로드 완료로 세지 않는다. 상세는 evidence의 `transport-receipt.json`, `local-replay.json`을 따른다.

관측한 부모 AS 제한은 512MiB, 개별파일 32MiB이고 준비 child는 AS 512MiB·개별파일 16MiB다. 최대 stage raw는 1,419,839 bytes로 stage 종료 soft bound 128MiB 안이었다. worker 1·retry 0·stage 60초 제한이다. hard disk quota·peak RSS·모든 child의 개별 getrlimit·SIGKILL/디스크 실패 시 봉인을 시험하거나 보증하지 않았다.

## 결정과 재현

이번 선별은 여기서 종료한다. 범용 cache의 이득으로 남은 사례는 없으며, 원 수명에서 남은 것은 정확 고정점의 몇 번 반복이다. 다음 연구 후보를 정한다면 **고정점 뒤 수치 산술만 생략하면서 patience·history·Cost·종료 의미를 보존할 수 있는가**를 좁게 증명하고, 그 관리 비용과 native 총시간을 함께 비교하는 과제다. 이 후속 native 실험은 이번 실행에 포함하지 않았다.

- source ZIP SHA256: `dc83430846b8ce54b13d3ffe837ce3a234682636e392979f4b7a9e019fa56102` (343,218 bytes)
- source manifest SHA256: `9f99111da48a4d66f8fd707c94c0d702e4416bec0a03acf59951db3a9bc6d3af` (107 files)
- frozen spec SHA256: `130dd200031ddf46c2295737d50b9c24c0f0c8ccf52dcbb6f0166dd884d70dc5`
- summary SHA256: `088b07f98b762125a289539c184a1e7e66f6a1f360f9ae97281805ff422fb99f`
- server evidence ZIP SHA256: `716934b5a15ab7da6aa1b605cfc82e10c64831f6876ab0b9b645976ac987e07e` (300,769 bytes; 로컬 미수신)

저장 결과 재검산 명령(저장소 root 기준):

```powershell
python -B tools/r24_trust_boundary/replay_saved.py --evidence evidence/trust-boundary-20261019-r24 --out <별도-검산-영수증.json>
```

이 명령은 새 native 실행이나 성능 재측정을 하지 않는다. 제출된 로컬 검산 영수증은 원 수신 자료와 함께 보존한다.
